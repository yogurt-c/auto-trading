package com.autotrading.app

import com.autotrading.core.Etf
import com.autotrading.core.Profile
import com.autotrading.engine.MonthlyRunner.Companion.KST
import com.autotrading.engine.Outcome
import com.autotrading.engine.RunSchedule
import com.autotrading.engine.RunState
import java.time.Instant
import java.time.format.DateTimeFormatter
import java.util.Locale

/** 화면·알림 문구. */
object Messages {
    data class Status(val text: String, val notify: Boolean)

    private val DATE_TIME = DateTimeFormatter.ofPattern("M/d(E) HH:mm", Locale.KOREAN)
    private val DATE = DateTimeFormatter.ofPattern("M/d(E)", Locale.KOREAN)

    fun of(outcome: Outcome): Status = when (outcome) {
        is Outcome.Done -> Status("${outcome.run.month.monthValue}월 리밸런싱 완료 — 주문 ${outcome.run.orders.size}건", true)
        is Outcome.Failed -> Status("${outcome.run.month.monthValue}월 리밸런싱 실패: ${outcome.run.failure}", true)
        is Outcome.Postponed ->
            Status("휴장이거나 장 마감이 가까워 ${outcome.date.format(DATE)} ${RunSchedule.RUN_AT}에 다시 실행합니다", true)
        is Outcome.RetryLater -> Status("${time(outcome.at)}에 다시 시도합니다 (${outcome.reason})", false)
    }

    fun time(at: Instant): String = at.atZone(KST).format(DATE_TIME)

    fun profile(profile: Profile): String = when (profile) {
        Profile.STABLE -> "안정형"
        Profile.CONSERVATIVE -> "보수형"
    }

    fun etf(code: String): String = Etf.entries.firstOrNull { it.code == code }?.displayName ?: code

    fun state(state: RunState): String = when (state) {
        RunState.SCHEDULED -> "대기"
        RunState.CHECKED_OPEN -> "개장 확인"
        RunState.PLANNED -> "주문 계획"
        RunState.SELLS_SENT -> "매도 체결 대기"
        RunState.SELLS_SETTLED -> "매도 완료"
        RunState.BUYS_SENT -> "매수 체결 대기"
        RunState.DONE -> "완료"
        RunState.FAILED -> "실패"
    }

    fun won(amount: Double): String = "%,.0f원".format(amount)
}
