import 'package:flutter/foundation.dart';

abstract final class AppConfig {
  static const String baseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'https://api.nexoescolar.example/v1',
  );

  static const bool useMock = bool.fromEnvironment(
    'USE_MOCK',
    defaultValue: !kReleaseMode,
  );

  /// Tiempo máximo por petición HTTP.
  static const Duration requestTimeout = Duration(seconds: 12);

  /// Intentos automáticos de envío del acceso antes de mostrar error.
  static const int maxSendAttempts = 3;

  /// Tiempo máximo esperando una etiqueta antes de cerrar la sesión NFC.
  static const Duration scanTimeout = Duration(seconds: 45);

  /// Cuánto tiempo se muestra "Acceso registrado" antes de volver a reposo.
  static const Duration successResetDelay = Duration(seconds: 5);

  /// En Android la sesión NFC (modo LECTOR de etiquetas) arranca sola al abrir la credencial.
  /// En iOS siempre es manual (iOS muestra una hoja del sistema al iniciar).
  ///
  /// IMPORTANTE: el modo lector apaga la emulación de tarjeta (HCE). Con lector de puerta
  /// (HCE) debe ser `false`; ponlo en `true` solo si usas únicamente etiquetas NFC en la pared.
  static const bool autoStartScanOnAndroid = false;

  /// Vigencia (segundos) del código QR de respaldo antes de regenerarse.
  static const int qrRefreshSeconds = 30;

  /// Longitud máxima aceptada para el identificador del punto de acceso.
  static const int maxPointIdLength = 128;

  /// En Android el teléfono responde como tarjeta (HCE) ante el lector PC/SC de la puerta.
  static const bool hceEnabledOnAndroid = true;

  /// Tiempo mínimo que se muestra el splash de Bot Studios.
  static const Duration splashMinDuration = Duration(milliseconds: 2400);

  /// Evita publicar una build de release apuntando a HTTP o en modo simulación por error.
  static void assertSafeForRelease() {
    if (kReleaseMode && useMock) {
      throw StateError('USE_MOCK=true no está permitido en release.');
    }
    if (!useMock && !baseUrl.startsWith('https://')) {
      throw StateError('API_BASE_URL debe usar HTTPS.');
    }
  }
}
