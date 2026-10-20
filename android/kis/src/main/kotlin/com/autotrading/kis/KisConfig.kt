package com.autotrading.kis

/**
 * 모의/실전 도메인·TR_ID·호출 간격. 실전 잠금은 engine에서 검증한다 (kis는 전송만 담당).
 * 호출 한도: 실전 초당 20건, 모의 초당 2건 — 여유를 두고 간격을 띄운다.
 */
enum class KisEnvironment(
    val baseUrl: String,
    internal val minIntervalMillis: Long,
    internal val balanceTr: String,
    internal val buyingPowerTr: String,
    internal val sellTr: String,
    internal val buyTr: String,
    internal val ordersTr: String,
    internal val cancelTr: String,
) {
    PAPER(
        baseUrl = "https://openapivts.koreainvestment.com:29443",
        minIntervalMillis = 550,
        balanceTr = "VTTC8434R",
        buyingPowerTr = "VTTC8908R",
        sellTr = "VTTC0011U",
        buyTr = "VTTC0012U",
        ordersTr = "VTTC0081R",
        cancelTr = "VTTC0013U",
    ),
    REAL(
        baseUrl = "https://openapi.koreainvestment.com:9443",
        minIntervalMillis = 60,
        balanceTr = "TTTC8434R",
        buyingPowerTr = "TTTC8908R",
        sellTr = "TTTC0011U",
        buyTr = "TTTC0012U",
        ordersTr = "TTTC0081R",
        cancelTr = "TTTC0013U",
    ),
}

/** 앱키·시크릿. toString으로 값이 새지 않게 한다. */
class KisCredentials(val appKey: String, val appSecret: String) {
    init {
        require(appKey.isNotBlank() && appSecret.isNotBlank()) { "앱키와 시크릿을 입력해야 합니다" }
    }

    override fun toString() = "KisCredentials(****)"
}

/** 계좌번호 8-2 체계. 화면·로그에는 [masked]만 쓴다. */
data class Account(val cano: String, val productCode: String = "01") {
    init {
        require(cano.length == 8 && cano.all(Char::isDigit)) { "계좌번호 앞 8자리는 숫자여야 합니다" }
        require(productCode.length == 2 && productCode.all(Char::isDigit)) { "계좌상품코드는 숫자 2자리여야 합니다" }
    }

    val masked: String get() = "${cano.take(2)}****${cano.takeLast(2)}-$productCode"

    override fun toString() = "Account($masked)"

    companion object {
        /** "12345678" 또는 "12345678-01". 상품코드 생략 시 01. */
        fun parse(text: String): Account {
            val parts = text.trim().split("-")
            require(parts.size in 1..2) { "계좌번호 형식이 잘못되었습니다" }
            return if (parts.size == 2) Account(parts[0], parts[1]) else Account(parts[0])
        }
    }
}
