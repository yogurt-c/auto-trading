package com.autotrading.app

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent

class AlarmReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        try {
            RunService.start(context)
        } catch (_: IllegalStateException) {
            // 정확한 알람 권한이 없어 백그라운드 시작이 막힘 (ForegroundServiceStartNotAllowedException)
            val graph = (context.applicationContext as TradingApp).graph
            graph.settings.status = "알람으로 실행하지 못했습니다 — 앱을 열어 '지금 실행'을 누르세요"
            graph.notifier.result(graph.settings.status.orEmpty())
        }
    }
}

/** 재부팅·앱 업데이트 때 알람이 지워지므로 다시 건다. 여기서 바로 실행하지 않는다 (Android 15는 부팅 시 dataSync 시작 금지). */
class BootReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action != Intent.ACTION_BOOT_COMPLETED && intent.action != Intent.ACTION_MY_PACKAGE_REPLACED) return
        (context.applicationContext as TradingApp).graph.reschedule()
    }
}
