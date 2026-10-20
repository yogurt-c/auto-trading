package com.autotrading.kis

import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import okhttp3.mockwebserver.RecordedRequest
import java.time.Clock
import java.time.Instant
import java.time.ZoneId
import java.util.concurrent.TimeUnit

/** sleep하면 시간이 그만큼 흐르는 가짜 시계. */
class FakeTime(start: Instant = Instant.parse("2026-11-02T00:10:00Z")) : Clock(), Sleeper {
    var now: Instant = start
    val sleeps = mutableListOf<Long>()

    override fun sleep(millis: Long) {
        sleeps += millis
        now = now.plusMillis(millis)
    }

    override fun instant(): Instant = now
    override fun getZone(): ZoneId = KisHttp.KST
    override fun withZone(zone: ZoneId?): Clock = this
}

const val TOKEN_JSON =
    """{"access_token":"tok-1","access_token_token_expired":"2026-11-03 09:10:00","token_type":"Bearer","expires_in":86400}"""

fun json(body: String, code: Int = 200, trCont: String? = null): MockResponse =
    MockResponse().setResponseCode(code).setBody(body).apply { trCont?.let { setHeader("tr_cont", it) } }

fun ok(output: String) = json("""{"rt_cd":"0","msg_cd":"MCA00000","msg1":"정상처리 되었습니다.",$output}""")

fun kisError(code: String, msg: String, http: Int = 500) =
    json("""{"rt_cd":"1","msg_cd":"$code","msg1":"$msg"}""", http)

class KisFixture(
    val env: KisEnvironment = KisEnvironment.PAPER,
    val tokens: TokenStore = InMemoryTokenStore(),
) : AutoCloseable {
    val server = MockWebServer().apply { start() }
    val time = FakeTime()
    val client = KisClient.create(
        env = env,
        credentials = KisCredentials("app-key-123", "app-secret-456"),
        account = Account("50123456", "01"),
        tokens = tokens,
        baseUrl = server.url("/"),
        clock = time,
        sleeper = time,
    )

    fun enqueue(vararg responses: MockResponse) = responses.forEach(server::enqueue)

    fun take(): RecordedRequest = checkNotNull(server.takeRequest(1, TimeUnit.SECONDS)) { "요청 없음" }

    /** 토큰 발급 요청을 건너뛰고 다음 API 요청을 돌려준다. */
    fun takeApi(): RecordedRequest = generateSequence { take() }.first { it.path != "/oauth2/tokenP" }

    override fun close() = server.shutdown()
}
