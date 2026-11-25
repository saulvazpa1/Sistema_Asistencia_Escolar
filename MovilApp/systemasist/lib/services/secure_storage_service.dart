import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import '../models/auth_session.dart';

/// Almacenamiento cifrado de la sesión del alumno.
///
/// - Android: EncryptedSharedPreferences respaldado por Android Keystore.
/// - iOS: Keychain (accesible tras el primer desbloqueo, sin migrar a otros equipos).
///
/// Se cifra TODO (token, UID y datos del alumno, que incluyen CURP).
class SecureStorageService {
  SecureStorageService({FlutterSecureStorage? storage})
      : _storage = storage ??
            const FlutterSecureStorage(
              aOptions: AndroidOptions(),
              iOptions: IOSOptions(
                accessibility: KeychainAccessibility.first_unlock_this_device,
              ),
            );

  final FlutterSecureStorage _storage;

  static const _kToken = 'nexo.token';
  static const _kUid = 'nexo.uid';
  static const _kStudent = 'nexo.student';

  Future<void> saveSession(AuthSession session) async {
    await Future.wait([
      _storage.write(key: _kToken, value: session.token),
      _storage.write(key: _kUid, value: session.uid),
      _storage.write(
        key: _kStudent,
        value: jsonEncode(session.student.toJson()),
      ),
    ]);
  }

  /// Devuelve la sesión guardada o `null` si no existe / está corrupta.
  /// Ante un error de descifrado (Keystore invalidado, restauración de backup...)
  /// limpia el almacenamiento para no quedar en un estado inconsistente.
  Future<AuthSession?> loadSession() async {
    try {
      final token = await _storage.read(key: _kToken);
      final uid = await _storage.read(key: _kUid);
      final studentJson = await _storage.read(key: _kStudent);
      if (token == null || uid == null || studentJson == null) return null;

      final decoded = jsonDecode(studentJson);
      if (decoded is! Map<String, dynamic>) throw const FormatException();

      return AuthSession.fromLoginJson({
        'token': token,
        'uid': uid,
        'alumno': decoded,
      });
    } catch (e) {
      debugPrint('SecureStorageService.loadSession falló: $e');
      await clear();
      return null;
    }
  }

  Future<void> clear() async {
    try {
      await _storage.deleteAll();
    } catch (e) {
      debugPrint('SecureStorageService.clear falló: $e');
    }
  }
}
