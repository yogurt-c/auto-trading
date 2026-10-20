package com.autotrading.kis

import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.contentOrNull
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.longOrNull
import okhttp3.HttpUrl
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import java.io.IOException
import java.time.Clock
import java.time.Duration
import java.time.LocalDateTime
import java.time.ZoneId
import java.time.format.DateTimeFormatter

internal class KisResponse(val body: JsonObject, val trCont: String)

/**
 * 공통 헤더·토큰·호출 간격·재시도. 재시도 규칙:
 * - 호출 한도(EGW00201)·토큰 만료: 처리되지 않은 요청이므로 조회·주문 모두 다시 보낸다
 * - 네트워크 끊김·응답 본문 없는 5xx: 조회만 다시 보낸다. 주문은 접수됐을 수 있어 [KisException.Transport]
 */
internal class KisHttp(
    private val http: OkHttpClient,
    private val baseUrl: HttpUrl,
    private val env: KisEnvironment,
    private val credentials: KisCredentials,
    private val tokens: TokenStore,
    private val clock: Clock,
    private val sleeper: Sleeper,
) {
    init {
        require(!http.retryOnConnectionFailure) { "retryOnConnectionFailure는 꺼야 한다 (주문 중복 방지)" }
    }

    private var lastCallAt = Long.MIN_VALUE

    @Synchronized
    fun get(path: String, trId: String, params: Map<String, String>, trCont: String = ""): KisResponse {
        val url = baseUrl.newBuilder().addPathSegments(path).apply {
            params.forEach { (k, v) -> addQueryParameter(k, v) }
        }.build()
        return call(trId, retryTransport = true) { Request.Builder().url(url).get().header("tr_cont", trCont) }
    }

    @Synchronized
    fun post(path: String, trId: String, body: Map<String, String>): KisResponse {
        val url = baseUrl.newBuilder().addPathSegments(path).build()
        val payload = JSON.encodeToString(JsonObject.serializer(), jsonOf(body)).toRequestBody(JSON_TYPE)
        return call(trId, retryTransport = false) { Request.Builder().url(url).post(payload) }
    }

    private fun call(trId: String, retryTransport: Boolean, request: () -> Request.Builder): KisResponse {
        var tokenRenewed = false
        var failure: KisException? = null
        for (attempt in 0 until MAX_ATTEMPTS) {
            if (attempt > 0) sleeper.sleep(BACKOFF_MILLIS * attempt)
            val built = request().authorize(trId).build()
            val (status, body, trCont) = try {
                execute(built)
            } catch (e: IOException) {
                failure = KisException.Transport("KIS 연결 실패 (${e.javaClass.simpleName})", e)
                if (retryTransport) continue else throw failure
            }
            val msgCd = body?.string("msg_cd").orEmpty()
            val rtCd = body?.string("rt_cd")
            when {
                msgCd == RATE_LIMITED -> failure = KisException.RateLimited()
                msgCd in TOKEN_REJECTED && !tokenRenewed -> {
                    tokens.save(null)
                    tokenRenewed = true
                }
                msgCd in TOKEN_REJECTED -> throw KisException.Auth(msgCd, body?.string("msg1").orEmpty())
                rtCd == null -> {
                    failure = KisException.Transport("KIS 응답 오류 (HTTP $status)")
                    if (!retryTransport || status < 500) throw failure
                }
                rtCd != "0" -> throw KisException.Rejected(msgCd, body?.string("msg1").orEmpty().trim())
                else -> return KisResponse(checkNotNull(body), trCont)
            }
        }
        throw checkNotNull(failure)
    }

    private fun execute(request: Request): Triple<Int, JsonObject?, String> {
        throttle()
        return http.newCall(request).execute().use { response ->
            val text = response.body?.string().orEmpty()
            val body = runCatching { JSON.parseToJsonElement(text).jsonObject }.getOrNull()
            Triple(response.code, body, response.header("tr_cont").orEmpty())
        }
    }

    private fun throttle() {
        if (lastCallAt != Long.MIN_VALUE) {
            val wait = lastCallAt + env.minIntervalMillis - clock.millis()
            if (wait > 0) sleeper.sleep(wait)
        }
        lastCallAt = clock.millis()
    }

    private fun Request.Builder.authorize(trId: String) = this
        .header("content-type", "application/json; charset=utf-8")
        .header("authorization", "Bearer ${token()}")
        .header("appkey", credentials.appKey)
        .header("appsecret", credentials.appSecret)
        .header("tr_id", trId)
        .header("custtype", "P")

    /** 저장된 토큰이 만료 10분 전까지 남아 있으면 재사용한다. */
    private fun token(): String {
        tokens.load()?.takeIf { it.expiresAt > clock.instant().plus(TOKEN_MARGIN) }?.let { return it.value }
        val request = Request.Builder()
            .url(baseUrl.newBuilder().addPathSegments("oauth2/tokenP").build())
            .post(
                JSON.encodeToString(
                    JsonObject.serializer(),
                    jsonOf(
                        mapOf(
                            "grant_type" to "client_credentials",
                            "appkey" to credentials.appKey,
                            "appsecret" to credentials.appSecret,
                        ),
                    ),
                ).toRequestBody(JSON_TYPE),
            )
            .build()
        val (status, body, _) = try {
            execute(request)
        } catch (e: IOException) {
            throw KisException.Transport("KIS 토큰 발급 연결 실패 (${e.javaClass.simpleName})", e)
        }
        val value = body?.string("access_token")
        if (body == null || value.isNullOrBlank()) {
            val code = body?.string("error_code").orEmpty()
            if (code == TOKEN_ISSUE_LIMITED) throw KisException.TokenIssueLimited()
            throw KisException.Auth(code.ifEmpty { "HTTP $status" }, body?.string("error_description").orEmpty())
        }
        val expiresAt = body.string("access_token_token_expired")
            ?.let { runCatching { LocalDateTime.parse(it, EXPIRY_FORMAT).atZone(KST).toInstant() }.getOrNull() }
            ?: clock.instant().plusSeconds(
                (body["expires_in"] as? JsonPrimitive)?.longOrNull
                    ?: throw KisException.Malformed("토큰 유효기간 없음"),
            )
        return AccessToken(value, expiresAt).also(tokens::save).value
    }

    companion object {
        const val RATE_LIMITED = "EGW00201"
        const val TOKEN_ISSUE_LIMITED = "EGW00133"
        val TOKEN_REJECTED = setOf("EGW00121", "EGW00123") // 유효하지 않은 토큰, 만료된 토큰
        const val MAX_ATTEMPTS = 4
        const val BACKOFF_MILLIS = 1_000L
        val TOKEN_MARGIN: Duration = Duration.ofMinutes(10)
        val KST: ZoneId = ZoneId.of("Asia/Seoul")
        private val EXPIRY_FORMAT = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss")
        private val JSON_TYPE = "application/json; charset=utf-8".toMediaType()
        val JSON = Json { ignoreUnknownKeys = true }

        private fun jsonOf(fields: Map<String, String>) = buildJsonObject {
            fields.forEach { (k, v) -> put(k, JsonPrimitive(v)) }
        }
    }
}

internal fun JsonObject.string(key: String): String? = (this[key] as? JsonPrimitive)?.contentOrNull
