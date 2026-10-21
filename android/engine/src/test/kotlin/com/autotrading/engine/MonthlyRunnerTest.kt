package com.autotrading.engine

import com.autotrading.core.Profile
import com.autotrading.core.Side
import com.autotrading.core.TradingCalendar
import com.autotrading.kis.KisEnvironment
import com.autotrading.kis.KisException
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertInstanceOf
import org.junit.jupiter.api.Assertions.assertNull
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.assertThrows
import java.time.LocalDate
import java.time.LocalDateTime
import java.time.YearMonth

private const val KODEX200 = "069500"
private const val SP500 = "360750"
private const val KTB3Y = "114260"
private val NOV: YearMonth = YearMonth.of(2026, 11)

class MonthlyRunnerTest {
    private val time = FakeTime(LocalDateTime.of(2026, 11, 2, 9, 10)) // 11월 첫 거래일(월)
    private val broker = FakeBroker(time).apply {
        prevClose = mapOf(KODEX200 to 35_215L, SP500 to 21_870L, KTB3Y to 113_405L)
        current = mapOf(KODEX200 to 35_300L, SP500 to 21_900L, KTB3Y to 113_400L)
    }
    private val store = InMemoryRunStore()
    private val calendar = TradingCalendar.bundled()

    private fun runner(env: KisEnvironment = KisEnvironment.PAPER, unlocked: Boolean = false) =
        MonthlyRunner(broker, store, calendar, time, time, env, unlocked)

    private fun execute(profile: Profile = Profile.STABLE) = runner().execute(NOV, profile)

    @Test
    fun `첫 투자는 현금으로 목표 비중만큼 지정가 매수하고 끝난다`() {
        broker.cash = 10_000_000

        val outcome = execute()

        val run = assertInstanceOf(Outcome.Done::class.java, outcome).run
        assertEquals(mapOf(KODEX200 to 141, SP500 to 227), run.targets)
        // 지정가 = 현재가 x 1.01을 5원 단위로 올림
        assertEquals(listOf(KODEX200 to 35_655L, SP500 to 22_120L), run.orders.map { it.code to it.limitPrice })
        assertTrue(run.orders.all { it.side == Side.BUY && !it.open && it.filledQty == it.qty })
        assertEquals(141, broker.positions[KODEX200])
        assertTrue(broker.positions.getValue(SP500) in 220..227)
        assertEquals(RunState.DONE, store.load(NOV)?.state)
    }

    @Test
    fun `성향 변경은 빠진 종목을 먼저 팔고 체결 뒤 매수한다`() {
        broker.positions += mapOf(KODEX200 to 141, SP500 to 227)
        broker.cash = 50_000

        val run = assertInstanceOf(Outcome.Done::class.java, execute(Profile.CONSERVATIVE)).run

        assertEquals(listOf("SELL" to KODEX200, "SELL" to SP500, "BUY" to KTB3Y), run.orders.map { it.side.name to it.code })
        val firstBuy = broker.calls.indexOf("order:BUY")
        assertTrue(broker.calls.subList(0, firstBuy).contains("buyingPower"), "매수 전 매도 체결 후 매수가능금액 조회")
        assertTrue(broker.positions.getValue(KTB3Y) > 0)
    }

    @Test
    fun `계좌의 다른 종목은 총자산에도 넣지 않고 주문하지 않는다`() {
        broker.positions += mapOf("005930" to 100)
        broker.current += mapOf("005930" to 60_000L)
        broker.cash = 10_000_000

        val run = assertInstanceOf(Outcome.Done::class.java, execute()).run

        assertTrue(run.orders.none { it.code == "005930" })
        assertEquals(10_000_000.0, run.equity)
        assertEquals(100, broker.positions["005930"])
    }

    @Test
    fun `내장 달력의 휴장일이면 다음 거래일로 미루고 KIS를 부르지 않는다`() {
        time.set(LocalDateTime.of(2026, 10, 9, 9, 10)) // 한글날

        assertEquals(Outcome.Postponed(LocalDate.of(2026, 10, 12)), execute())
        assertTrue(broker.calls.isEmpty())
    }

    @Test
    fun `달력에 없는 해는 오늘 시세가 없으면 휴장으로 보고 미룬다`() {
        time.set(LocalDateTime.of(2027, 1, 1, 9, 10)) // 2027 휴장일은 아직 내장 안 함
        broker.openToday = false

        assertEquals(Outcome.Postponed(LocalDate.of(2027, 1, 4)), runner().execute(YearMonth.of(2027, 1), Profile.STABLE))
        assertEquals(RunState.SCHEDULED, store.load(YearMonth.of(2027, 1))?.state)
    }

    @Test
    fun `장 시작 전이면 09시05분에 다시, 15시 이후면 다음 거래일로`() {
        time.set(LocalDateTime.of(2026, 11, 2, 8, 50))
        val early = assertInstanceOf(Outcome.RetryLater::class.java, execute())
        assertEquals(LocalDateTime.of(2026, 11, 2, 9, 5).atZone(MonthlyRunner.KST).toInstant(), early.at)

        time.set(LocalDateTime.of(2026, 11, 2, 15, 0))
        assertEquals(Outcome.Postponed(LocalDate.of(2026, 11, 3)), execute())
    }

    @Test
    fun `주문 응답을 잃어도 재실행 때 체결조회로 찾아 다시 주문하지 않는다`() {
        broker.cash = 10_000_000
        broker.failNext["accept:BUY"] = KisException.Transport("read timeout")

        assertInstanceOf(Outcome.RetryLater::class.java, execute())
        assertNull(store.load(NOV)?.orders?.single()?.orderNo, "전송 결과 미확인으로 저장")

        val run = assertInstanceOf(Outcome.Done::class.java, execute()).run

        assertEquals(2, broker.placed.size)
        assertEquals(broker.placed.map { it.orderNo }, run.orders.map { it.orderNo })
    }

    @Test
    fun `주문이 접수되지 않았으면 재실행 때 한 번만 다시 보낸다`() {
        broker.cash = 10_000_000
        broker.failNext["order:BUY"] = KisException.Transport("connect failed")

        assertInstanceOf(Outcome.RetryLater::class.java, execute())
        assertInstanceOf(Outcome.Done::class.java, execute())

        assertEquals(listOf(KODEX200, SP500), broker.placed.map { it.code })
    }

    @Test
    fun `매도 체결이 30분 안에 안 되면 잔량을 취소하고 실패`() {
        broker.positions += mapOf(KODEX200 to 141, SP500 to 227)
        broker.cash = 50_000
        broker.fill = FakeBroker.Fill.NEVER

        val run = assertInstanceOf(Outcome.Failed::class.java, execute(Profile.CONSERVATIVE)).run

        assertTrue(run.failure.orEmpty().startsWith("30분 내 미체결"), run.failure)
        assertEquals(2, broker.calls.count { it == "cancel" })
        assertTrue(broker.placed.none { it.side == Side.BUY })
        assertEquals(MonthlyRunner.SETTLE_TIMEOUT.toMillis(), time.sleeps.sum())
    }

    @Test
    fun `주문 거부는 기록을 지우고 사유와 함께 실패`() {
        broker.cash = 10_000_000
        broker.failNext["order:BUY"] = KisException.Rejected("40250000", "주문가능금액을 초과했습니다")

        val run = assertInstanceOf(Outcome.Failed::class.java, execute()).run

        assertEquals("[40250000] 주문가능금액을 초과했습니다", run.failure)
        assertTrue(run.orders.isEmpty())
        assertInstanceOf(Outcome.Failed::class.java, execute(), "실패한 run은 다시 주문하지 않는다")
        assertTrue(broker.placed.isEmpty())
    }

    @Test
    fun `다음 거래일에 재개하면 전날 주문을 확정하고 오늘 잔고로 다시 계획한다`() {
        broker.positions += mapOf(KODEX200 to 141, SP500 to 227)
        broker.cash = 50_000
        broker.fill = FakeBroker.Fill.NEVER
        broker.failNext["orders"] = KisException.Transport("앱 종료 대신 네트워크 끊김")
        assertInstanceOf(Outcome.RetryLater::class.java, execute(Profile.CONSERVATIVE))
        assertEquals(RunState.SELLS_SENT, store.load(NOV)?.state)

        broker.closeDay()
        broker.fill = FakeBroker.Fill.NOW
        broker.prevDate = LocalDate.of(2026, 11, 2)
        time.set(LocalDateTime.of(2026, 11, 3, 9, 10))
        val run = assertInstanceOf(Outcome.Done::class.java, execute()).run

        assertEquals(LocalDate.of(2026, 11, 3), run.tradeDate)
        assertEquals(Profile.CONSERVATIVE, run.profile, "만들 때의 성향 유지")
        assertTrue(run.orders.filter { it.date == LocalDate.of(2026, 11, 2) }.none { it.open })
        assertTrue(broker.positions.getValue(KTB3Y) > 0)
    }

    @Test
    fun `실패한 달은 그날 다시 시도하면 이전 주문과 구분해 새로 주문하고 완료한다`() {
        broker.positions += mapOf(KODEX200 to 141, SP500 to 227)
        broker.cash = 50_000
        broker.fill = FakeBroker.Fill.NEVER
        assertInstanceOf(Outcome.Failed::class.java, execute(Profile.CONSERVATIVE))
        assertInstanceOf(Outcome.Failed::class.java, execute(Profile.CONSERVATIVE), "execute는 실패한 run을 다시 진행하지 않는다")

        broker.fill = FakeBroker.Fill.NOW
        val run = assertInstanceOf(Outcome.Done::class.java, runner().retry(NOV, Profile.STABLE)).run

        assertEquals(Profile.CONSERVATIVE, run.profile, "실패한 run의 성향 유지")
        assertEquals(1, run.attempt)
        assertEquals(listOf(0, 0, 1, 1, 1), run.orders.map { it.attempt })
        assertTrue(run.orders.none { it.open })
        assertEquals(listOf(KODEX200, SP500, KODEX200, SP500, KTB3Y), broker.placed.map { it.code })
        assertTrue(broker.positions.getValue(KTB3Y) > 0)
    }

    @Test
    fun `취소되지 않은 미체결 주문이 남아 있으면 다시 시도하지 않는다`() {
        broker.positions += mapOf(KODEX200 to 141, SP500 to 227)
        broker.cash = 50_000
        broker.fill = FakeBroker.Fill.NEVER
        broker.failNext["cancel"] = KisException.Rejected("APBK0919", "취소 불가")
        assertInstanceOf(Outcome.Failed::class.java, execute(Profile.CONSERVATIVE))
        val placed = broker.placed.size

        val failed = assertInstanceOf(Outcome.Failed::class.java, runner().retry(NOV, Profile.CONSERVATIVE)).run

        assertTrue(failed.failure.orEmpty().startsWith("미체결 주문이 남아 있어"), failed.failure)
        assertEquals(placed, broker.placed.size)
        assertEquals(0, store.load(NOV)?.attempt, "저장된 run은 그대로")
    }

    @Test
    fun `다음 거래일에 다시 시도하면 전날 미체결은 소멸한 것으로 보고 진행한다`() {
        broker.positions += mapOf(KODEX200 to 141, SP500 to 227)
        broker.cash = 50_000
        broker.fill = FakeBroker.Fill.NEVER
        broker.failNext["cancel"] = KisException.Rejected("APBK0919", "취소 불가")
        assertInstanceOf(Outcome.Failed::class.java, execute(Profile.CONSERVATIVE))

        broker.fill = FakeBroker.Fill.NOW
        broker.prevDate = LocalDate.of(2026, 11, 2)
        time.set(LocalDateTime.of(2026, 11, 3, 9, 10))
        val run = assertInstanceOf(Outcome.Done::class.java, runner().retry(NOV, Profile.CONSERVATIVE)).run

        assertEquals(LocalDate.of(2026, 11, 3), run.tradeDate)
        assertTrue(broker.positions.getValue(KTB3Y) > 0)
    }

    @Test
    fun `실패하지 않은 달의 다시 시도는 일반 실행과 같다`() {
        broker.cash = 10_000_000

        assertInstanceOf(Outcome.Done::class.java, runner().retry(NOV, Profile.STABLE))
        assertInstanceOf(Outcome.Done::class.java, runner().retry(NOV, Profile.STABLE))
        assertEquals(2, broker.placed.size)
    }

    @Test
    fun `전일 종가가 없으면 주문 없이 실패`() {
        broker.cash = 10_000_000
        val run = MonthlyRunner(
            object : Broker by broker {
                override fun dailyBars(code: String) =
                    broker.dailyBars(code).filter { it.date == LocalDate.of(2026, 11, 2) }
            },
            store, calendar, time, time, KisEnvironment.PAPER, false,
        )

        val failed = assertInstanceOf(Outcome.Failed::class.java, run.execute(NOV, Profile.STABLE)).run
        assertTrue(failed.failure.orEmpty().startsWith("전일 종가 없음"), failed.failure)
        assertTrue(broker.placed.isEmpty())
    }

    @Test
    fun `실전은 잠금 해제 없이는 만들 수 없다`() {
        assertThrows<IllegalArgumentException> { runner(KisEnvironment.REAL) }
        runner(KisEnvironment.REAL, unlocked = true)
    }

    @Test
    fun `저장 형식은 JSON 왕복이 된다`() {
        broker.cash = 10_000_000
        val run = assertInstanceOf(Outcome.Done::class.java, execute()).run

        assertEquals(run, MonthlyRun.fromJson(run.toJson()))
    }

    @Test
    fun `ETF 지정가는 호가단위로 올림`() {
        assertEquals(35_655L, EtfTick.ceil(35_653.0))
        assertEquals(35_655L, EtfTick.ceil(35_655.0))
        assertEquals(1_999L, EtfTick.ceil(1_998.2))
    }
}
