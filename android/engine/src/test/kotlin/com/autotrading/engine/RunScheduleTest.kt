package com.autotrading.engine

import com.autotrading.core.Profile
import com.autotrading.core.TradingCalendar
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.io.TempDir
import java.io.File
import java.time.Instant
import java.time.LocalDate
import java.time.LocalDateTime
import java.time.YearMonth

class RunScheduleTest {
    private val schedule = RunSchedule(TradingCalendar.bundled())
    private val nov = YearMonth.of(2026, 11)

    private fun at(text: String): Instant = LocalDateTime.parse(text).atZone(MonthlyRunner.KST).toInstant()

    @Test
    fun `끝난 run은 다음 달 첫 거래일 09시10분`() {
        val done = Outcome.Done(MonthlyRun(nov, Profile.STABLE, RunState.DONE))
        val failed = Outcome.Failed(MonthlyRun(nov, Profile.STABLE, RunState.FAILED))

        assertEquals(at("2026-12-01T09:10"), schedule.after(done, at("2026-11-02T09:40")))
        assertEquals(at("2026-12-01T09:10"), schedule.after(failed, at("2026-11-02T09:40")))
    }

    @Test
    fun `연기는 그날 09시10분, 재시도는 지정 시각`() {
        val now = at("2026-11-02T09:40")

        assertEquals(at("2026-11-03T09:10"), schedule.after(Outcome.Postponed(LocalDate.of(2026, 11, 3)), now))
        assertEquals(at("2026-11-02T09:42"), schedule.after(Outcome.RetryLater(at("2026-11-02T09:42"), "x"), now))
        assertEquals(now, schedule.after(Outcome.RetryLater(at("2026-11-02T09:00"), "x"), now), "지난 시각이면 바로")
    }

    @Test
    fun `깨어났을 때 이번 달이 안 끝났으면 장중엔 지금, 장 전엔 09시10분, 마감 후엔 다음 거래일`() {
        val pending = MonthlyRun(nov, Profile.STABLE, RunState.SELLS_SENT)

        assertEquals(at("2026-11-02T11:00"), schedule.onWake(pending, at("2026-11-02T11:00")))
        assertEquals(at("2026-11-02T11:00"), schedule.onWake(null, at("2026-11-02T11:00")))
        assertEquals(at("2026-11-02T09:10"), schedule.onWake(null, at("2026-11-02T07:00")))
        assertEquals(at("2026-11-03T09:10"), schedule.onWake(pending, at("2026-11-02T15:30")))
        assertEquals(at("2026-11-09T09:10"), schedule.onWake(null, at("2026-11-07T10:00")), "토요일")
    }

    @Test
    fun `깨어났을 때 이번 달이 끝났으면 다음 달 첫 거래일 (휴장 건너뜀)`() {
        val done = MonthlyRun(YearMonth.of(2026, 2), Profile.STABLE, RunState.DONE)

        // 3/1 일요일, 3/2 삼일절 대체공휴일
        assertEquals(at("2026-03-03T09:10"), schedule.onWake(done, at("2026-02-20T10:00")))
    }
}

class FileRunStoreTest {
    @TempDir
    lateinit var dir: File

    @Test
    fun `달마다 파일 하나에 저장하고 덮어쓰며 기록은 최근 달부터`() {
        val store = FileRunStore(dir)
        val oct = MonthlyRun(YearMonth.of(2026, 10), Profile.STABLE, RunState.DONE)
        val nov = MonthlyRun(YearMonth.of(2026, 11), Profile.CONSERVATIVE)

        store.save(oct)
        store.save(nov)
        store.save(nov.copy(state = RunState.PLANNED))

        assertEquals(RunState.PLANNED, FileRunStore(dir).load(nov.month)?.state)
        assertEquals(listOf(nov.month, oct.month), store.all().map { it.month })
        assertEquals(null, store.load(YearMonth.of(2026, 9)))
        assertEquals(setOf("run-2026-10.json", "run-2026-11.json"), dir.list()!!.toSet(), "임시 파일이 남지 않는다")
    }
}
