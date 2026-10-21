package com.autotrading.app.ui

import android.content.Intent
import android.os.Build
import android.provider.Settings
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import com.autotrading.app.Messages
import com.autotrading.engine.MonthlyRun
import com.autotrading.engine.RunState
import java.time.YearMonth

@Composable
fun HomeScreen(state: UiState, onAutoRun: (Boolean) -> Unit, onRunNow: () -> Unit, onRetry: () -> Unit) {
    Column(
        Modifier.verticalScroll(rememberScrollState()).padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Text("모의투자 · ${state.maskedAccount}", style = MaterialTheme.typography.labelLarge)
        state.profile?.let { Text("${Messages.profile(it)} 성향", style = MaterialTheme.typography.headlineSmall) }

        Section("자동 실행") {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text("매월 첫 거래일 09:10", Modifier.weight(1f))
                Switch(checked = state.autoRun, onCheckedChange = onAutoRun)
            }
            Text(
                when {
                    state.running -> "지금 실행 중"
                    state.nextRunAt != null -> "다음 실행: ${Messages.time(state.nextRunAt)}"
                    else -> "꺼짐"
                },
            )
            Muted("켤 때 장중이고 이번 달 실행이 끝나지 않았으면 바로 리밸런싱합니다.")
        }

        if (!state.exactAlarmAllowed) ExactAlarmWarning()

        state.status?.let { Section("최근 결과") { Text(it) } }

        Button(onClick = onRunNow, enabled = !state.running, modifier = Modifier.fillMaxWidth()) {
            Text(if (state.running) "실행 중…" else "지금 실행")
        }
        Muted("새 주문은 09:05~15:00에만 보냅니다. 이번 달이 이미 끝났으면 아무것도 하지 않습니다.")

        if (state.current?.state == RunState.FAILED) {
            OutlinedButton(onClick = onRetry, enabled = !state.running, modifier = Modifier.fillMaxWidth()) {
                Text("이번 달 다시 시도")
            }
            Muted("미체결 주문이 남아 있지 않을 때만, 오늘 잔고로 처음부터 다시 계획합니다. 이전 주문 기록은 남습니다.")
        }

        state.current?.let { RunCard("이번 달", it, state.month) }
    }
}

@Composable
private fun ExactAlarmWarning() {
    val context = LocalContext.current
    Section("정확한 알람 권한 필요") {
        Text("권한이 없으면 정해진 시각에 자동 실행되지 않을 수 있습니다.", color = MaterialTheme.colorScheme.error)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            OutlinedButton(onClick = { context.startActivity(Intent(Settings.ACTION_REQUEST_SCHEDULE_EXACT_ALARM)) }) {
                Text("권한 설정 열기")
            }
        }
    }
}

/** 한 달 실행 요약 + 주문·체결 목록. 기록 화면에서도 쓴다. */
@Composable
fun RunCard(title: String, run: MonthlyRun, current: YearMonth) {
    Section("$title · ${run.month} · ${Messages.state(run, current)}") {
        Muted("${Messages.profile(run.profile)}${run.tradeDate?.let { " · 거래일 $it" }.orEmpty()}")
        if (run.equity > 0) Text("총자산 ${Messages.won(run.equity)}")
        if (run.targets.isNotEmpty()) {
            Text("목표: " + run.targets.entries.joinToString { "${Messages.etf(it.key)} ${it.value}주" })
        }
        run.orders.forEach { o ->
            val side = if (o.side.name == "BUY") "매수" else "매도"
            val price = if (o.avgPrice > 0) " @ ${Messages.won(o.avgPrice)}" else ""
            val open = if (o.open) " (미체결)" else ""
            Text("${o.date} $side ${Messages.etf(o.code)} ${o.filledQty}/${o.qty}주$price$open")
        }
        run.failure?.let { Text(it, color = MaterialTheme.colorScheme.error) }
    }
}
