package com.example.systemasist

import android.content.Intent
import android.content.pm.PackageManager
import android.nfc.NfcAdapter
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel

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
                    "isSupported" -> result.success(hasHce())
                    "status" -> result.success(buildStatus())
                    else -> result.notImplemented()
                }
            }
    }

    private fun hasHce(): Boolean =
        packageManager.hasSystemFeature(PackageManager.FEATURE_NFC_HOST_CARD_EMULATION)

    /** ¿Android ve nuestro servicio entre los servicios HCE instalados? */
    @Suppress("DEPRECATION")
    private fun isServiceRegistered(): Boolean = try {
        val intent = Intent("android.nfc.cardemulation.action.HOST_APDU_SERVICE")
            .setPackage(packageName)
        packageManager.queryIntentServices(intent, 0)
            .any { it.serviceInfo?.name?.endsWith("NexoHostApduService") == true }
    } catch (e: Exception) {
        false
    }

    private fun buildStatus(): Map<String, Any?> {
        val adapter = try {
            NfcAdapter.getDefaultAdapter(applicationContext)
        } catch (e: Exception) {
            null
        }
        val credential = CredentialVault.load(applicationContext)
        return mapOf(
            "hceSupported" to hasHce(),
            "nfcPresent" to (adapter != null),
            "nfcEnabled" to (adapter?.isEnabled == true),
            "serviceRegistered" to isServiceRegistered(),
            "hasCredential" to (credential != null),
            "active" to (credential?.active == true),
            "uid" to credential?.uid,
            "vaultError" to (if (credential == null) CredentialVault.lastError else null),
            "lastTouchAt" to HceDiag.lastAt(applicationContext),
            "lastResult" to HceDiag.lastResult(applicationContext),
        )
    }

    private companion object {
        const val CHANNEL = "mx.edu.utt.nexoescolar/hce"
    }
}
