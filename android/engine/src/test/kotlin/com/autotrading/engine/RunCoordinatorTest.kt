package com.autotrading.engine

import com.autotrading.core.Profile
import com.autotrading.core.TradingCalendar
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertFalse
import org.junit.jupiter.api.Assertions.assertNull
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.Test
import java.io.IOException
import java.time.LocalDateTime
import java.time.YearMonth

class RunCoordinatorTest {
    private val time = FakeTime(LocalDateTime.of(2026, 11, 2, 9, 40))
    private val coordinator = RunCoordinator(RunSchedule(TradingCalendar.bundled()), time)
    private val nov = YearMonth.of(2026, 11)

    private fun at(text: String) = LocalDateTime.parse(text).atZone(MonthlyRunner.KST).toInstant()

    @Test
    fun `완료는 알리고 다음 달 첫 거래일로`() {
        val report = coordinator.run(autoRun = true) { Outcome.Done(MonthlyRun(nov, Profile.STABLE, RunState.DONE)) }

        assertTrue(report.notify)
        assertEquals(at("2026-12-01T09:10"), report.nextRunAt)
    }

    @Test
    fun `일시 오류 재시도는 알리지 않는다`() {
        val report = coordinator.run(autoRun = true) { Outcome.RetryLater(at("2026-11-02T09:42"), "x") }

        assertFalse(report.notify)
        assertEquals(at("2026-11-02T09:42"), report.nextRunAt)
    }

    @Test
    fun `예상하지 못한 예외는 10분 뒤 재시도로 바꾸고 알리되 메시지는 남기지 않는다`() {
        val report = coordinator.run(autoRun = true) { throw IOException("appsecret=leak") }

        assertTrue(report.notify)
        assertEquals("IOException", report.unexpectedError)
        assertEquals(at("2026-11-02T09:50"), report.nextRunAt)
        assertFalse(report.outcome.toString().contains("leak"))
    }

    @Test
    fun `자동 실행이 꺼져 있으면 알람을 걸지 않는다`() {
        val report = coordinator.run(autoRun = false) { Outcome.Postponed(java.time.LocalDate.of(2026, 11, 3)) }

        assertNull(report.nextRunAt)
        assertTrue(report.notify)
    }

    @Test
    fun `끝나지 못한 채 달이 바뀐 run은 중단된 것으로 본다`() {
        val stuck = MonthlyRun(YearMonth.of(2026, 10), Profile.STABLE, RunState.BUYS_SENT)

        assertTrue(stuck.isAbandoned(nov))
        assertFalse(stuck.isAbandoned(YearMonth.of(2026, 10)))
        assertFalse(stuck.copy(state = RunState.DONE).isAbandoned(nov))
    }
}
