package com.autotrading.app.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.unit.dp
import com.autotrading.engine.MonthlyRun
import java.time.YearMonth

@Composable
fun HistoryScreen(history: List<MonthlyRun>, unreadable: List<String>, current: YearMonth) {
    LazyColumn(contentPadding = PaddingValues(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        if (history.isEmpty() && unreadable.isEmpty()) item { Text("아직 실행 기록이 없습니다.") }
        if (unreadable.isNotEmpty()) {
            item { Text("읽을 수 없는 기록: ${unreadable.joinToString()}", color = MaterialTheme.colorScheme.error) }
        }
        items(history, key = { it.month.toString() }) { RunCard("기록", it, current) }
    }
}
