import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';

import '../models/auth_session.dart';

/// Puente con el servicio nativo de emulación de tarjeta (HCE, solo Android).
///
/// El servicio Kotlin (`NexoHostApduService`) responde al lector de la puerta aunque la app esté
/// cerrada, por eso necesita su propia copia cifrada del token (Android Keystore).
/// Esta clase la mantiene sincronizada con la sesión: se llama al iniciar sesión, al restaurarla
/// y al cerrar sesión.
class HceService {
  const HceService();

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
  Future<void> sync(AuthSession session) async {
    if (!_isAndroid) return;
    try {
      await _channel.invokeMethod<bool>('setCredential', {
        'uid': session.uid,
        'token': session.token,
        'active': session.student.credencialActiva,
      });
    } on PlatformException catch (e) {
      debugPrint('HceService.sync falló: $e');
    } on MissingPluginException {
      // Sin implementación nativa (tests, otra plataforma): se ignora.
    }
  }

  /// Borra la credencial del servicio HCE (cierre de sesión).
  Future<void> clear() async {
    if (!_isAndroid) return;
    try {
      await _channel.invokeMethod<bool>('clear');
    } on PlatformException catch (e) {
      debugPrint('HceService.clear falló: $e');
    } on MissingPluginException {
      // Ignorar.
    }
  }
}
