package mx.edu.utt.nexoescolar

import android.nfc.cardemulation.HostApduService
import android.os.Bundle
import org.json.JSONObject
import javax.crypto.Mac
import javax.crypto.spec.SecretKeySpec

/**
 * Emulación de tarjeta (HCE): el teléfono responde al lector de la puerta.
 *
 * Protocolo:
 *   Lector -> 00 A4 04 00 06 F0 4E 45 58 4F 01 [00]        (SELECT AID)
 *   Teléfono -> <JSON UTF-8> 90 00                        (o 61 xx si no cabe: usar GET RESPONSE)
 *   Lector -> 00 C0 00 00 [Le]                             (GET RESPONSE, solo si hubo 61 xx)
 *
 * JSON: {"v":1,"uid":"...","ts":<epoch seg>,"sig":"<hex>"}
 *   sig = HMAC-SHA256(key = token, msg = "<uid>.<ts>"), hex en minúsculas
 * (mismo formato que el QR de respaldo, así el servidor valida ambos igual).
 *
 * El servicio funciona con la app cerrada; lee la credencial de [CredentialVault].
 */
class NexoHostApduService : HostApduService() {

    private var pending: ByteArray? = null
    private var selected = false

    override fun processCommandApdu(apdu: ByteArray, extras: Bundle?): ByteArray {
        if (apdu.size < 4) return SW_UNKNOWN

        return when {
            isSelectAid(apdu) -> handleSelect()
            selected && apdu[0] == CLA_ISO && apdu[1] == INS_GET_RESPONSE -> nextChunk()
            else -> SW_INS_NOT_SUPPORTED
        }
    }

    override fun onDeactivated(reason: Int) {
        pending = null
        selected = false
    }

    private fun handleSelect(): ByteArray {
        pending = null
        selected = false

        val credential = CredentialVault.load(applicationContext) ?: return SW_NOT_ALLOWED
        if (!credential.active) return SW_NOT_ALLOWED // credencial inactiva: no emitir nada

        val payload = try {
            buildPayload(credential)
        } catch (e: Exception) {
            return SW_UNKNOWN
        }

        selected = true
        pending = payload
        return nextChunk()
    }

    /** Envía hasta [CHUNK] bytes; si quedan más, responde 61 xx para que el lector pida el resto. */
    private fun nextChunk(): ByteArray {
        val data = pending ?: return SW_NOT_ALLOWED
        val size = minOf(CHUNK, data.size)
        val head = data.copyOfRange(0, size)
        val rest = data.copyOfRange(size, data.size)

        return if (rest.isEmpty()) {
            pending = null
            head + SW_OK
        } else {
            pending = rest
            head + byteArrayOf(0x61, minOf(rest.size, 0xFF).toByte())
        }
    }

    private fun buildPayload(credential: CredentialVault.Credential): ByteArray {
        val ts = System.currentTimeMillis() / 1000
        val mac = Mac.getInstance("HmacSHA256")
        mac.init(SecretKeySpec(credential.token.toByteArray(Charsets.UTF_8), "HmacSHA256"))
        val sig = mac.doFinal("${credential.uid}.$ts".toByteArray(Charsets.UTF_8))
            .joinToString("") { "%02x".format(it) }

        return JSONObject()
            .put("v", 1)
            .put("uid", credential.uid)
            .put("ts", ts)
            .put("sig", sig)
            .toString()
            .toByteArray(Charsets.UTF_8)
    }

    private fun isSelectAid(apdu: ByteArray): Boolean {
        if (apdu.size < 5 + AID.size) return false
        if (apdu[0] != CLA_ISO || apdu[1] != INS_SELECT || apdu[2] != 0x04.toByte()) return false
        if (apdu[4].toInt() and 0xFF != AID.size) return false
        return apdu.copyOfRange(5, 5 + AID.size).contentEquals(AID)
    }

    private companion object {
        val AID = byteArrayOf(0xF0.toByte(), 0x4E, 0x45, 0x58, 0x4F, 0x01)

        const val CHUNK = 240
        const val CLA_ISO: Byte = 0x00
        const val INS_SELECT: Byte = 0xA4.toByte()
        const val INS_GET_RESPONSE: Byte = 0xC0.toByte()

        val SW_OK = byteArrayOf(0x90.toByte(), 0x00)
        val SW_NOT_ALLOWED = byteArrayOf(0x69, 0x85.toByte()) // condiciones de uso no satisfechas
        val SW_INS_NOT_SUPPORTED = byteArrayOf(0x6D, 0x00)
        val SW_UNKNOWN = byteArrayOf(0x6F, 0x00)
    }
}
