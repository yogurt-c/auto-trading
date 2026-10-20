package com.autotrading.app

import android.app.Application

class TradingApp : Application() {
    lateinit var graph: AppGraph
        private set

    override fun onCreate() {
        super.onCreate()
        graph = AppGraph(this)
        graph.notifier.createChannels()
    }
}
