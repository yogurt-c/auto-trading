package com.autotrading.app.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp

/** KIS 모의투자 키·계좌 입력. 저장 전에 잔고 조회로 확인한다. 입력값은 화면 회전 시에도 저장하지 않는다(remember). */
@Composable
fun SetupScreen(setup: SetupState, onSave: (appKey: String, appSecret: String, account: String) -> Unit) {
    var appKey by remember { mutableStateOf("") }
    var appSecret by remember { mutableStateOf("") }
    var account by remember { mutableStateOf("") }
    Column(
        Modifier.verticalScroll(rememberScrollState()).padding(24.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Text("KIS 모의투자 연결", style = MaterialTheme.typography.headlineSmall)
        Muted("한국투자증권 KIS Developers에서 발급한 모의투자 앱키·시크릿과 모의투자 계좌번호를 입력하세요. 이 기기의 Keystore로 암호화해 저장하며, 백업되지 않습니다.")
        Secret("앱키", appKey) { appKey = it }
        Secret("앱시크릿", appSecret) { appSecret = it }
        OutlinedTextField(
            value = account,
            onValueChange = { account = it },
            label = { Text("계좌번호 (12345678-01)") },
            singleLine = true,
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
            modifier = Modifier.fillMaxWidth(),
        )
        setup.error?.let { Text(it, color = MaterialTheme.colorScheme.error) }
        Button(
            onClick = { onSave(appKey, appSecret, account) },
            enabled = !setup.checking && appKey.isNotBlank() && appSecret.isNotBlank() && account.isNotBlank(),
            modifier = Modifier.fillMaxWidth(),
        ) {
            Text(if (setup.checking) "연결 확인 중…" else "연결 확인 후 저장")
        }
    }
}

@Composable
private fun Secret(label: String, value: String, onChange: (String) -> Unit) {
    OutlinedTextField(
        value = value,
        onValueChange = onChange,
        label = { Text(label) },
        singleLine = true,
        visualTransformation = PasswordVisualTransformation(),
        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Password, autoCorrectEnabled = false),
        modifier = Modifier.fillMaxWidth(),
    )
}
