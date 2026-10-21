package com.autotrading.engine

import java.time.Clock
import java.time.Duration
import java.time.Instant

/**
 * 한 번 실행하고 다음 알람 시각·알림 여부를 정한다. app의 RunService는 [Report]를 그대로 적용한다.
 * engine이 처리하지 못한 예외(파일 I/O·버그)도 여기서 잡아 [UNEXPECTED_RETRY] 뒤 재시도로 바꾸고 알린다.
 */
class RunCoordinator(private val schedule: RunSchedule, private val clock: Clock) {
    data class Report(
        val outcome: Outcome,
        /** null이면 알람을 걸지 않는다 (자동 실행 꺼짐). */
        val nextRunAt: Instant?,
        val notify: Boolean,
        /** 예상하지 못한 예외의 종류. 메시지에는 비밀이 섞일 수 있어 남기지 않는다. */
        val unexpectedError: String? = null,
    )

    fun run(autoRun: Boolean, execute: () -> Outcome): Report {
        var unexpected: String? = null
        val outcome = try {
            execute()
        } catch (e: Exception) {
            unexpected = e.javaClass.simpleName
            Outcome.RetryLater(clock.instant().plus(UNEXPECTED_RETRY), "예상하지 못한 오류: $unexpected")
        }
        return Report(
            outcome = outcome,
            nextRunAt = if (autoRun) schedule.after(outcome, clock.instant()) else null,
            notify = unexpected != null || outcome !is Outcome.RetryLater,
            unexpectedError = unexpected,
        )
    }

    companion object {
        val UNEXPECTED_RETRY: Duration = Duration.ofMinutes(10)
    }
}
