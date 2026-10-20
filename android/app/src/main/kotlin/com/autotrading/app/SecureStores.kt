package com.autotrading.app

import com.autotrading.kis.AccessToken
import com.autotrading.kis.Account
import com.autotrading.kis.KisCredentials
import com.autotrading.kis.TokenStore
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json
import java.time.Instant

/** 앱키·시크릿·계좌. 화면에는 [Account.masked]만 쓴다. */
class KisSecrets(val credentials: KisCredentials, val account: Account) {
    override fun toString() = "KisSecrets(${account.masked})"
}

class SecretsStore(private val box: SecretBox) {
    @Serializable
    private data class Stored(val appKey: String, val appSecret: String, val cano: String, val productCode: String)

    fun load(): KisSecrets? {
        val bytes = box.read() ?: return null
        return runCatching {
            val s = Json.decodeFromString<Stored>(bytes.decodeToString())
            KisSecrets(KisCredentials(s.appKey, s.appSecret), Account(s.cano, s.productCode))
        }.getOrNull()
    }

    fun save(secrets: KisSecrets) {
        val c = secrets.credentials
        val stored = Stored(c.appKey, c.appSecret, secrets.account.cano, secrets.account.productCode)
        box.write(Json.encodeToString(Stored.serializer(), stored).encodeToByteArray())
    }

    fun clear() = box.delete()
}

/** 접근토큰 (24시간, 발급 1분 1회 제한) — 앱이 다시 시작돼도 재사용한다. */
class KeystoreTokenStore(private val box: SecretBox) : TokenStore {
    @Serializable
    private data class Stored(val value: String, val expiresAt: Long)

    @Synchronized
    override fun load(): AccessToken? {
        val bytes = box.read() ?: return null
        return runCatching {
            val s = Json.decodeFromString<Stored>(bytes.decodeToString())
            AccessToken(s.value, Instant.ofEpochSecond(s.expiresAt))
        }.getOrNull()
    }

    @Synchronized
    override fun save(token: AccessToken?) {
        if (token == null) {
            box.delete()
            return
        }
        val stored = Stored(token.value, token.expiresAt.epochSecond)
        box.write(Json.encodeToString(Stored.serializer(), stored).encodeToByteArray())
    }
}
