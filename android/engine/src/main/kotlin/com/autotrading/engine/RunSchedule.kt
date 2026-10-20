package com.autotrading.engine

import com.autotrading.core.TradingCalendar
import com.autotrading.engine.MonthlyRunner.Companion.KST
import java.time.Instant
import java.time.LocalDate
import java.time.LocalTime
import java.time.YearMonth

/**
 * 다음 실행 시각 (설계 문서 5절). app은 이 시각에 정확한 알람을 건다.
 * 실행은 항상 "그 시각이 속한 달"의 run을 진행한다 — 지난달 run이 끝나지 않은 채 달이 바뀌면 새 달 run이 이어받는다.
 */
class RunSchedule(private val calendar: TradingCalendar) {
    fun after(outcome: Outcome, now: Instant): Instant = when (outcome) {
        is Outcome.Done, is Outcome.Failed -> firstRunOf(YearMonth.from(now.atZone(KST)).plusMonths(1))
        is Outcome.Postponed -> runAt(outcome.date)
        is Outcome.RetryLater -> maxOf(outcome.at, now)
    }

    /**
     * 부팅·앱 실행·자동 실행 켜기 때. 이번 달 run이 끝났으면 다음 달 첫 거래일,
     * 아니면 장중이면 지금, 장 시작 전이면 오늘 [RUN_AT], 그 외에는 다음 거래일 [RUN_AT].
     */
    fun onWake(current: MonthlyRun?, now: Instant): Instant {
        val local = now.atZone(KST)
        if (current?.isFinished == true) return firstRunOf(YearMonth.from(local).plusMonths(1))
        val today = local.toLocalDate()
        if (calendar.isTradingDay(today)) {
            val time = local.toLocalTime()
            if (time.isBefore(RUN_AT)) return runAt(today)
            if (time.isBefore(MonthlyRunner.SEND_UNTIL)) return now
        }
        return runAt(calendar.nextTradingDay(today))
    }

    fun firstRunOf(month: YearMonth): Instant = runAt(calendar.firstTradingDay(month))

    private fun runAt(date: LocalDate): Instant = date.atTime(RUN_AT).atZone(KST).toInstant()

    companion object {
        /** 장 시작 직후 호가가 안정된 뒤 (설계: 매월 첫 거래일 09:10). */
        val RUN_AT: LocalTime = LocalTime.of(9, 10)
    }
}
