package com.autotrading.app.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.autotrading.app.Messages
import com.autotrading.core.Profile

/**
 * 성향별 과거 수치 (research/reports/r4_summary.md). 기대 수익률은 표시하지 않는다 (설계 7절) —
 * 최근 구간 수익률은 국내 급등장 영향이 커서 낙폭·회복 기간만 보여준다.
 */
private val HISTORY = mapOf(
    Profile.STABLE to listOf(
        "장기(2000–2019) 최대 낙폭 -40.8%, 회복까지 최장 2,066일(약 5년 8개월)",
        "최악의 해 2008년 -30%",
        "최근(2020–2026.9) 최대 낙폭 -28.2%, 최악의 해 2022년 -19%",
    ),
    Profile.CONSERVATIVE to listOf(
        "장기(2000–2019) 최대 낙폭 -19.3%, 회복까지 최장 689일(약 1년 11개월)",
        "최근(2020–2026.9) 최대 낙폭 -14.6%, 최악의 해 2022년 -11%",
    ),
)

@Composable
fun ProfileScreen(state: UiState, onSelect: (Profile) -> Unit, modifier: Modifier) {
    Column(
        modifier.verticalScroll(rememberScrollState()).padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Text("투자 성향", style = MaterialTheme.typography.headlineSmall)
        Muted("매월 첫 거래일에 아래 비중으로 맞춥니다. 성향 변경은 한 달에 한 번이며, 이번 달 실행이 이미 시작됐으면 다음 달부터 반영됩니다.")
        Profile.entries.forEach { profile ->
            Section(Messages.profile(profile)) {
                Text(profile.weights.entries.joinToString(" · ") { "${it.key.displayName} ${(it.value * 100).toInt()}%" })
                HISTORY[profile].orEmpty().forEach { Muted(it) }
                val selected = state.profile == profile
                val enabled = !selected && state.canChangeProfile
                if (selected) {
                    OutlinedButton(onClick = {}, enabled = false, modifier = Modifier.fillMaxWidth()) { Text("사용 중") }
                } else {
                    Button(onClick = { onSelect(profile) }, enabled = enabled, modifier = Modifier.fillMaxWidth()) {
                        Text(if (state.canChangeProfile) "이 성향 사용" else "이번 달은 이미 변경함")
                    }
                }
            }
        }
        Muted("과거 수치는 미래 수익을 보장하지 않습니다. 장기 구간의 채권은 단기 금리로 합성한 값입니다.")
    }
}
