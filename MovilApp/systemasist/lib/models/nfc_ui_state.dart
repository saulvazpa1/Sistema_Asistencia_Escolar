import 'access_models.dart';

/// Fases del flujo NFC visibles para el usuario.
enum NfcPhase {
  checking,
  unsupported,
  disabled,
  idle,
  waiting,
  sending,
  success,
  error,
}

/// Estado inmutable que consume la UI (textos ya listos para mostrar).
class NfcUiState {
  const NfcUiState._({
    required this.phase,
    required this.title,
    this.detail,
    this.result,
    this.canRetry = false,
  });

  final NfcPhase phase;
  final String title;
  final String? detail;
  final AccessResult? result;

  /// En `error`: hay un punto ya leído que se puede reenviar sin volver a tocar la etiqueta.
  final bool canRetry;

  const NfcUiState.checking()
      : this._(phase: NfcPhase.checking, title: 'Verificando NFC…');

  const NfcUiState.unsupported()
      : this._(
          phase: NfcPhase.unsupported,
          title: 'Este dispositivo no tiene NFC',
          detail: 'Muestra el código QR de respaldo en la entrada.',
        );

  const NfcUiState.disabled()
      : this._(
          phase: NfcPhase.disabled,
          title: 'NFC desactivado',
          detail: 'Actívalo en los ajustes para registrar tu acceso.',
        );

  const NfcUiState.idle({String? detail, String? title})
      : this._(
          phase: NfcPhase.idle,
          title: title ?? 'Listo para registrar',
          detail: detail ?? 'Toca el botón y acerca tu teléfono al lector.',
        );

  const NfcUiState.waiting()
      : this._(
          phase: NfcPhase.waiting,
          title: 'Acerque al lector',
          detail: 'Mantén el teléfono junto al punto de acceso.',
        );

  const NfcUiState.sending()
      : this._(
          phase: NfcPhase.sending,
          title: 'Transmitiendo ID…',
          detail: 'No alejes el teléfono.',
        );

  NfcUiState.success(AccessResult r)
      : this._(
          phase: NfcPhase.success,
          title: 'Acceso registrado',
          detail: r.mensaje,
          result: r,
        );

  const NfcUiState.error(String message, {bool canRetry = false})
      : this._(
          phase: NfcPhase.error,
          title: 'No se pudo registrar',
          detail: message,
          canRetry: canRetry,
        );
}
