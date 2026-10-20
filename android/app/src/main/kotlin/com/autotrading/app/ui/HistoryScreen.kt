package com.autotrading.app.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.unit.dp
import com.autotrading.engine.MonthlyRun

@Composable
fun HistoryScreen(history: List<MonthlyRun>) {
    LazyColumn(contentPadding = PaddingValues(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        if (history.isEmpty()) item { Text("아직 실행 기록이 없습니다.") }
        items(history, key = { it.month.toString() }) { RunCard("기록", it) }
    }
}
