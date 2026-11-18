package mx.edu.utt.nexoescolar

import android.content.Context
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.Base64
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

    private const val KEY_ALIAS = "nexo_hce_key"
    private const val PREFS = "nexo_hce_vault"
    private const val PREF_BLOB = "blob"
    private const val TRANSFORMATION = "AES/GCM/NoPadding"
    private const val GCM_TAG_BITS = 128

    fun save(context: Context, uid: String, token: String, active: Boolean) {
        val plain = JSONObject()
            .put("uid", uid)
            .put("token", token)
            .put("active", active)
            .toString()
            .toByteArray(Charsets.UTF_8)

        val cipher = Cipher.getInstance(TRANSFORMATION)
        cipher.init(Cipher.ENCRYPT_MODE, getOrCreateKey())
        val blob = cipher.iv + cipher.doFinal(plain) // IV (12 bytes) || cifrado+tag

        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .edit()
            .putString(PREF_BLOB, Base64.encodeToString(blob, Base64.NO_WRAP))
            .apply()
    }

    /** Devuelve la credencial o null si no existe o no se puede descifrar. */
    fun load(context: Context): Credential? {
        return try {
            val encoded = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
                .getString(PREF_BLOB, null) ?: return null
            val blob = Base64.decode(encoded, Base64.NO_WRAP)
            if (blob.size <= 12) return null

            val cipher = Cipher.getInstance(TRANSFORMATION)
            cipher.init(
                Cipher.DECRYPT_MODE,
                getOrCreateKey(),
                GCMParameterSpec(GCM_TAG_BITS, blob, 0, 12),
            )
            val json = JSONObject(String(cipher.doFinal(blob, 12, blob.size - 12), Charsets.UTF_8))
            Credential(
                uid = json.getString("uid"),
                token = json.getString("token"),
                active = json.optBoolean("active", true),
            )
        } catch (e: Exception) {
            null // llave invalidada, datos corruptos, etc.: tratar como "sin credencial"
        }
    }

    fun clear(context: Context) {
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit().clear().apply()
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
