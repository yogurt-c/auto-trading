package com.autotrading.kis

import com.autotrading.core.Side
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.jsonObject
import okhttp3.HttpUrl
import okhttp3.HttpUrl.Companion.toHttpUrl
import okhttp3.OkHttpClient
import java.math.BigDecimal
import java.time.Clock
import java.time.Duration
import java.time.LocalDate
import java.time.format.DateTimeFormatter

/**
 * 앱이 쓰는 KIS API 7종 (모의투자 지원 확인: .claude/docs/kis-api-spec.md).
 * 모든 호출은 블로킹이다. 실전 잠금·주문 종목 제한 같은 불변조건은 engine에서 검증한다.
 */
class KisClient internal constructor(
    private val http: KisHttp,
    private val env: KisEnvironment,
    private val account: Account,
) {
    /** 주식잔고조회 — 연속조회로 전 종목을 모은다. 보유 0주 줄은 뺀다. */
    fun balance(): Balance {
        var deposit: Long? = null
        val positions = paged(BALANCE_PATH, env.balanceTr, balanceParams()) { body ->
            if (deposit == null) {
                val summary = (body["output2"] as? JsonArray)?.firstOrNull()?.jsonObject
                    ?: throw KisException.Malformed("잔고 요약(output2) 없음")
                deposit = summary.won("prvs_rcdl_excc_amt")
            }
            body.rows("output1").map {
                Position(it.text("pdno"), it.qty("hldg_qty"), it.qty("ord_psbl_qty"))
            }
        }
        return Balance(positions.filter { it.qty > 0 }, checkNotNull(deposit))
    }

    /** 매수가능조회 — 미수 없이 살 수 있는 금액(nrcvb_buy_amt). 종목·단가 없이 금액만 조회. */
    fun buyingPower(): Long {
        val params = accountParams() + mapOf(
            "PDNO" to "",
            "ORD_UNPR" to "",
            "ORD_DVSN" to MARKET,
            "CMA_EVLU_AMT_ICLD_YN" to "N",
            "OVRS_ICLD_YN" to "N",
        )
        return http.get(BUYING_POWER_PATH, env.buyingPowerTr, params).body.single("output").won("nrcvb_buy_amt")
    }

    /** 주식현재가 일자별 — 최근 30거래일, 최신 날짜 먼저. 장중이면 맨 앞이 오늘(현재가). */
    fun dailyBars(code: String): List<DailyBar> {
        requireCode(code)
        val params = mapOf(
            "FID_COND_MRKT_DIV_CODE" to "J",
            "FID_INPUT_ISCD" to code,
            "FID_PERIOD_DIV_CODE" to "D",
            "FID_ORG_ADJ_PRC" to "0",
        )
        return http.get(DAILY_PATH, DAILY_TR, params).body.rows("output")
            .filter { it.text("stck_bsop_date").isNotBlank() }
            .map { DailyBar(LocalDate.parse(it.text("stck_bsop_date"), DATE), it.won("stck_clpr")) }
            .sortedByDescending { it.date }
    }

    /**
     * 시장가 주문. [KisException.Transport]가 나면 접수됐을 수 있으니 재주문하지 말고 [orders]로 확인한다.
     */
    fun placeMarketOrder(code: String, side: Side, qty: Int): OrderReceipt {
        requireCode(code)
        require(qty > 0) { "주문 수량은 1 이상: $qty" }
        val body = accountParams() + mapOf(
            "PDNO" to code,
            "ORD_DVSN" to MARKET,
            "ORD_QTY" to qty.toString(),
            "ORD_UNPR" to "0",
        )
        val tr = if (side == Side.SELL) env.sellTr else env.buyTr
        val out = http.post(ORDER_PATH, tr, body).body.single("output")
        return OrderReceipt(out.upper("ODNO"), out.upper("KRX_FWDG_ORD_ORGNO"), code, side, qty)
    }

    /** 주식일별주문체결조회 — 하루 주문 전체(취소 주문 줄 포함). [code]를 주면 그 종목만. */
    fun orders(date: LocalDate, code: String = ""): List<OrderStatus> {
        if (code.isNotEmpty()) requireCode(code)
        val day = date.format(DATE)
        val params = accountParams() + mapOf(
            "INQR_STRT_DT" to day,
            "INQR_END_DT" to day,
            "SLL_BUY_DVSN_CD" to "00",
            "INQR_DVSN" to "01",
            "PDNO" to code,
            "CCLD_DVSN" to "00",
            "ORD_GNO_BRNO" to "",
            "ODNO" to "",
            "INQR_DVSN_3" to "00",
            "INQR_DVSN_1" to "",
            "EXCG_ID_DVSN_CD" to "KRX",
        )
        return paged(ORDERS_PATH, env.ordersTr, params) { body -> body.rows("output1").map(::orderStatus) }
    }

    /** 미체결 잔량 전부 취소. 이미 체결된 수량은 취소되지 않는다. */
    fun cancel(receipt: OrderReceipt): String {
        val body = accountParams() + mapOf(
            "KRX_FWDG_ORD_ORGNO" to receipt.orgNo,
            "ORGN_ODNO" to receipt.orderNo,
            "ORD_DVSN" to "00",
            "RVSE_CNCL_DVSN_CD" to "02",
            "ORD_QTY" to "0",
            "ORD_UNPR" to "0",
            "QTY_ALL_ORD_YN" to "Y",
            "EXCG_ID_DVSN_CD" to "KRX",
        )
        return http.post(CANCEL_PATH, env.cancelTr, body).body.single("output").upper("ODNO")
    }

    private fun orderStatus(row: JsonObject): OrderStatus {
        val side = when (row.text("sll_buy_dvsn_cd")) {
            "01" -> Side.SELL
            "02" -> Side.BUY
            else -> throw KisException.Malformed("매도매수구분 알 수 없음: ${row.text("sll_buy_dvsn_cd")}")
        }
        return OrderStatus(
            orderNo = row.text("odno"),
            originalOrderNo = row.text("orgn_odno").trim().takeIf { it.isNotEmpty() && it.any { c -> c != '0' } },
            code = row.text("pdno"),
            side = side,
            orderedQty = row.qty("ord_qty"),
            filledQty = row.qty("tot_ccld_qty"),
            canceledQty = row.qty("cnc_cfrm_qty"),
            rejectedQty = row.qty("rjct_qty"),
            avgPrice = row.decimal("avg_prvs").toDouble(),
        )
    }

    /** tr_cont가 F/M이면 다음 페이지가 있다. 연속조회 키는 응답 본문의 ctx_area_fk100/nk100. */
    private fun <T> paged(
        path: String,
        trId: String,
        params: Map<String, String>,
        rows: (JsonObject) -> List<T>,
    ): List<T> {
        val result = mutableListOf<T>()
        var fk = ""
        var nk = ""
        var trCont = ""
        repeat(MAX_PAGES) {
            val page = http.get(path, trId, params + mapOf("CTX_AREA_FK100" to fk, "CTX_AREA_NK100" to nk), trCont)
            result += rows(page.body)
            if (page.trCont !in MORE) return result
            fk = page.body.text("ctx_area_fk100")
            nk = page.body.text("ctx_area_nk100")
            trCont = "N"
        }
        throw KisException.Malformed("연속조회가 ${MAX_PAGES}페이지를 넘음")
    }

    private fun accountParams() = mapOf("CANO" to account.cano, "ACNT_PRDT_CD" to account.productCode)

    private fun balanceParams() = accountParams() + mapOf(
        "AFHR_FLPR_YN" to "N",
        "OFL_YN" to "",
        "INQR_DVSN" to "01",
        "UNPR_DVSN" to "01",
        "FUND_STTL_ICLD_YN" to "N",
        "FNCG_AMT_AUTO_RDPT_YN" to "N",
        "PRCS_DVSN" to "01",
    )

    companion object {
        private const val BALANCE_PATH = "uapi/domestic-stock/v1/trading/inquire-balance"
        private const val BUYING_POWER_PATH = "uapi/domestic-stock/v1/trading/inquire-psbl-order"
        private const val DAILY_PATH = "uapi/domestic-stock/v1/quotations/inquire-daily-price"
        private const val ORDER_PATH = "uapi/domestic-stock/v1/trading/order-cash"
        private const val ORDERS_PATH = "uapi/domestic-stock/v1/trading/inquire-daily-ccld"
        private const val CANCEL_PATH = "uapi/domestic-stock/v1/trading/order-rvsecncl"
        private const val DAILY_TR = "FHKST01010400" // 모의·실전 공통
        private const val MARKET = "01"
        private const val MAX_PAGES = 20
        private val MORE = setOf("F", "M")
        private val DATE = DateTimeFormatter.BASIC_ISO_DATE

        fun create(
            env: KisEnvironment,
            credentials: KisCredentials,
            account: Account,
            tokens: TokenStore,
            baseUrl: HttpUrl = env.baseUrl.toHttpUrl(),
            okHttp: OkHttpClient = defaultOkHttp(),
            clock: Clock = Clock.system(KisHttp.KST),
            sleeper: Sleeper = Sleeper.THREAD,
        ) = KisClient(KisHttp(okHttp, baseUrl, env, credentials, tokens, clock, sleeper), env, account)

        /** OkHttp의 연결 실패 자동 재전송을 끈다 — 주문 POST가 중복 접수될 수 있다. 재시도는 [KisHttp]만 한다. */
        fun defaultOkHttp(): OkHttpClient = OkHttpClient.Builder()
            .retryOnConnectionFailure(false)
            .connectTimeout(Duration.ofSeconds(10))
            .readTimeout(Duration.ofSeconds(15))
            .writeTimeout(Duration.ofSeconds(15))
            .build()

        private fun requireCode(code: String) =
            require(code.length == 6 && code.all(Char::isLetterOrDigit)) { "종목코드는 6자리: $code" }
    }
}

private fun JsonObject.text(key: String) = string(key).orEmpty()

/** 주문 응답 output은 대문자 키, 문서 예시와 달리 소문자로 올 때도 대비한다. */
private fun JsonObject.upper(key: String) = (string(key) ?: string(key.lowercase())).orEmpty()
    .ifBlank { throw KisException.Malformed("$key 없음") }

private fun JsonObject.rows(key: String): List<JsonObject> = when (val v = this[key]) {
    null -> emptyList()
    is JsonArray -> v.map { it.jsonObject }
    else -> throw KisException.Malformed("$key 가 배열이 아님")
}

private fun JsonObject.single(key: String): JsonObject = when (val v = this[key]) {
    is JsonObject -> v
    is JsonArray -> v.firstOrNull()?.jsonObject ?: throw KisException.Malformed("$key 비어 있음")
    else -> throw KisException.Malformed("$key 없음")
}

/** KIS 숫자는 문자열. 빈 값은 0, 숫자가 아니면 [KisException.Malformed]. */
private fun JsonObject.decimal(key: String): BigDecimal {
    val raw = text(key).trim()
    if (raw.isEmpty()) return BigDecimal.ZERO
    return raw.toBigDecimalOrNull() ?: throw KisException.Malformed("$key 숫자 아님")
}

private fun JsonObject.won(key: String): Long = decimal(key).toLong()

private fun JsonObject.qty(key: String): Int = decimal(key).toInt()
