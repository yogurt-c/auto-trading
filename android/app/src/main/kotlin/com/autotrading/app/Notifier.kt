package com.autotrading.app

import android.Manifest
import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import androidx.core.content.ContextCompat
import com.autotrading.app.ui.MainActivity

/** 알림에는 키·토큰·계좌번호를 넣지 않는다 — 결과와 사유만. */
class Notifier(private val context: Context) {
    fun createChannels() {
        val manager = context.getSystemService(NotificationManager::class.java)
        manager.createNotificationChannel(
            NotificationChannel(RUNNING, "리밸런싱 진행 중", NotificationManager.IMPORTANCE_LOW),
        )
        manager.createNotificationChannel(
            NotificationChannel(RESULT, "리밸런싱 결과", NotificationManager.IMPORTANCE_DEFAULT),
        )
    }

    fun running(): Notification = NotificationCompat.Builder(context, RUNNING)
        .setSmallIcon(R.drawable.ic_notify)
        .setContentTitle("월 리밸런싱 실행 중")
        .setContentText("주문·체결 확인 중입니다 (최대 1시간)")
        .setOngoing(true)
        .setContentIntent(openApp())
        .build()

    fun result(text: String) = post(RESULT_ID, text, alertOnce = false)

    /** 예상하지 못한 오류 — 10분마다 재시도하므로 같은 알림을 갱신만 하고 소리는 한 번만. */
    fun error(text: String) = post(ERROR_ID, text, alertOnce = true)

    private fun post(id: Int, text: String, alertOnce: Boolean) {
        val allowed = Build.VERSION.SDK_INT < Build.VERSION_CODES.TIRAMISU ||
            ContextCompat.checkSelfPermission(context, Manifest.permission.POST_NOTIFICATIONS) ==
            PackageManager.PERMISSION_GRANTED
        if (!allowed) return
        val notification = NotificationCompat.Builder(context, RESULT)
            .setSmallIcon(R.drawable.ic_notify)
            .setContentTitle("월 리밸런싱")
            .setContentText(text)
            .setStyle(NotificationCompat.BigTextStyle().bigText(text))
            .setAutoCancel(true)
            .setOnlyAlertOnce(alertOnce)
            .setContentIntent(openApp())
            .build()
        NotificationManagerCompat.from(context).notify(id, notification)
    }

    private fun openApp(): PendingIntent = PendingIntent.getActivity(
        context,
        0,
        Intent(context, MainActivity::class.java),
        PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT,
    )

    companion object {
        const val RUNNING_ID = 1
        private const val RESULT_ID = 2
        private const val ERROR_ID = 3
        private const val RUNNING = "running"
        private const val RESULT = "result"
    }
}
