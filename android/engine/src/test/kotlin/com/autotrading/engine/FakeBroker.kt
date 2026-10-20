package com.autotrading.engine

import com.autotrading.core.Side
import com.autotrading.kis.Balance
import com.autotrading.kis.DailyBar
import com.autotrading.kis.KisException
import com.autotrading.kis.OrderReceipt
import com.autotrading.kis.OrderStatus
import com.autotrading.kis.Position
import com.autotrading.kis.Sleeper
import java.time.Clock
import java.time.Instant
import java.time.LocalDate
import java.time.LocalDateTime
import java.time.ZoneId

class FakeTime(start: LocalDateTime) : Clock(), Sleeper {
    var now: Instant = start.atZone(MonthlyRunner.KST).toInstant()
    val sleeps = mutableListOf<Long>()

    fun set(time: LocalDateTime) {
        now = time.atZone(MonthlyRunner.KST).toInstant()
    }

    override fun sleep(millis: Long) {
        sleeps += millis
        now = now.plusMillis(millis)
    }

    override fun instant(): Instant = now
    override fun getZone(): ZoneId = MonthlyRunner.KST
    override fun withZone(zone: ZoneId?): Clock = this
}

/**
 * 가짜 증권사. 주문은 [fill]에 따라 즉시 체결(매도는 현재가, 매수는 현재가)되거나 미체결로 남는다.
 * [failNext]로 다음 호출 하나에 오류를 주입한다. "accept:" 접두어면 주문은 접수하고 응답만 잃는다.
 */
class FakeBroker(private val time: FakeTime) : Broker {
    enum class Fill { NOW, NEVER }

    val positions = mutableMapOf<String, Int>()
    var cash = 0L
    var prevClose = mapOf<String, Long>()
    var current = mapOf<String, Long>()
    var prevDate: LocalDate = LocalDate.of(2026, 10, 30)
    var openToday = true
    var fill = Fill.NOW
    val failNext = mutableMapOf<String, KisException>()
    val calls = mutableListOf<String>()
    private val orders = mutableListOf<OrderStatus>()
    private val orderDates = mutableMapOf<String, LocalDate>()

    val placed: List<OrderStatus> get() = orders.filter { it.originalOrderNo == null }

    private fun today() = time.instant().atZone(MonthlyRunner.KST).toLocalDate()

    private fun maybeFail(call: String) {
        calls += call
        failNext.remove(call)?.let { throw it }
    }

    override fun balance(): Balance {
        maybeFail("balance")
        return Balance(positions.filterValues { it > 0 }.map { (c, q) -> Position(c, q, q) }, cash)
    }

    override fun buyingPower(): Long {
        maybeFail("buyingPower")
        return cash
    }

    override fun dailyBars(code: String): List<DailyBar> {
        maybeFail("dailyBars")
        val prev = DailyBar(prevDate, prevClose.getValue(code))
        return if (openToday) listOf(DailyBar(today(), current.getValue(code)), prev) else listOf(prev)
    }

    override fun sellMarket(code: String, qty: Int): OrderReceipt {
        check(qty <= (positions[code] ?: 0)) { "보유 수량 초과 매도" }
        return order(code, Side.SELL, qty, current.getValue(code))
    }

    override fun buyLimit(code: String, qty: Int, price: Long): OrderReceipt {
        check(price >= current.getValue(code)) { "지정가가 현재가보다 낮다" }
        check(qty * price <= cash) { "주문가능금액 초과" }
        return order(code, Side.BUY, qty, current.getValue(code))
    }

    private fun order(code: String, side: Side, qty: Int, price: Long): OrderReceipt {
        val lost = failNext.remove("accept:$side")
        maybeFail("order:$side")
        val no = "%010d".format(orders.size + 1)
        val filled = if (fill == Fill.NOW) qty else 0
        orders += OrderStatus(no, "06010", null, code, side, qty, filled, 0, 0, if (filled > 0) price.toDouble() else 0.0)
        orderDates[no] = today()
        settle(code, side, filled, price)
        lost?.let { throw it }
        return OrderReceipt(no, "06010", code, side, qty)
    }

    private fun settle(code: String, side: Side, qty: Int, price: Long) {
        val sign = if (side == Side.BUY) 1 else -1
        positions[code] = (positions[code] ?: 0) + sign * qty
        cash -= sign * qty * price
    }

    override fun orders(date: LocalDate): List<OrderStatus> {
        maybeFail("orders")
        return orders.filter { orderDates[it.orderNo] == date }
    }

    override fun cancel(receipt: OrderReceipt) {
        maybeFail("cancel")
        val i = orders.indexOfFirst { it.orderNo == receipt.orderNo }
        val o = orders[i]
        orders[i] = o.copy(canceledQty = o.openQty)
        orders += o.copy(orderNo = "C${o.orderNo}", originalOrderNo = o.orderNo, orderedQty = o.openQty, filledQty = 0)
    }

    /** 장 마감: 미체결 당일 주문은 소멸한다. */
    fun closeDay() {
        orders.replaceAll { if (it.openQty > 0) it.copy(canceledQty = it.openQty) else it }
    }
}
