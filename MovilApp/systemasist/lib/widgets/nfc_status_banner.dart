import 'package:app_settings/app_settings.dart';
import 'package:material_ui/material_ui.dart';

import '../core/app_theme.dart';
import '../models/nfc_ui_state.dart';

/// Abre la pantalla de ajustes NFC del sistema (Android) o los ajustes de la app (iOS).
Future<void> openNfcSettings() {
  return AppSettings.openAppSettings(type: AppSettingsType.nfc);
}

/// Banner interactivo: aparece solo cuando el NFC está apagado o no existe.
class NfcStatusBanner extends StatelessWidget {
  const NfcStatusBanner({super.key, required this.state});

  final NfcUiState state;

  @override
  Widget build(BuildContext context) {
    final visible = state.phase == NfcPhase.disabled ||
        state.phase == NfcPhase.unsupported;
    if (!visible) return const SizedBox.shrink();

    final canActivate = state.phase == NfcPhase.disabled;

    return Semantics(
      liveRegion: true,
      container: true,
      child: Container(
        margin: const EdgeInsets.only(bottom: 16),
        padding: const EdgeInsets.fromLTRB(14, 12, 8, 12),
        decoration: BoxDecoration(
          color: NexoColors.warning.withValues(alpha: 0.16),
          border: Border.all(color: NexoColors.warning),
          borderRadius: BorderRadius.circular(10),
        ),
        child: Row(
          children: [
            const Icon(Icons.nfc, color: NexoColors.warning),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    state.title,
                    style: const TextStyle(
                      color: Colors.white,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  if (state.detail != null)
                    Text(
                      state.detail!,
                      style: const TextStyle(color: Colors.white70, fontSize: 13),
                    ),
                ],
              ),
            ),
            if (canActivate)
              TextButton(
                onPressed: openNfcSettings,
                child: const Text(
                  'ACTIVAR',
                  style: TextStyle(
                    color: NexoColors.warning,
                    fontWeight: FontWeight.w800,
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }
}

/// Diálogo flotante que guía al usuario a activar el NFC.
Future<void> showNfcDisabledDialog(BuildContext context) {
  return showDialog<void>(
    context: context,
    builder: (ctx) => AlertDialog(
      backgroundColor: NexoColors.modal,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
      icon: const Icon(Icons.nfc, color: NexoColors.warning, size: 36),
      title: const Text('Activa el NFC'),
      content: const Text(
        'Para registrar tu entrada y salida necesitas tener el NFC encendido.\n\n'
        '1. Toca "Abrir ajustes".\n'
        '2. Activa la opción NFC.\n'
        '3. Regresa a NexoEscolar.',
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(ctx).pop(),
          child: const Text('Ahora no'),
        ),
        FilledButton(
          style: FilledButton.styleFrom(minimumSize: const Size(0, 44)),
          onPressed: () {
            Navigator.of(ctx).pop();
            openNfcSettings();
          },
          child: const Text('Abrir ajustes'),
        ),
      ],
    ),
  );
}
