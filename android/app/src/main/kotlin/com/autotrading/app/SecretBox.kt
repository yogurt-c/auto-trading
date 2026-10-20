package com.autotrading.app

import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.AtomicFile
import java.io.File
import java.nio.ByteBuffer
import java.security.GeneralSecurityException
import java.security.KeyStore
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

/**
 * Android Keystore의 AES-256-GCM 키로 암호화한 파일 1개. 키는 기기 밖으로 꺼낼 수 없어
 * 파일이 복사돼도 다른 기기에서는 풀리지 않는다. 파일 형식: [IV 길이 1바이트][IV][암호문+태그].
 */
class SecretBox(private val file: File, private val alias: String) {
    private val atomic = AtomicFile(file)

    fun write(plain: ByteArray) {
        val cipher = Cipher.getInstance(TRANSFORMATION).apply { init(Cipher.ENCRYPT_MODE, key()) }
        val sealed = cipher.doFinal(plain)
        val iv = cipher.iv
        val out = atomic.startWrite()
        try {
            out.write(ByteBuffer.allocate(1 + iv.size + sealed.size).put(iv.size.toByte()).put(iv).put(sealed).array())
            atomic.finishWrite(out)
        } catch (e: Exception) {
            atomic.failWrite(out)
            throw e
        }
    }

    /** 없거나 풀 수 없으면(키 초기화·파일 손상) null — 사용자가 다시 입력한다. */
    fun read(): ByteArray? {
        if (!file.exists()) return null
        return try {
            val buffer = ByteBuffer.wrap(atomic.readFully())
            val iv = ByteArray(buffer.get().toInt()).also(buffer::get)
            val sealed = ByteArray(buffer.remaining()).also(buffer::get)
            Cipher.getInstance(TRANSFORMATION)
                .apply { init(Cipher.DECRYPT_MODE, key(), GCMParameterSpec(TAG_BITS, iv)) }
                .doFinal(sealed)
        } catch (_: GeneralSecurityException) {
            null
        } catch (_: RuntimeException) {
            null // 잘린 파일 (BufferUnderflow·음수 길이)
        }
    }

    fun delete() {
        atomic.delete()
    }

    private fun key(): SecretKey {
        val store = KeyStore.getInstance(KEYSTORE).apply { load(null) }
        (store.getKey(alias, null) as? SecretKey)?.let { return it }
        val spec = KeyGenParameterSpec.Builder(alias, KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT)
            .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
            .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
            .setKeySize(256)
            .build()
        return KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, KEYSTORE).apply { init(spec) }.generateKey()
    }

    private companion object {
        const val KEYSTORE = "AndroidKeyStore"
        const val TRANSFORMATION = "AES/GCM/NoPadding"
        const val TAG_BITS = 128
    }
}
