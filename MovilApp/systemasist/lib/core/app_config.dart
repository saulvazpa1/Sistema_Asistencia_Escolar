import 'package:flutter/foundation.dart';

// ----- Central app configuration -----

abstract final class AppConfig {
  static const String baseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'https://api.example.com',
  );

  static const bool useMock = bool.fromEnvironment(
    'USE_MOCK',
    defaultValue: !kReleaseMode,
  );

  // --------- Maximum time per HTTP request ---------
  static const Duration requestTimeout = Duration(seconds: 12);

  // ---------- Automatic retry attempts for access requests before displaying an error message ----------
  static const int maxSendAttempts = 3;

  // ---------- Maximum time to wait for a tag before ending the NFC session ----------
  static const Duration scanTimeout = Duration(seconds: 45);

  // --------- Cuánto tiempo se muestra "Acceso registrado" antes de volver a reposo. --------
  static const Duration successResetDelay = Duration(seconds: 5);

  // --------- La sesion NFC arranca sola al abrir la app --------
  static const bool autoStartScanOnAndroid = true;

  // --------- Vigencia del codigo QR de acceso, en segundos. --------
  static const int qrRefreshSeconds = 30;

  // --------- Longitud maxima que acepta el identificador del punto de acceso ----------
  static const int maxPointIdLength = 128;

  // --------- Evita publicar una construccion apuntando a HTTP ----------
  static void assertSafeForRelease() {
    if (kReleaseMode && useMock) {
      throw StateError('USE_MOCK = true no está permitido.');
    }
    if (!useMock && !baseUrl.startsWith('https://')) {
      throw StateError('API_BASE_URL debe de usar HTTPS.');
    }
  }
}
