import 'package:material_ui/material_ui.dart';

import '../core/app_theme.dart';
import '../models/nfc_ui_state.dart';
import 'nfc_status_banner.dart';

/// Panel de estado NFC en tiempo real: "Acerque al lector" -> "Transmitiendo ID…" -> "Acceso registrado".
class NfcTransmitPanel extends StatelessWidget {
  const NfcTransmitPanel({
    super.key,
    required this.state,
    required this.credentialActive,
    required this.hceMode,
    required this.onStart,
    required this.onCancel,
    required this.onRetry,
  });

  final NfcUiState state;
  final bool credentialActive;

  /// Con HCE, el botón es solo para leer una etiqueta fija (modo lector).
  final bool hceMode;
  final VoidCallback onStart;
  final VoidCallback onCancel;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    final accent = _accentFor(state.phase);

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: NexoColors.navyDark,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: accent.withValues(alpha: 0.6)),
      ),
      child: Column(
        children: [
          SizedBox(
            height: 84,
            child: Center(child: _StatusIcon(phase: state.phase, color: accent)),
          ),
          const SizedBox(height: 12),
          // liveRegion: los lectores de pantalla anuncian cada cambio de estado.
          Semantics(
            liveRegion: true,
            child: AnimatedSwitcher(
              duration: const Duration(milliseconds: 250),
              child: Column(
                key: ValueKey('${state.phase}-${state.title}-${state.detail}'),
                children: [
                  Text(
                    state.title,
                    textAlign: TextAlign.center,
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 20,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  if (state.detail != null) ...[
                    const SizedBox(height: 6),
                    Text(
                      state.detail!,
                      textAlign: TextAlign.center,
                      style: const TextStyle(color: Colors.white70, fontSize: 14),
                    ),
                  ],
                ],
              ),
            ),
          ),
          const SizedBox(height: 18),
          _buildAction(),
        ],
      ),
    );
  }

  Widget _buildAction() {
    if (!credentialActive) {
      return const Text(
        'Tu credencial está inactiva. Acude a Servicios Estudiantiles.',
        textAlign: TextAlign.center,
        style: TextStyle(color: NexoColors.errorText),
      );
    }

    switch (state.phase) {
      case NfcPhase.idle:
        // Con HCE NO hay botón: pulsarlo abriría el modo lector y apagaría la tarjeta.
        if (hceMode) return const SizedBox.shrink();
        return FilledButton.icon(
          onPressed: onStart,
          icon: const Icon(Icons.nfc),
          label: Text(
            'Registrar acceso por NFC',
          ),
        );
      case NfcPhase.waiting:
        return OutlinedButton(onPressed: onCancel, child: const Text('Cancelar'));
      case NfcPhase.error:
        return FilledButton.icon(
          onPressed: onRetry,
          icon: const Icon(Icons.refresh),
          label: Text(state.canRetry ? 'Reintentar envío' : 'Intentar de nuevo'),
        );
      case NfcPhase.disabled:
        return FilledButton.icon(
          onPressed: openNfcSettings,
          icon: const Icon(Icons.settings),
          label: const Text('Activar NFC'),
        );
      case NfcPhase.checking:
      case NfcPhase.sending:
      case NfcPhase.success:
      case NfcPhase.unsupported:
        return const SizedBox.shrink();
    }
  }

  static Color _accentFor(NfcPhase phase) => switch (phase) {
        NfcPhase.success => NexoColors.green,
        NfcPhase.error => NexoColors.errorText,
        NfcPhase.disabled || NfcPhase.unsupported => NexoColors.warning,
        _ => NexoColors.fieldBorder,
      };
}

class _StatusIcon extends StatelessWidget {
  const _StatusIcon({required this.phase, required this.color});

  final NfcPhase phase;
  final Color color;

  @override
  Widget build(BuildContext context) {
    switch (phase) {
      case NfcPhase.waiting:
        return _PulsingNfcIcon(color: color);
      case NfcPhase.checking:
      case NfcPhase.sending:
        return SizedBox(
          width: 52,
          height: 52,
          child: CircularProgressIndicator(strokeWidth: 4, color: NexoColors.green),
        );
      case NfcPhase.success:
        return Icon(Icons.check_circle, size: 72, color: color);
      case NfcPhase.error:
        return Icon(Icons.error_outline, size: 72, color: color);
      case NfcPhase.disabled:
      case NfcPhase.unsupported:
        return Icon(Icons.nfc, size: 64, color: color);
      case NfcPhase.idle:
        return Icon(Icons.contactless_outlined, size: 64, color: color);
    }
  }
}

/// Icono NFC con ondas que se expanden (indica "esperando lectura").
class _PulsingNfcIcon extends StatefulWidget {
  const _PulsingNfcIcon({required this.color});

  final Color color;

  @override
  State<_PulsingNfcIcon> createState() => _PulsingNfcIconState();
}

class _PulsingNfcIconState extends State<_PulsingNfcIcon>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 1600),
  )..repeat();

  @override
  void dispose() {
    _controller.dispose(); // evita fuga del Ticker
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _controller,
      builder: (context, child) {
        final t = _controller.value;
        return Stack(
          alignment: Alignment.center,
          children: [
            Container(
              width: 40 + 44 * t,
              height: 40 + 44 * t,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                border: Border.all(
                  color: NexoColors.green.withValues(alpha: 1 - t),
                  width: 3,
                ),
              ),
            ),
            child!,
          ],
        );
      },
      child: Icon(Icons.nfc, size: 44, color: widget.color),
    );
  }
}
