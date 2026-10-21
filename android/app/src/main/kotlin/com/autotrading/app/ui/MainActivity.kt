package com.autotrading.app.ui

import android.Manifest
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.viewModels
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Icon
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.painterResource
import androidx.core.content.ContextCompat
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.compose.LocalLifecycleOwner
import androidx.lifecycle.repeatOnLifecycle
import com.autotrading.app.R
import kotlinx.coroutines.delay

class MainActivity : ComponentActivity() {
    private val viewModel: AppViewModel by viewModels()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        if (savedInstanceState == null) viewModel.onLaunch()
        setContent {
            AppTheme {
                App(viewModel)
            }
        }
    }
}

private enum class Tab(val label: String) { HOME("홈"), PROFILE("성향"), HISTORY("기록"), SETTINGS("설정") }

@Composable
private fun App(viewModel: AppViewModel) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val setup by viewModel.setup.collectAsStateWithLifecycle()
    RequestNotificationPermission()
    RefreshWhileVisible(viewModel)

    when {
        !state.loaded -> Unit
        state.maskedAccount == null -> SetupScreen(setup, viewModel::saveKeys)
        state.profile == null -> ProfileScreen(state, viewModel::selectProfile, Modifier)
        else -> MainTabs(state, viewModel)
    }
}

@Composable
private fun MainTabs(state: UiState, viewModel: AppViewModel) {
    var tab by rememberSaveable { mutableIntStateOf(Tab.HOME.ordinal) }
    Scaffold(
        bottomBar = {
            NavigationBar {
                Tab.entries.forEach { t ->
                    NavigationBarItem(
                        selected = tab == t.ordinal,
                        onClick = { tab = t.ordinal },
                        icon = { Icon(painterResource(R.drawable.ic_notify), contentDescription = null) },
                        label = { Text(t.label) },
                    )
                }
            }
        },
    ) { padding ->
        Box(Modifier.padding(padding)) {
            when (Tab.entries[tab]) {
                Tab.HOME -> HomeScreen(state, viewModel::setAutoRun, viewModel::runNow, viewModel::retry)
                Tab.PROFILE -> ProfileScreen(state, viewModel::selectProfile, Modifier)
                Tab.HISTORY -> HistoryScreen(state.history, state.unreadable, state.month)
                Tab.SETTINGS -> SettingsScreen(state, viewModel::resetKeys)
            }
        }
    }
}

/** 화면이 보이는 동안 5초마다 다시 읽는다 — 실행 중 주문·체결 진행이 파일에 저장된다. */
@Composable
private fun RefreshWhileVisible(viewModel: AppViewModel) {
    val lifecycle = LocalLifecycleOwner.current.lifecycle
    LaunchedEffect(lifecycle) {
        lifecycle.repeatOnLifecycle(Lifecycle.State.STARTED) {
            while (true) {
                viewModel.refresh()
                delay(REFRESH_MILLIS)
            }
        }
    }
}

@Composable
private fun RequestNotificationPermission() {
    if (Build.VERSION.SDK_INT < Build.VERSION_CODES.TIRAMISU) return
    val context = LocalContext.current
    val launcher = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) {}
    LaunchedEffect(Unit) {
        val granted = ContextCompat.checkSelfPermission(context, Manifest.permission.POST_NOTIFICATIONS) ==
            PackageManager.PERMISSION_GRANTED
        if (!granted) launcher.launch(Manifest.permission.POST_NOTIFICATIONS)
    }
}

private const val REFRESH_MILLIS = 5_000L
