import 'package:material_ui/material_ui.dart';

import '../core/app_theme.dart';
import '../models/nfc_ui_state.dart';
import '../models/student.dart';

/// Modal "Propiedades": estado de credencial, vinculación con Telegram, NFC y cierre de sesión.
Future<void> showPropertiesDialog(
  BuildContext context, {
  required Student student,
  required String credentialId,
  required NfcUiState nfcState,
  required Future<void> Function() onLogout,
}) {
  return showDialog<void>(
    context: context,
    builder: (dialogContext) {
      final nfcOk = nfcState.phase != NfcPhase.disabled &&
          nfcState.phase != NfcPhase.unsupported;

      return Dialog(
        backgroundColor: NexoColors.modal,
        insetPadding: const EdgeInsets.symmetric(horizontal: 20),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
        child: Padding(
          padding: const EdgeInsets.fromLTRB(24, 24, 24, 20),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                'Propiedades',
                style: TextStyle(
                  color: Colors.white,
                  fontSize: 24,
                  fontWeight: FontWeight.w700,
                ),
              ),
              const SizedBox(height: 20),
              _Property(
                label: 'ID de credencial:',
                value: credentialId,
              ),
              _Property(
                label: 'Estado de credencial:',
                value: student.credencialActiva ? 'Activa' : 'Inactiva',
                valueColor:
                    student.credencialActiva ? Colors.white : NexoColors.errorText,
              ),
              _Property(
                label: 'Estatus de la Vinculación con Telegram:',
                value: student.telegramVinculado
                    ? 'Vinculado correctamente'
                    : 'Sin vincular. Pide a tu tutor completar el registro.',
                valueColor:
                    student.telegramVinculado ? Colors.white : NexoColors.warning,
              ),
              _Property(
                label: 'NFC del dispositivo:',
                value: nfcOk ? 'Disponible' : 'Desactivado o no disponible',
                valueColor: nfcOk ? Colors.white : NexoColors.warning,
              ),
              const SizedBox(height: 8),
              FilledButton(
                style: FilledButton.styleFrom(
                  backgroundColor: NexoColors.danger,
                  minimumSize: const Size.fromHeight(50),
                ),
                onPressed: () async {
                  Navigator.of(dialogContext).pop();
                  if (!context.mounted) return;
                  final confirmed = await showLogoutConfirmDialog(context);
                  if (confirmed == true) await onLogout();
                },
                child: const Text('Cerrar Sesión'),
              ),
            ],
          ),
        ),
      );
    },
  );
}

/// Confirmación previa al cierre de sesión (borra token y UID del dispositivo).
Future<bool?> showLogoutConfirmDialog(BuildContext context) {
  return showDialog<bool>(
    context: context,
    builder: (ctx) => AlertDialog(
      backgroundColor: NexoColors.modal,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
      title: const Text('¿Cerrar sesión?'),
      content: const Text(
        'Se eliminará tu credencial de este teléfono. '
        'Tendrás que iniciar sesión de nuevo para volver a usarla.',
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(ctx).pop(false),
          child: const Text('Cancelar'),
        ),
        FilledButton(
          style: FilledButton.styleFrom(
            backgroundColor: NexoColors.danger,
            minimumSize: const Size(0, 44),
          ),
          onPressed: () => Navigator.of(ctx).pop(true),
          child: const Text('Cerrar sesión'),
        ),
      ],
    ),
  );
}

class _Property extends StatelessWidget {
  const _Property({
    required this.label,
    required this.value,
    this.valueColor = Colors.white,
  });

  final String label;
  final String value;
  final Color valueColor;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 18),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            label,
            style: const TextStyle(
              color: Colors.white,
              fontSize: 17,
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(height: 2),
          Text(value, style: TextStyle(color: valueColor, fontSize: 17)),
        ],
      ),
    );
  }
}
