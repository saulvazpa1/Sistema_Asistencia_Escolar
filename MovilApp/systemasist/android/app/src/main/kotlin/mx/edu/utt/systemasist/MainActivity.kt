package mx.edu.utt.nexoescolar

import android.content.pm.PackageManager
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel

/**
 * Puente Flutter <-> nativo para el servicio HCE.
 * Canal: "mx.edu.utt.nexoescolar/hce"
 *   setCredential(uid, token, active) -> guarda la credencial cifrada para el servicio HCE
 *   clear()                           -> la borra (cierre de sesión)
 *   isSupported()                     -> true si el teléfono soporta HCE
 */
class MainActivity : FlutterActivity() {

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)

        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, CHANNEL)
            .setMethodCallHandler { call, result ->
                when (call.method) {
                    "setCredential" -> {
                        val uid = call.argument<String>("uid")
                        val token = call.argument<String>("token")
                        val active = call.argument<Boolean>("active") ?: true
                        if (uid.isNullOrEmpty() || token.isNullOrEmpty()) {
                            result.error("bad_args", "uid y token son obligatorios", null)
                        } else {
                            try {
                                CredentialVault.save(applicationContext, uid, token, active)
                                result.success(true)
                            } catch (e: Exception) {
                                result.error("vault_error", e.message, null)
                            }
                        }
                    }
                    "clear" -> {
                        CredentialVault.clear(applicationContext)
                        result.success(true)
                    }
                    "isSupported" -> result.success(
                        packageManager.hasSystemFeature(PackageManager.FEATURE_NFC_HOST_CARD_EMULATION),
                    )
                    else -> result.notImplemented()
                }
            }
    }

    private companion object {
        const val CHANNEL = "mx.edu.utt.nexoescolar/hce"
    }
}
