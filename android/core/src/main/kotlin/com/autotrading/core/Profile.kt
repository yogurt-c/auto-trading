package com.autotrading.core

/** 앱이 주문하는 국내 상장 ETF. 이 3종목 외에는 주문하지 않는다. */
enum class Etf(val code: String, val displayName: String) {
    KODEX_200("069500", "KODEX 200"),
    TIGER_US_SP500("360750", "TIGER 미국S&P500"),
    KODEX_KTB_3Y("114260", "KODEX 국고채3년"),
    ;

    companion object {
        val codes: Set<String> = entries.map { it.code }.toSet()
    }
}

/**
 * 투자 성향 — 목표 비중. 근거: research/reports/r4_summary.md
 * shared/fixtures/profiles/app_profiles.json과 일치해야 한다 (ProfileTest).
 */
enum class Profile(val weights: Map<Etf, Double>) {
    STABLE(mapOf(Etf.KODEX_200 to 0.5, Etf.TIGER_US_SP500 to 0.5)),
    CONSERVATIVE(mapOf(Etf.KODEX_200 to 0.25, Etf.TIGER_US_SP500 to 0.25, Etf.KODEX_KTB_3Y to 0.5)),
    ;

    val weightsByCode: Map<String, Double> get() = weights.mapKeys { it.key.code }
}
