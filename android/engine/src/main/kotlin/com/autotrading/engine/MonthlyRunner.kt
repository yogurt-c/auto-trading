package com.autotrading.engine

import com.autotrading.core.Etf
import com.autotrading.core.Profile
import com.autotrading.core.RebalancePlanner
import com.autotrading.core.Side
import com.autotrading.core.TradingCalendar
import com.autotrading.kis.KisEnvironment
import com.autotrading.kis.KisException
import com.autotrading.kis.OrderReceipt
import com.autotrading.kis.Sleeper
import java.time.Clock
import java.time.Duration
import java.time.Instant
import java.time.LocalDate
import java.time.LocalTime
import java.time.YearMonth
import java.time.ZoneId

sealed interface Outcome {
    data class Done(val run: MonthlyRun) : Outcome

    /** 사유는 [MonthlyRun.failure]. 알림 대상. */
    data class Failed(val run: MonthlyRun) : Outcome

    /** 휴장일이거나 장 마감이 가까움 — [date] 09:10에 다시 실행한다. */
    data class Postponed(val date: LocalDate) : Outcome

    /** 일시 오류(네트워크·호출 한도·토큰 발급 제한) 또는 장 시작 전 — [at]에 다시 실행한다. */
    data class RetryLater(val at: Instant, val reason: String) : Outcome
}

/**
 * 월 리밸런싱 실행 (설계 문서 4절). [execute]는 몇 번을 다시 불러도 안전하다:
 * - 단계마다 [RunStore]에 저장하고, 주문은 보내기 **전에** 기록한다
 * - 전송 결과를 모르는 주문은 주문체결조회로 접수 여부를 확인한 뒤에만 다시 보낸다
 * - 거래일이 바뀌면 남은 주문을 정리하고 그날 잔고로 처음부터 다시 계획한다
 *
 * 불변조건: 주문 종목은 성향 ETF 3종만, 하루 주문 ≤ [MAX_DAILY_ORDERS]건, 매수 총액 ≤ 매수가능금액,
 * 매도 수량 ≤ 주문가능수량, 실전은 잠금 해제 시에만 생성 가능.
 */
class MonthlyRunner(
    private val broker: Broker,
    private val store: RunStore,
    private val calendar: TradingCalendar,
    private val clock: Clock,
    private val sleeper: Sleeper,
    env: KisEnvironment,
    realTradingUnlocked: Boolean,
    private val planner: RebalancePlanner = RebalancePlanner(),
) {
    init {
        require(env == KisEnvironment.PAPER || realTradingUnlocked) { "실전 매매는 잠겨 있습니다" }
    }

    private sealed interface Step {
        data class Next(val run: MonthlyRun) : Step
        data class Stop(val outcome: Outcome) : Step
    }

    /** 이번 달 run이 없으면 [profile]로 만든다. 이미 있으면 만들 때의 성향을 그대로 쓴다. */
    fun execute(month: YearMonth, profile: Profile): Outcome {
        var run = store.load(month) ?: MonthlyRun(month, profile).also(store::save)
        while (true) {
            when (run.state) {
                RunState.DONE -> return Outcome.Done(run)
                RunState.FAILED -> return Outcome.Failed(run)
                else -> Unit
            }
            val step = try {
                advance(run)
            } catch (e: KisException) {
                return handle(month, run, e)
            } catch (e: IllegalStateException) {
                return fail(store.load(month) ?: run, e.message ?: "불변조건 위반")
            } catch (e: IllegalArgumentException) {
                return fail(store.load(month) ?: run, e.message ?: "잘못된 입력")
            }
            when (step) {
                is Step.Next -> run = step.run.also(store::save)
                is Step.Stop -> return step.outcome
            }
        }
    }

    private fun advance(run: MonthlyRun): Step {
        val today = today()
        if (run.tradeDate != null && run.tradeDate != today) return Step.Next(rollover(run, run.tradeDate))
        return when (run.state) {
            RunState.SCHEDULED -> checkOpen(run, today)
            RunState.CHECKED_OPEN -> plan(run)
            RunState.PLANNED -> send(run, today, run.plannedSells.orEmpty(), RunState.SELLS_SENT)
            RunState.SELLS_SENT -> awaitSettled(run, today, Side.SELL)
            RunState.SELLS_SETTLED -> send(planBuys(run, today), today, null, RunState.BUYS_SENT)
            RunState.BUYS_SENT -> awaitSettled(run, today, Side.BUY)
            RunState.DONE, RunState.FAILED -> error("종료된 run: ${run.state}")
        }
    }

    /** 휴장 확인: 내장 달력 + 오늘 시세 줄 유무(달력에 없는 해·임시 휴장). 전일 종가를 저장한다. */
    private fun checkOpen(run: MonthlyRun, today: LocalDate): Step {
        if (!calendar.isTradingDay(today)) return Step.Stop(Outcome.Postponed(calendar.nextTradingDay(today)))
        tradingWindow(today)?.let { return Step.Stop(it) }
        val bars = Etf.entries.associate { it.code to broker.dailyBars(it.code) }
        if (bars.values.none { rows -> rows.any { it.date == today } }) {
            return Step.Stop(Outcome.Postponed(calendar.nextTradingDay(today)))
        }
        val prevClose = bars.mapValues { (code, rows) ->
            checkNotNull(rows.firstOrNull { it.date < today }) { "전일 종가 없음: $code" }.close.toDouble()
        }
        return Step.Next(run.copy(state = RunState.CHECKED_OPEN, tradeDate = today, prevClose = prevClose))
    }

    private fun plan(run: MonthlyRun): Step {
        val balance = broker.balance()
        val holdings = balance.positions.associate { it.code to it.qty }
        val plan = planner.plan(run.profile.weightsByCode, holdings, run.prevClose, balance.depositD2.toDouble())
        for (sell in plan.sells) {
            val orderable = balance.positions.firstOrNull { it.code == sell.code }?.orderableQty ?: 0
            check(sell.qty <= orderable) { "매도가능수량 부족: ${sell.code} ${sell.qty}주 > ${orderable}주" }
        }
        return Step.Next(
            run.copy(
                state = RunState.PLANNED,
                equity = plan.equity,
                targets = plan.targets,
                plannedSells = plan.sells.map(::PlannedOrder),
            ),
        )
    }

    /**
     * 매수는 매도 체결 후 실제 매수가능금액으로 한 번만 계획해 저장한다 (다시 계산하면 이미 보낸 매수를 또 살 수 있다).
     * 시장가 매수는 상한가 기준으로 주문금액을 잡으므로, 오늘 현재가 + [BUY_PREMIUM] 지정가로 즉시 체결시킨다.
     */
    private fun planBuys(run: MonthlyRun, today: LocalDate): MonthlyRun {
        if (run.plannedBuys != null) return run
        tradingWindow(today)?.let { return run } // send()에서 다시 확인해 멈춘다
        val holdings = broker.balance().positions.associate { it.code to it.qty }
        val cash = broker.buyingPower()
        val limits = run.targets.keys.associateWith { code ->
            val now = broker.dailyBars(code).firstOrNull { it.date == today }?.close?.toDouble()
                ?: checkNotNull(run.prevClose[code]) { "가격 없음: $code" }
            EtfTick.ceil(now * (1 + BUY_PREMIUM))
        }
        val buys = planner.planBuys(holdings, run.targets, limits.mapValues { it.value.toDouble() }, cash.toDouble(), run.equity)
        val total = buys.sumOf { it.qty * limits.getValue(it.code) }
        check(total <= cash) { "매수 총액 $total > 매수가능금액 $cash" }
        return run.copy(plannedBuys = buys.map { PlannedOrder(it, limits.getValue(it.code)) }).also(store::save)
    }

    /** 계획된 주문 중 아직 보내지 않은 것만 보낸다. [planned]가 null이면 run.plannedBuys. */
    private fun send(run: MonthlyRun, today: LocalDate, planned: List<PlannedOrder>?, next: RunState): Step {
        tradingWindow(today)?.let { return Step.Stop(it) }
        var r = reconcile(run, today)
        for (order in planned ?: r.plannedBuys.orEmpty()) {
            if (r.orders.none { it.date == today && it.code == order.code && it.side == order.side }) {
                r = place(r, today, order)
            }
        }
        return Step.Next(r.copy(state = next, phaseStartedAt = clock.instant()))
    }

    private fun place(run: MonthlyRun, today: LocalDate, order: PlannedOrder): MonthlyRun {
        check(order.code in Etf.codes) { "성향 ETF가 아닌 종목 주문: ${order.code}" }
        check(run.orders.count { it.date == today } < MAX_DAILY_ORDERS) { "하루 주문 ${MAX_DAILY_ORDERS}건 초과" }
        val record = OrderRecord(today, order.code, order.side, order.qty, order.limitPrice)
        val sending = run.copy(orders = run.orders + record).also(store::save)
        val receipt = try {
            when (order.side) {
                Side.SELL -> broker.sellMarket(order.code, order.qty)
                Side.BUY -> broker.buyLimit(order.code, order.qty, checkNotNull(order.limitPrice) { "매수 지정가 없음" })
            }
        } catch (e: KisException.Rejected) {
            store.save(run) // 거부 = 접수되지 않음. 기록을 지운다
            throw e
        }
        val sent = record.copy(orderNo = receipt.orderNo, orgNo = receipt.orgNo)
        return sending.copy(orders = run.orders + sent).also(store::save)
    }

    /**
     * 전송 결과를 모르는 주문을 KIS 주문 목록과 맞춘다. 같은 종목·방향·수량의 아직 짝이 없는 주문이 있으면
     * 접수된 것으로, 없으면 접수되지 않은 것으로 보고 기록을 지운다 (다음 단계에서 다시 보낸다).
     */
    private fun reconcile(run: MonthlyRun, date: LocalDate): MonthlyRun {
        if (run.orders.none { it.date == date && it.orderNo == null }) return run
        val claimed = run.orders.mapNotNull { it.orderNo }.toMutableSet()
        val kisOrders = broker.orders(date).filter { it.originalOrderNo == null }
        val orders = run.orders.mapNotNull { record ->
            if (record.date != date || record.orderNo != null) return@mapNotNull record
            val match = kisOrders.firstOrNull {
                it.orderNo !in claimed && it.code == record.code && it.side == record.side && it.orderedQty == record.qty
            } ?: return@mapNotNull null
            claimed += match.orderNo
            record.copy(orderNo = match.orderNo, orgNo = match.orgNo)
        }
        return run.copy(orders = orders).also(store::save)
    }

    private fun refresh(run: MonthlyRun, date: LocalDate): MonthlyRun {
        val statuses = broker.orders(date).associateBy { it.orderNo }
        val orders = run.orders.map { record ->
            val status = statuses[record.orderNo]
            if (record.date != date || status == null) {
                record
            } else {
                record.copy(filledQty = status.filledQty, avgPrice = status.avgPrice, open = !status.isSettled)
            }
        }
        return run.copy(orders = orders).also(store::save)
    }

    /** 체결조회 폴링 (최대 [SETTLE_TIMEOUT]). 시간 안에 체결되지 않으면 잔량을 취소하고 FAILED. */
    private fun awaitSettled(run: MonthlyRun, today: LocalDate, side: Side): Step {
        var r = reconcile(run, today)
        val sendState = if (side == Side.SELL) RunState.PLANNED else RunState.SELLS_SETTLED
        val planned = if (side == Side.SELL) r.plannedSells.orEmpty() else r.plannedBuys.orEmpty()
        if (planned.any { p -> r.orders.none { it.date == today && it.code == p.code && it.side == side } }) {
            return Step.Next(r.copy(state = sendState)) // 접수되지 않은 주문이 있다 — 다시 보낸다
        }
        val next = if (side == Side.SELL) RunState.SELLS_SETTLED else RunState.DONE
        val deadline = checkNotNull(r.phaseStartedAt) { "phaseStartedAt 없음" }.plus(SETTLE_TIMEOUT)
        while (true) {
            r = refresh(r, today)
            val open = r.orders.filter { it.date == today && it.side == side && it.open }
            if (open.isEmpty()) return Step.Next(r.copy(state = next, phaseStartedAt = null))
            if (!clock.instant().isBefore(deadline)) return cancelAndFail(r, today, side, open)
            sleeper.sleep(POLL.toMillis())
        }
    }

    private fun cancelAndFail(run: MonthlyRun, today: LocalDate, side: Side, open: List<OrderRecord>): Step {
        for (record in open) {
            try {
                broker.cancel(OrderReceipt(checkNotNull(record.orderNo), record.orgNo, record.code, record.side, record.qty))
            } catch (_: KisException.Rejected) {
                // 그 사이 체결돼 취소할 잔량이 없을 수 있다 — 아래 재조회로 판단
            }
        }
        val r = refresh(run, today)
        val unfilled = r.orders.filter { it.date == today && it.side == side && it.filledQty < it.qty }
        if (unfilled.isEmpty()) {
            val next = if (side == Side.SELL) RunState.SELLS_SETTLED else RunState.DONE
            return Step.Next(r.copy(state = next, phaseStartedAt = null))
        }
        val detail = unfilled.joinToString { "${it.code} ${it.filledQty}/${it.qty}주" }
        return Step.Next(r.copy(state = RunState.FAILED, failure = "${SETTLE_TIMEOUT.toMinutes()}분 내 미체결, 잔량 취소: $detail"))
    }

    /** 거래일이 지났다: 그날 주문을 확정하고(당일 주문은 장 마감에 소멸) 오늘 잔고로 처음부터 다시 계획한다. */
    private fun rollover(run: MonthlyRun, day: LocalDate): MonthlyRun {
        val reconciled = refresh(reconcile(run, day), day)
        val orders = reconciled.orders.map { if (it.date == day) it.copy(open = false) else it }
        return MonthlyRun(run.month, run.profile, orders = orders)
    }

    /** 새 주문은 [OPEN_AT]~[SEND_UNTIL] 사이에만 보낸다. */
    private fun tradingWindow(today: LocalDate): Outcome? {
        val time = clock.instant().atZone(KST).toLocalTime()
        return when {
            time.isBefore(OPEN_AT) -> Outcome.RetryLater(today.atTime(OPEN_AT).atZone(KST).toInstant(), "장 시작 전")
            !time.isBefore(SEND_UNTIL) -> Outcome.Postponed(calendar.nextTradingDay(today))
            else -> null
        }
    }

    private fun handle(month: YearMonth, run: MonthlyRun, e: KisException): Outcome {
        val latest = store.load(month) ?: run
        return when (e) {
            is KisException.Transport, is KisException.RateLimited, is KisException.TokenIssueLimited ->
                Outcome.RetryLater(clock.instant().plus(RETRY_DELAY), e.message.orEmpty())
            is KisException.Rejected, is KisException.Auth, is KisException.Malformed -> fail(latest, e.message.orEmpty())
        }
    }

    private fun fail(run: MonthlyRun, reason: String): Outcome {
        val failed = run.copy(state = RunState.FAILED, failure = reason).also(store::save)
        return Outcome.Failed(failed)
    }

    private fun today(): LocalDate = clock.instant().atZone(KST).toLocalDate()

    companion object {
        val KST: ZoneId = ZoneId.of("Asia/Seoul")
        val OPEN_AT: LocalTime = LocalTime.of(9, 5)
        val SEND_UNTIL: LocalTime = LocalTime.of(15, 0)
        val POLL: Duration = Duration.ofSeconds(10)
        val SETTLE_TIMEOUT: Duration = Duration.ofMinutes(30)
        val RETRY_DELAY: Duration = Duration.ofMinutes(2)
        const val BUY_PREMIUM = 0.01
        const val MAX_DAILY_ORDERS = 6
    }
}
