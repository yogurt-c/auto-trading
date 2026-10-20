package com.autotrading.app

import android.app.AlarmManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.os.Build
import java.time.Instant

/** 실행 알람 1개. 다시 걸면 이전 알람을 대체한다. 울리면 [AlarmReceiver]가 [RunService]를 시작한다. */
class Alarms(private val context: Context) {
    private val manager = context.getSystemService(AlarmManager::class.java)

    /** 정확한 알람이어야 알람에서 foreground service를 시작할 수 있다 (Android 12+). 13+는 USE_EXACT_ALARM으로 항상 허용. */
    val canScheduleExact: Boolean
        get() = Build.VERSION.SDK_INT < Build.VERSION_CODES.S || manager.canScheduleExactAlarms()

    fun set(at: Instant) {
        if (canScheduleExact) {
            manager.setExactAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, at.toEpochMilli(), intent())
        } else {
            manager.setAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, at.toEpochMilli(), intent())
        }
    }

    fun cancel() = manager.cancel(intent())

    private fun intent(): PendingIntent = PendingIntent.getBroadcast(
        context,
        0,
        Intent(context, AlarmReceiver::class.java),
        PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT,
    )
}
