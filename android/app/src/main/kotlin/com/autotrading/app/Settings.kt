package com.autotrading.app

import android.content.SharedPreferences
import androidx.core.content.edit
import com.autotrading.core.Profile
import java.time.Instant
import java.time.YearMonth

/** 비밀이 아닌 설정·상태. 키·계좌·토큰은 [SecretsStore]·[KeystoreTokenStore]에만 둔다. */
class Settings(private val prefs: SharedPreferences) {
    var autoRun: Boolean
        get() = prefs.getBoolean(AUTO_RUN, false)
        set(value) = prefs.edit { putBoolean(AUTO_RUN, value) }

    val profile: Profile?
        get() = prefs.getString(PROFILE, null)?.let { name -> Profile.entries.firstOrNull { it.name == name } }

    /** 처음 고를 때는 제한 없음. 바꾸는 것은 달마다 한 번 (설계 1절). */
    fun canChangeProfile(month: YearMonth): Boolean =
        profile == null || prefs.getString(PROFILE_CHANGED, null) != month.toString()

    fun setProfile(profile: Profile, month: YearMonth): Boolean {
        val current = this.profile
        if (current == profile) return true
        if (!canChangeProfile(month)) return false
        prefs.edit {
            putString(PROFILE, profile.name)
            if (current != null) putString(PROFILE_CHANGED, month.toString())
        }
        return true
    }

    var nextRunAt: Instant?
        get() = prefs.getLong(NEXT_RUN, 0).takeIf { it > 0 }?.let(Instant::ofEpochMilli)
        set(value) = prefs.edit { putLong(NEXT_RUN, value?.toEpochMilli() ?: 0) }

    /** 마지막 실행 결과 한 줄 (홈 화면). */
    var status: String?
        get() = prefs.getString(STATUS, null)
        set(value) = prefs.edit { putString(STATUS, value) }

    private companion object {
        const val AUTO_RUN = "auto_run"
        const val PROFILE = "profile"
        const val PROFILE_CHANGED = "profile_changed_month"
        const val NEXT_RUN = "next_run_at"
        const val STATUS = "status"
    }
}
