package com.autotrading.app.ui

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.autotrading.app.KisSecrets
import com.autotrading.app.Messages
import com.autotrading.app.RunService
import com.autotrading.app.TradingApp
import com.autotrading.core.Etf
import com.autotrading.core.Profile
import com.autotrading.engine.MonthlyRun
import com.autotrading.engine.MonthlyRunner.Companion.KST
import com.autotrading.kis.Account
import com.autotrading.kis.KisCredentials
import com.autotrading.kis.KisException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.time.Instant
import java.time.YearMonth

data class UiState(
    val loaded: Boolean = false,
    val maskedAccount: String? = null,
    val profile: Profile? = null,
    val canChangeProfile: Boolean = true,
    val autoRun: Boolean = false,
    val nextRunAt: Instant? = null,
    val status: String? = null,
    val running: Boolean = false,
    val exactAlarmAllowed: Boolean = true,
    val month: YearMonth = YearMonth.now(KST),
    val current: MonthlyRun? = null,
    val history: List<MonthlyRun> = emptyList(),
    /** 읽을 수 없는 실행 기록 파일 이름. */
    val unreadable: List<String> = emptyList(),
)

/** 키 입력 화면 상태. 키 값은 화면 입력란에만 있고 여기에는 결과 문구만 둔다. */
data class SetupState(val checking: Boolean = false, val error: String? = null)

class AppViewModel(application: Application) : AndroidViewModel(application) {
    private val graph = (application as TradingApp).graph
    private val _state = MutableStateFlow(UiState())
    val state: StateFlow<UiState> = _state.asStateFlow()
    private val _setup = MutableStateFlow(SetupState())
    val setup: StateFlow<SetupState> = _setup.asStateFlow()

    fun refresh() {
        viewModelScope.launch {
            _state.value = withContext(Dispatchers.IO) {
                try {
                    load()
                } catch (e: Exception) {
                    // 화면이 죽지 않게 이전 상태를 유지한다. 메시지에 비밀이 섞일 수 있어 종류만
                    _state.value.copy(loaded = true, status = "화면 정보를 읽지 못했습니다: ${e.javaClass.simpleName}")
                }
            }
        }
    }

    private fun load(): UiState {
        val settings = graph.settings
        val history = graph.runs.history()
        val month = graph.month()
        return UiState(
            loaded = true,
            maskedAccount = graph.secrets.load()?.account?.masked,
            profile = settings.profile,
            canChangeProfile = settings.canChangeProfile(graph.month()),
            autoRun = settings.autoRun,
            nextRunAt = settings.nextRunAt,
            status = settings.status,
            running = RunService.isRunning,
            exactAlarmAllowed = graph.alarms.canScheduleExact,
            month = month,
            current = history.runs.firstOrNull { it.month == month },
            history = history.runs,
            unreadable = history.unreadable,
        )
    }

    /** 잔고 조회로 키·계좌를 확인한 뒤에만 저장한다. 실패하면 토큰도 지운다. */
    fun saveKeys(appKey: String, appSecret: String, account: String) {
        _setup.value = SetupState(checking = true)
        viewModelScope.launch {
            val error = withContext(Dispatchers.IO) {
                try {
                    val secrets = KisSecrets(KisCredentials(appKey.trim(), appSecret.trim()), Account.parse(account))
                    graph.tokens.save(null)
                    val balance = graph.client(secrets).balance()
                    graph.secrets.save(secrets)
                    val held = balance.positions.count { it.code in Etf.codes }
                    graph.settings.status = "연결 확인: 성향 ETF ${held}종 보유, 예수금 ${Messages.won(balance.depositD2.toDouble())}"
                    null
                } catch (e: IllegalArgumentException) {
                    e.message
                } catch (e: KisException) {
                    graph.tokens.save(null)
                    "연결 실패: ${e.message}"
                } catch (e: Exception) {
                    // Keystore·파일 저장 실패. 메시지에 입력값이 섞일 수 있어 종류만 보여준다
                    "저장 실패: ${e.javaClass.simpleName}"
                }
            }
            _setup.value = SetupState(error = error)
            refresh()
        }
    }

    fun resetKeys() = io {
        graph.settings.autoRun = false
        graph.secrets.clear()
        graph.tokens.save(null)
        graph.reschedule()
    }

    fun selectProfile(profile: Profile) = io {
        if (graph.settings.setProfile(profile, graph.month())) graph.reschedule()
    }

    fun setAutoRun(on: Boolean) = io {
        graph.settings.autoRun = on
        graph.reschedule()
    }

    fun runNow() {
        RunService.start(getApplication())
        refresh()
    }

    /** 실패한 이번 달을 다시 시도한다 (engine이 미체결 주문이 없을 때만 진행). */
    fun retry() {
        RunService.start(getApplication(), retry = true)
        refresh()
    }

    /** 앱 실행 시: 알람이 지워졌거나 놓쳤을 수 있어 다시 건다 (설계 5절). */
    fun onLaunch() = io {
        if (!RunService.isRunning) graph.reschedule()
    }

    private fun io(block: () -> Unit) {
        viewModelScope.launch {
            withContext(Dispatchers.IO) { block() }
            refresh()
        }
    }
}
