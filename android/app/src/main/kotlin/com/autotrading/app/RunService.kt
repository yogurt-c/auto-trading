package com.autotrading.app

import android.annotation.SuppressLint
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.os.IBinder
import androidx.core.app.ServiceCompat
import androidx.core.content.ContextCompat
import java.util.concurrent.atomic.AtomicBoolean
import kotlin.concurrent.thread

/**
 * 월 실행을 foreground service로 돌린다 — 체결 대기(최대 30분 x 2) 동안 시스템이 프로세스를 끄지 않게.
 * 이미 실행 중이면 새 요청은 무시하고 watchdog 알람만 미룬다.
 */
class RunService : Service() {
    override fun onBind(intent: Intent?): IBinder? = null

    @SuppressLint("InlinedApi") // ServiceCompat은 API 29 미만에서 type을 무시한다
    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        val graph = (application as TradingApp).graph
        ServiceCompat.startForeground(
            this,
            Notifier.RUNNING_ID,
            graph.notifier.running(),
            ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC,
        )
        graph.armWatchdog()
        if (running.compareAndSet(false, true)) {
            thread(name = "monthly-run") {
                try {
                    graph.runOnce(retry = intent?.getBooleanExtra(EXTRA_RETRY, false) == true)
                } finally {
                    running.set(false)
                    stopSelf()
                }
            }
        }
        return START_NOT_STICKY
    }

    companion object {
        private val running = AtomicBoolean(false)

        val isRunning: Boolean get() = running.get()

        /** 화면(앞에 있을 때)이나 정확한 알람에서만 부른다 — 그 외 백그라운드 시작은 Android 12+에서 막힌다. */
        fun start(context: Context, retry: Boolean = false) {
            val intent = Intent(context, RunService::class.java).putExtra(EXTRA_RETRY, retry)
            ContextCompat.startForegroundService(context, intent)
        }

        private const val EXTRA_RETRY = "retry"
    }
}
