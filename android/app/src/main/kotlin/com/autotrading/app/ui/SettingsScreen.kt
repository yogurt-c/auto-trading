package com.autotrading.app.ui

import android.content.Intent
import android.provider.Settings
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp

@Composable
fun SettingsScreen(state: UiState, onResetKeys: () -> Unit) {
    val context = LocalContext.current
    var confirmReset by remember { mutableStateOf(false) }
    Column(
        Modifier.verticalScroll(rememberScrollState()).padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Section("계좌") {
            Text("모의투자 · ${state.maskedAccount}")
            OutlinedButton(onClick = { confirmReset = true }, enabled = !state.running) { Text("키·계좌 다시 입력") }
        }
        Section("실전 매매") {
            Text("잠김")
            Muted("이 버전은 모의투자만 지원합니다. 모의투자로 최소 2회 월 실행을 확인한 뒤 열 예정입니다.")
        }
        Section("배터리 최적화") {
            Muted("절전 모드에서 알람이 늦어질 수 있습니다. 이 앱을 '최적화하지 않음'으로 두세요.")
            OutlinedButton(onClick = { context.startActivity(Intent(Settings.ACTION_IGNORE_BATTERY_OPTIMIZATION_SETTINGS)) }) {
                Text("배터리 최적화 설정 열기")
            }
        }
    }
    if (confirmReset) {
        AlertDialog(
            onDismissRequest = { confirmReset = false },
            title = { Text("키·계좌를 지울까요?") },
            text = { Text("자동 실행이 꺼집니다. 실행 기록은 남습니다.") },
            confirmButton = {
                TextButton(onClick = {
                    confirmReset = false
                    onResetKeys()
                }) { Text("지우기") }
            },
            dismissButton = { TextButton(onClick = { confirmReset = false }) { Text("취소") } },
        )
    }
}
