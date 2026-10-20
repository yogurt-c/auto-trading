package com.autotrading.core

import kotlin.math.floor

enum class Side { SELL, BUY }

data class OrderIntent(val code: String, val side: Side, val qty: Int)

/**
 * 월 리밸런싱 주문 계획. 기준 구현: research/src/research/rebalance.py (shared/fixtures/rebalance).
 *
 * 1. [plan]: 전일 종가로 목표 수량과 매도 주문을 계산한다.
 * 2. 매도 체결 후 실제 예수금으로 [planBuys]를 호출한다. 목표 수량은 1단계 값을 그대로 쓴다.
 *
 * 관리 대상은 [managedCodes](성향 ETF 전체)뿐이다. 계좌의 다른 종목은 총자산에도 넣지 않는다.
 */
class RebalancePlanner(
    private val cashBuffer: Double = CASH_BUFFER,
    private val minOrderFraction: Double = MIN_ORDER_FRACTION,
    private val costReserve: Double = COST_RESERVE,
    private val managedCodes: Set<String> = Etf.codes,
) {
    data class Plan(val equity: Double, val targets: Map<String, Int>, val sells: List<OrderIntent>)

    fun plan(
        weights: Map<String, Double>,
        holdings: Map<String, Int>,
        prices: Map<String, Double>,
        cash: Double,
    ): Plan {
        require(weights.keys.all { it in managedCodes }) { "관리 대상이 아닌 종목: ${weights.keys - managedCodes}" }
        val equity = managedEquity(holdings, prices, cash)
        val targets = targetShares(weights, equity, prices)
        return Plan(equity, targets, planSells(holdings, targets, prices, equity))
    }

    fun managedEquity(holdings: Map<String, Int>, prices: Map<String, Double>, cash: Double): Double =
        cash + holdings.filterKeys { it in managedCodes }.entries.sumOf { (code, qty) -> qty * price(prices, code) }

    fun targetShares(weights: Map<String, Double>, equity: Double, prices: Map<String, Double>): Map<String, Int> {
        val budget = equity * (1 - cashBuffer)
        return weights.filterValues { it > 0 }.toSortedMap()
            .mapValues { (code, w) -> floor(budget * w / price(prices, code)).toInt() }
    }

    /** 목표보다 많은 수량을 매도. 성향에서 빠진 관리 종목은 금액과 무관하게 전량 매도. */
    fun planSells(
        holdings: Map<String, Int>,
        targets: Map<String, Int>,
        prices: Map<String, Double>,
        equity: Double,
    ): List<OrderIntent> = holdings.toSortedMap().mapNotNull { (code, held) ->
        if (code !in managedCodes) return@mapNotNull null
        val excess = held - (targets[code] ?: 0)
        when {
            excess <= 0 -> null
            code in targets && excess * price(prices, code) < equity * minOrderFraction -> null
            else -> OrderIntent(code, Side.SELL, excess)
        }
    }

    /** 목표보다 적은 수량을 매수 (종목코드 순). 예수금이 모자라면 뒤 종목부터 줄어든다. */
    fun planBuys(
        holdings: Map<String, Int>,
        targets: Map<String, Int>,
        prices: Map<String, Double>,
        cash: Double,
        equity: Double,
    ): List<OrderIntent> {
        var remaining = cash
        return targets.toSortedMap().mapNotNull { (code, target) ->
            val p = price(prices, code)
            val shortfall = target - (holdings[code] ?: 0)
            if (shortfall <= 0 || shortfall * p < equity * minOrderFraction) return@mapNotNull null
            val unit = p * (1 + costReserve)
            val qty = minOf(shortfall, floor(remaining / unit).toInt())
            if (qty <= 0) return@mapNotNull null
            remaining -= qty * unit
            OrderIntent(code, Side.BUY, qty)
        }
    }

    private fun price(prices: Map<String, Double>, code: String): Double {
        val p = requireNotNull(prices[code]) { "가격 없음: $code" }
        require(p > 0) { "가격이 0 이하: $code=$p" }
        return p
    }

    companion object {
        const val CASH_BUFFER = 0.005
        const val MIN_ORDER_FRACTION = 0.01
        const val COST_RESERVE = 0.002
    }
}
