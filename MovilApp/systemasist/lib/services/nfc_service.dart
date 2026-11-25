import 'dart:async';
import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';
import 'package:ndef_record/ndef_record.dart';
import 'package:nfc_manager/nfc_manager.dart';
import 'package:nfc_manager/nfc_manager_android.dart';
import 'package:nfc_manager/nfc_manager_ios.dart';

import '../core/app_config.dart';
import '../core/app_exceptions.dart';
import '../models/access_models.dart';
import '../models/auth_session.dart';
import '../models/nfc_ui_state.dart';
import 'access_service.dart';

/// Gestiona TODO el ciclo NFC de la credencial (modo "punto de acceso"):
///
///   1. Verifica hardware / estado del NFC ([refreshAvailability]).
///   2. Abre una sesión de lectura ([startScan]) y espera la etiqueta fija de la puerta.
///   3. Extrae el identificador del punto (NDEF de texto/URI, o UID de la etiqueta).
///   4. Envía token + UID del alumno al backend con reintentos ([AccessService]).
///   5. Cierra SIEMPRE la sesión NFC (éxito, error, timeout, cancelación o dispose).
///
/// La UI solo escucha [state].
class NfcService {
  NfcService({required AccessService accessService, this.hceMode = false})
      : _access = accessService;

  final AccessService _access;

  /// `true` cuando el teléfono también responde como tarjeta (HCE) ante el lector de la puerta.
  /// En ese caso la lectura de etiquetas es opcional/manual: el modo lector apaga el HCE.
  final bool hceMode;

  NfcUiState _idle() => NfcUiState.idle(
        title: hceMode ? 'Teléfono listo como tarjeta' : null,
        detail: hceMode ? 'Acerca tu teléfono al lector de la puerta.' : null,
      );

  /// Estado observable para la UI.
  final ValueNotifier<NfcUiState> state =
      ValueNotifier<NfcUiState>(const NfcUiState.checking());

  /// Se invoca cuando el servidor responde 401 (token inválido).
  VoidCallback? onSessionExpired;

  NfcAvailability _availability = NfcAvailability.unsupported;
  AuthSession? _session;
  CheckInPoint? _lastPoint;

  bool _sessionActive = false; // hay una sesión nativa abierta
  bool _busy = false; // procesando una lectura / enviando (anti doble disparo)
  bool _disposed = false;

  Timer? _scanTimeout;
  Timer? _successReset;

  bool get isEnabled => _availability == NfcAvailability.enabled;
  bool get isSupported => _availability != NfcAvailability.unsupported;

  // ---------------------------------------------------------------------------
  // Disponibilidad
  // ---------------------------------------------------------------------------

  /// Consulta hardware + estado del NFC y actualiza [state].
  /// Llamar al iniciar y cada vez que la app vuelve a primer plano
  /// (el usuario pudo activar el NFC en ajustes).
  Future<void> refreshAvailability() async {
    NfcAvailability availability;
    try {
      availability = await NfcManager.instance.checkAvailability();
    } catch (e) {
      debugPrint('NfcService.checkAvailability falló: $e');
      availability = NfcAvailability.unsupported;
    }
    if (_disposed) return;
    _availability = availability;

    final phase = state.value.phase;
    switch (availability) {
      case NfcAvailability.unsupported:
        await _closeSession();
        _emit(const NfcUiState.unsupported());
      case NfcAvailability.disabled:
        if (!_busy) {
          await _closeSession();
          _emit(const NfcUiState.disabled());
        }
      case NfcAvailability.enabled:
        if (phase == NfcPhase.checking ||
            phase == NfcPhase.disabled ||
            phase == NfcPhase.unsupported) {
          _emit(_idle());
        }
    }
  }

  // ---------------------------------------------------------------------------
  // Sesión de lectura
  // ---------------------------------------------------------------------------

  /// Abre la sesión NFC y queda a la espera de la etiqueta del punto de acceso.
  Future<void> startScan(AuthSession session) async {
    _session = session;
    // En modo tarjeta (HCE) NUNCA se abre el modo lector: apagaría la emulación de tarjeta.
    if (hceMode) return;
    if (_disposed || _busy || _sessionActive) return;

    _successReset?.cancel();
    await refreshAvailability();
    if (_disposed || !isEnabled) return;

    _emit(const NfcUiState.waiting());
    try {
      _sessionActive = true;
      await NfcManager.instance.startSession(
        pollingOptions: {NfcPollingOption.iso14443},
        alertMessageIos: 'Acerque su teléfono al lector de la puerta',
        onDiscovered: _onDiscovered,
        onSessionErrorIos: _onIosSessionError,
      );
      _armScanTimeout();
    } catch (e) {
      debugPrint('NfcService.startSession falló: $e');
      _sessionActive = false;
      _emit(const NfcUiState.error('No se pudo iniciar el NFC. Intenta de nuevo.'));
    }
  }

  /// Cancela la espera (botón "Cancelar", app en segundo plano...).
  Future<void> cancel() async {
    _scanTimeout?.cancel();
    if (_busy) return; // no abortar un envío en curso
    await _closeSession();
    if (!_disposed && isEnabled) _emit(_idle());
  }

  /// Reenvía el último punto leído sin pedir un nuevo toque (tras un error de red).
  Future<void> retrySend() async {
    final point = _lastPoint;
    if (_disposed || _busy || point == null || _session == null) return;
    _busy = true;
    await _send(point);
  }

  /// Libera TODO: timers, sesión nativa y notifier. Llamar desde `dispose()`.
  void dispose() {
    if (_disposed) return;
    _disposed = true;
    _scanTimeout?.cancel();
    _successReset?.cancel();
    unawaited(_closeSession());
    state.dispose();
  }

  // ---------------------------------------------------------------------------
  // Callbacks NFC
  // ---------------------------------------------------------------------------

  Future<void> _onDiscovered(NfcTag tag) async {
    if (_disposed || _busy) return; // Android puede disparar varias veces seguidas
    _busy = true;
    _scanTimeout?.cancel();

    final point = await _extractPoint(tag);
    if (point == null) {
      await _fail('Etiqueta no reconocida. Acerca el teléfono al punto de acceso.');
      return;
    }
    _lastPoint = point;
    await _send(point);
  }

  void _onIosSessionError(NfcReaderSessionErrorIos error) {
    // iOS ya invalidó la sesión por su cuenta.
    _sessionActive = false;
    _scanTimeout?.cancel();
    if (_disposed || _busy) return;
    if (state.value.phase != NfcPhase.waiting) return;

    switch (error.code) {
      case NfcReaderErrorCodeIos.readerSessionInvalidationErrorUserCanceled:
      case NfcReaderErrorCodeIos.readerSessionInvalidationErrorSessionTimeout:
        _emit(_idle());
      default:
        _emit(NfcUiState.error(error.message));
    }
  }

  // ---------------------------------------------------------------------------
  // Envío con reintentos
  // ---------------------------------------------------------------------------

  Future<void> _send(CheckInPoint point) async {
    final session = _session;
    if (session == null) {
      await _fail('No hay una sesión activa.');
      return;
    }

    _emit(const NfcUiState.sending());
    ApiException? lastError;

    for (var attempt = 1; attempt <= AppConfig.maxSendAttempts; attempt++) {
      try {
        final result = await _access.registerAccess(session, point);
        if (_disposed) return;

        await _closeSession(alertMessageIos: 'Acceso registrado');
        _busy = false;
        _emit(NfcUiState.success(result));
        _successReset?.cancel();
        _successReset = Timer(AppConfig.successResetDelay, () {
          if (!_disposed && state.value.phase == NfcPhase.success) {
            _emit(_idle());
          }
        });
        return;
      } on SessionExpiredException {
        await _closeSession(errorMessageIos: 'Sesión expirada');
        _busy = false;
        if (!_disposed) onSessionExpired?.call();
        return;
      } on ApiException catch (e) {
        lastError = e;
        if (!e.retryable) break; // rechazo de negocio: no insistir
        if (attempt < AppConfig.maxSendAttempts) {
          await Future<void>.delayed(Duration(seconds: attempt));
          if (_disposed) return;
        }
      } catch (e) {
        debugPrint('NfcService._send error inesperado: $e');
        lastError = const ApiException('Error inesperado al registrar el acceso.');
        break;
      }
    }

    await _fail(
      lastError?.message ?? 'No se pudo registrar el acceso.',
      canRetry: lastError?.retryable ?? false,
    );
  }

  Future<void> _fail(String message, {bool canRetry = false}) async {
    await _closeSession(errorMessageIos: message);
    _busy = false;
    _emit(NfcUiState.error(message, canRetry: canRetry && _lastPoint != null));
  }

  // ---------------------------------------------------------------------------
  // Utilidades
  // ---------------------------------------------------------------------------

  void _armScanTimeout() {
    _scanTimeout?.cancel();
    _scanTimeout = Timer(AppConfig.scanTimeout, () async {
      if (_disposed || _busy) return;
      await _closeSession();
      _emit(const NfcUiState.idle(
        detail: 'Tiempo agotado. Toca el botón para intentar de nuevo.',
      ));
    });
  }

  /// Cierra la sesión nativa de forma idempotente (nunca lanza).
  Future<void> _closeSession({
    String? alertMessageIos,
    String? errorMessageIos,
  }) async {
    if (!_sessionActive) return;
    _sessionActive = false;
    try {
      await NfcManager.instance.stopSession(
        alertMessageIos: alertMessageIos,
        errorMessageIos: errorMessageIos,
      );
    } catch (e) {
      debugPrint('NfcService.stopSession: $e');
    }
  }

  void _emit(NfcUiState next) {
    if (_disposed) return;
    state.value = next;
    if (next.phase == NfcPhase.success) {
      HapticFeedback.heavyImpact();
    }
  }

  // ---------------------------------------------------------------------------
  // Lectura de la etiqueta
  // ---------------------------------------------------------------------------

  /// Obtiene el identificador del punto de acceso a partir de la etiqueta.
  /// Prioridad: registro NDEF (texto o URI) > UID de la etiqueta.
  Future<CheckInPoint?> _extractPoint(NfcTag tag) async {
    Uint8List? uid;
    NdefMessage? message;

    try {
      // IMPORTANTE: los helpers `.from(tag)` son específicos de plataforma;
      // usarlos en la plataforma equivocada lanza un TypeError.
      switch (defaultTargetPlatform) {
        case TargetPlatform.android:
          uid = NfcTagAndroid.from(tag)?.id;
          final ndef = NdefAndroid.from(tag);
          if (ndef != null) {
            message = ndef.cachedNdefMessage ?? await ndef.getNdefMessage();
          }
        case TargetPlatform.iOS:
          uid = MiFareIos.from(tag)?.identifier ??
              Iso7816Ios.from(tag)?.identifier ??
              Iso15693Ios.from(tag)?.identifier;
          message = NdefIos.from(tag)?.cachedNdefMessage;
        default:
          break;
      }
    } catch (e) {
      debugPrint('NfcService._extractPoint falló: $e');
    }

    final uidHex = uid == null
        ? ''
        : uid.map((b) => b.toRadixString(16).padLeft(2, '0')).join().toUpperCase();
    final ndefId = _pointIdFromNdef(message);
    final pointId = ndefId ?? uidHex;
    if (pointId.isEmpty) return null;

    return CheckInPoint(
      pointId: pointId.length > AppConfig.maxPointIdLength
          ? pointId.substring(0, AppConfig.maxPointIdLength)
          : pointId,
      tagUid: uidHex,
    );
  }

  static const List<String> _uriPrefixes = [
    '',
    'http://www.',
    'https://www.',
    'http://',
    'https://',
    'tel:',
    'mailto:',
  ];

  /// Decodifica el primer registro NDEF well-known de tipo Texto ('T') o URI ('U').
  String? _pointIdFromNdef(NdefMessage? message) {
    if (message == null) return null;

    for (final record in message.records) {
      if (record.typeNameFormat != TypeNameFormat.wellKnown) continue;
      if (record.type.length != 1 || record.payload.isEmpty) continue;

      final payload = record.payload;
      switch (record.type[0]) {
        case 0x54: // 'T' - texto: [status][lang...][texto]
          final langLength = payload[0] & 0x3F;
          if (payload.length <= 1 + langLength) continue;
          final text = utf8
              .decode(payload.sublist(1 + langLength), allowMalformed: true)
              .trim();
          if (text.isNotEmpty) return text;
        case 0x55: // 'U' - URI: [prefijo][resto]
          final prefix =
              payload[0] < _uriPrefixes.length ? _uriPrefixes[payload[0]] : '';
          final uri = utf8.decode(payload.sublist(1), allowMalformed: true).trim();
          if (uri.isNotEmpty) return '$prefix$uri';
      }
    }
    return null;
  }
}
