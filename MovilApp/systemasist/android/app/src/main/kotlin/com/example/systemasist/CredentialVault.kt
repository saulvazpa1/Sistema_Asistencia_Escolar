package com.example.systemasist

import android.content.Context
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.Base64
import android.util.Log
import org.json.JSONObject
import java.security.KeyStore
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

/**
 * Bóveda nativa de la credencial para el servicio HCE.
 *
 * El servicio HCE puede ser invocado por Android con la app de Flutter cerrada, así que necesita
 * su propia copia del token. Se guarda cifrada con AES-256-GCM usando una llave NO exportable
 * del Android Keystore (la llave nunca sale del hardware/TEE).
 */
object CredentialVault {

    data class Credential(val uid: String, val token: String, val active: Boolean)

    private const val TAG = "NexoVault"
    private const val KEY_ALIAS = "nexo_hce_key"
    private const val PREFS = "nexo_hce_vault"
    private const val PREF_BLOB = "blob"
    private const val TRANSFORMATION = "AES/GCM/NoPadding"
    private const val GCM_TAG_BITS = 128

    /** Motivo del último fallo de [load] (null = bien o sin datos). Solo para diagnóstico. */
    @Volatile
    var lastError: String? = null
        private set

    fun save(context: Context, uid: String, token: String, active: Boolean) {
        val plain = JSONObject()
            .put("uid", uid)
            .put("token", token)
            .put("active", active)
            .toString()
            .toByteArray(Charsets.UTF_8)

        val blob = try {
            encrypt(plain)
        } catch (e: Exception) {
            // Llave del Keystore dañada/invalidada: se borra y se vuelve a intentar una vez.
            Log.w(TAG, "Cifrado falló, regenerando llave: $e")
            deleteKey()
            encrypt(plain)
        }

        // commit() (síncrono) en vez de apply(): el lector puede tocar justo después de guardar.
        val saved = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .edit()
            .putString(PREF_BLOB, Base64.encodeToString(blob, Base64.NO_WRAP))
            .commit()
        if (!saved) throw IllegalStateException("No se pudo escribir la credencial en disco")
        lastError = null
    }

    /** Devuelve la credencial o null si no existe o no se puede descifrar. */
    fun load(context: Context): Credential? {
        val encoded = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .getString(PREF_BLOB, null)
        if (encoded == null) {
            lastError = "vacía: la app aún no ha guardado la credencial"
            return null
        }
        return try {
            val blob = Base64.decode(encoded, Base64.NO_WRAP)
            if (blob.size <= 12) {
                lastError = "datos corruptos"
                return null
            }
            val cipher = Cipher.getInstance(TRANSFORMATION)
            cipher.init(
                Cipher.DECRYPT_MODE,
                getOrCreateKey(),
                GCMParameterSpec(GCM_TAG_BITS, blob, 0, 12),
            )
            val json = JSONObject(String(cipher.doFinal(blob, 12, blob.size - 12), Charsets.UTF_8))
            lastError = null
            Credential(
                uid = json.getString("uid"),
                token = json.getString("token"),
                active = json.optBoolean("active", true),
            )
        } catch (e: Exception) {
            Log.e(TAG, "No se pudo descifrar la credencial", e)
            lastError = "no se pudo descifrar (${e.javaClass.simpleName}); vuelve a iniciar sesión"
            null // llave invalidada, datos corruptos, etc.: tratar como "sin credencial"
        }
    }

    fun clear(context: Context) {
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit().clear().commit()
        lastError = null
    }

    private fun encrypt(plain: ByteArray): ByteArray {
        val cipher = Cipher.getInstance(TRANSFORMATION)
        cipher.init(Cipher.ENCRYPT_MODE, getOrCreateKey())
        val iv = cipher.iv
        return iv + cipher.doFinal(plain) // IV (12 bytes) || cifrado+tag
    }

    private fun deleteKey() {
        try {
            KeyStore.getInstance("AndroidKeyStore").apply { load(null) }.deleteEntry(KEY_ALIAS)
        } catch (e: Exception) {
            Log.w(TAG, "No se pudo borrar la llave: $e")
        }
    }

    private fun getOrCreateKey(): SecretKey {
        val keyStore = KeyStore.getInstance("AndroidKeyStore").apply { load(null) }
        (keyStore.getEntry(KEY_ALIAS, null) as? KeyStore.SecretKeyEntry)?.let { return it.secretKey }

        val generator = KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, "AndroidKeyStore")
        generator.init(
            KeyGenParameterSpec.Builder(
                KEY_ALIAS,
                KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT,
            )
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
                .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
                .setKeySize(256)
                .build(),
        )
        return generator.generateKey()
    }
}

/**
 * Registro (NO sensible) del último toque del lector sobre el servicio HCE.
 * Lo escribe el servicio y lo lee la app para mostrar "el lector sí llegó / qué respondí".
 */
object HceDiag {
    private const val PREFS = "nexo_hce_diag"

    fun record(context: Context, result: String) {
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .edit()
            .putLong("at", System.currentTimeMillis())
            .putString("result", result)
            .apply()
    }

    fun lastAt(context: Context): Long =
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).getLong("at", 0L)

    fun lastResult(context: Context): String? =
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).getString("result", null)
}
