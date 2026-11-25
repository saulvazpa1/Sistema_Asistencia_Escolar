import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';

import '../models/auth_session.dart';

/// Diagnóstico de la emulación de tarjeta tal como lo ve el código nativo.
class HceStatus {
  const HceStatus({
    this.nativeMissing = false,
    this.hceSupported = false,
    this.nfcPresent = false,
    this.nfcEnabled = false,
    this.serviceRegistered = false,
    this.hasCredential = false,
    this.active = false,
    this.uid,
    this.vaultError,
    this.lastTouchAt = 0,
    this.lastResult,
  });

  /// El canal nativo no existe: no se reemplazó `MainActivity.kt` (o falta recompilar).
  final bool nativeMissing;
  final bool hceSupported;
  final bool nfcPresent;
  final bool nfcEnabled;
  final bool serviceRegistered;
  final bool hasCredential;
  final bool active;
  final String? uid;
  final String? vaultError;

  /// Epoch en milisegundos del último SELECT recibido de un lector (0 = nunca).
  final int lastTouchAt;
  final String? lastResult;

  /// Todo listo para que el lector reciba datos.
  bool get ready =>
      !nativeMissing &&
      hceSupported &&
      nfcEnabled &&
      serviceRegistered &&
      hasCredential &&
      active;

  factory HceStatus.fromMap(Map<Object?, Object?> m) => HceStatus(
    hceSupported: m['hceSupported'] == true,
    nfcPresent: m['nfcPresent'] == true,
    nfcEnabled: m['nfcEnabled'] == true,
    serviceRegistered: m['serviceRegistered'] == true,
    hasCredential: m['hasCredential'] == true,
    active: m['active'] == true,
    uid: m['uid'] as String?,
    vaultError: m['vaultError'] as String?,
    lastTouchAt: (m['lastTouchAt'] as num?)?.toInt() ?? 0,
    lastResult: m['lastResult'] as String?,
  );
}

/// Puente con el servicio nativo de emulación de tarjeta (HCE, solo Android).
///
/// El servicio Kotlin (`NexoHostApduService`) responde al lector de la puerta aunque la app esté
/// cerrada, por eso necesita su propia copia cifrada del token (Android Keystore).
/// Esta clase la mantiene sincronizada con la sesión: se llama al iniciar sesión, al restaurarla
/// y al cerrar sesión.
class HceService {
  const HceService();

  static const Duration _nativeTimeout = Duration(seconds: 3);
  static const MethodChannel _channel = MethodChannel(
    'mx.edu.utt.nexoescolar/hce',
  );

  bool get _isAndroid => defaultTargetPlatform == TargetPlatform.android;

  /// ¿El teléfono soporta HCE? (false en iOS o equipos sin la función).
  Future<bool> isSupported() async {
    if (!_isAndroid) return false;
    try {
      return await _channel.invokeMethod<bool>('isSupported') ?? false;
    } on PlatformException catch (e) {
      debugPrint('HceService.isSupported: $e');
      return false;
    } on MissingPluginException {
      return false;
    }
  }

  /// Guarda/actualiza la credencial que el servicio HCE entregará al lector.
  /// Devuelve `false` si no se pudo (módulo nativo ausente o error de cifrado).
  Future<bool> sync(AuthSession session) async {
    if (!_isAndroid) return true;
    try {
      return await _channel
              .invokeMethod<bool>('setCredential', {
                'uid': session.uid,
                'token': session.signingKey, // llave de firma = SHA-256(token)
                'active': session.student.credencialActiva,
              })
              .timeout(_nativeTimeout, onTimeout: () => false) ??
          false;
    } on PlatformException catch (e) {
      debugPrint('HceService.sync falló: $e');
      return false;
    } on MissingPluginException {
      debugPrint(
        'HceService.sync: falta MainActivity.kt nativo (canal no registrado)',
      );
      return false;
    }
  }

  /// Borra la credencial del servicio HCE (cierre de sesión).
  Future<void> clear() async {
    if (!_isAndroid) return;
    try {
      await _channel
          .invokeMethod<bool>('clear')
          .timeout(_nativeTimeout, onTimeout: () => null);
    } on PlatformException catch (e) {
      debugPrint('HceService.clear falló: $e');
    } on MissingPluginException {
      // Ignorar.
    }
  }

  /// Estado real del servicio nativo (para mostrar por qué el lector no recibe datos).
  Future<HceStatus> status() async {
    if (!_isAndroid) return const HceStatus();
    try {
      final raw = await _channel
          .invokeMethod<Map<Object?, Object?>>('status')
          .timeout(_nativeTimeout, onTimeout: () => null);
      return raw == null
          ? const HceStatus(nativeMissing: true)
          : HceStatus.fromMap(raw);
    } on MissingPluginException {
      return const HceStatus(nativeMissing: true);
    } on PlatformException catch (e) {
      debugPrint('HceService.status falló: $e');
      return const HceStatus(nativeMissing: true);
    }
  }
}
