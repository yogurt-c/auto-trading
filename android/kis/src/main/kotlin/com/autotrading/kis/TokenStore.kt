package com.autotrading.kis

import java.time.Instant

/** 접근토큰. 유효기간 24시간, 발급은 1분에 1회라 앱이 다시 시작돼도 저장된 값을 재사용한다. */
class AccessToken(val value: String, val expiresAt: Instant) {
    override fun toString() = "AccessToken(expiresAt=$expiresAt)"
}

/** app에서는 Keystore로 암호화해 저장한다. 키·계좌를 바꾸면 비운다. */
interface TokenStore {
    fun load(): AccessToken?

    /** null이면 지운다. */
    fun save(token: AccessToken?)
}

class InMemoryTokenStore : TokenStore {
    @Volatile
    private var token: AccessToken? = null

    override fun load() = token

    override fun save(token: AccessToken?) {
        this.token = token
    }
}

fun interface Sleeper {
    fun sleep(millis: Long)

    companion object {
        val THREAD = Sleeper { Thread.sleep(it) }
    }
}
