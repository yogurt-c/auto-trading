package com.autotrading.engine

import com.autotrading.core.Side
import com.autotrading.kis.Balance
import com.autotrading.kis.DailyBar
import com.autotrading.kis.KisClient
import com.autotrading.kis.OrderReceipt
import com.autotrading.kis.OrderStatus
import java.time.LocalDate

/** engine이 쓰는 증권사 기능. 테스트는 가짜 구현으로 각 단계 중단·재시작을 재현한다. */
interface Broker {
    fun balance(): Balance
    fun buyingPower(): Long
    fun dailyBars(code: String): List<DailyBar>
    fun sellMarket(code: String, qty: Int): OrderReceipt
    fun buyLimit(code: String, qty: Int, price: Long): OrderReceipt
    fun orders(date: LocalDate): List<OrderStatus>
    fun cancel(receipt: OrderReceipt)
}

class KisBroker(private val kis: KisClient) : Broker {
    override fun balance() = kis.balance()
    override fun buyingPower() = kis.buyingPower()
    override fun dailyBars(code: String) = kis.dailyBars(code)
    override fun sellMarket(code: String, qty: Int) = kis.placeMarketOrder(code, Side.SELL, qty)
    override fun buyLimit(code: String, qty: Int, price: Long) = kis.placeLimitOrder(code, Side.BUY, qty, price)
    override fun orders(date: LocalDate) = kis.orders(date)
    override fun cancel(receipt: OrderReceipt) {
        kis.cancel(receipt)
    }
}

/** KRX ETF 호가단위: 2,000원 미만 1원, 이상 5원. */
internal object EtfTick {
    fun ceil(price: Double): Long {
        val tick = if (price < 2_000) 1L else 5L
        return kotlin.math.ceil(price / tick).toLong() * tick
    }
}
