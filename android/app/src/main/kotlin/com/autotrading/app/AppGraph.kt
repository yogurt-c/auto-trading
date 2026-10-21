package com.autotrading.app

import android.content.Context
import com.autotrading.core.TradingCalendar
import com.autotrading.engine.FileRunStore
import com.autotrading.engine.KisBroker
import com.autotrading.engine.MonthlyRun
import com.autotrading.engine.MonthlyRunner
import com.autotrading.engine.MonthlyRunner.Companion.KST
import com.autotrading.engine.RunCoordinator
import com.autotrading.engine.RunSchedule
import com.autotrading.kis.KisClient
import com.autotrading.kis.KisEnvironment
import com.autotrading.kis.Sleeper
import java.io.File
import java.time.Clock
import java.time.Duration
import java.time.Instant
import java.time.YearMonth

/** 수동 의존성 연결 (설계: DI 없음). [TradingApp]이 하나만 만든다. */
class AppGraph(context: Context) {
    val calendar: TradingCalendar = TradingCalendar.bundled()
    val runs = FileRunStore(File(context.filesDir, "runs"))
    val secrets = SecretsStore(SecretBox(File(context.filesDir, "kis.bin"), "kis_secrets"))
    val tokens = KeystoreTokenStore(SecretBox(File(context.filesDir, "token.bin"), "kis_token"))
    val settings = Settings(context.getSharedPreferences("settings", Context.MODE_PRIVATE))
    val alarms = Alarms(context)
    val notifier = Notifier(context)
    val clock: Clock = Clock.system(KST)
    private val schedule = RunSchedule(calendar)
    private val coordinator = RunCoordinator(schedule, clock)

    fun client(secrets: KisSecrets): KisClient =
        KisClient.create(ENV, secrets.credentials, secrets.account, tokens)

    fun month(): YearMonth = YearMonth.from(clock.instant().atZone(KST))

    /** 읽을 수 없으면 null — 실행은 engine에서 다시 읽다 실패해 오류 알림으로 드러난다. */
    fun currentRun(): MonthlyRun? = runCatching { runs.load(month()) }.getOrNull()

    /** 부팅·앱 실행·설정 변경 때. 자동 실행이 켜져 있고 키·성향이 있으면 다음 알람을 건다. */
    fun reschedule() {
        if (!settings.autoRun || secrets.load() == null || settings.profile == null) {
            alarms.cancel()
            settings.nextRunAt = null
            return
        }
        arm(schedule.onWake(currentRun(), clock.instant()))
    }

    /** 실행 도중 프로세스가 죽어도 이어서 진행하도록 미리 걸어 두는 알람. 정상 종료 시 다음 일정으로 바뀐다. */
    fun armWatchdog() {
        if (settings.autoRun) alarms.set(clock.instant().plus(WATCHDOG))
    }

    /** [RunService]의 작업 스레드에서 호출한다 (블로킹, 최대 약 1시간). [retry]면 실패한 이번 달을 다시 시도한다. */
    fun runOnce(retry: Boolean) {
        val secrets = secrets.load()
        val profile = settings.profile
        if (secrets == null || profile == null) {
            settings.status = "KIS 키와 투자 성향을 먼저 설정하세요"
            reschedule() // watchdog 알람을 지운다
            return
        }
        val report = coordinator.run(settings.autoRun) {
            val runner = MonthlyRunner(
                KisBroker(client(secrets)), runs, calendar, clock, Sleeper.THREAD, ENV, realTradingUnlocked = false,
            )
            if (retry) runner.retry(month(), profile) else runner.execute(month(), profile)
        }
        val text = Messages.of(report.outcome).text
        settings.status = text
        val next = report.nextRunAt
        if (next != null) arm(next) else settings.nextRunAt = null
        when {
            report.unexpectedError != null -> notifier.error(text)
            report.notify -> notifier.result(text)
        }
    }

    private fun arm(at: Instant) {
        alarms.set(at)
        settings.nextRunAt = at
    }

    companion object {
        /** 실전은 이 버전에서 잠겨 있다 — 모의투자만. */
        val ENV = KisEnvironment.PAPER
        private val WATCHDOG: Duration = Duration.ofMinutes(15)
    }
}
