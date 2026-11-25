import 'package:material_ui/material_ui.dart';

import '../core/app_theme.dart';
import '../services/hce_service.dart';

/// Lista de comprobación de la tarjeta NFC: dice qué falta para que el lector reciba el ID.
class HceStatusCard extends StatelessWidget {
  const HceStatusCard({super.key, required this.status});

  final HceStatus? status;

  @override
  Widget build(BuildContext context) {
    final s = status;
    if (s == null) return const SizedBox.shrink();

    final touch = _touchText(s);
    final rows = <_Row>[
      if (s.nativeMissing)
        const _Row(
          false,
          'Falta el código nativo de la app',
          'Reemplaza MainActivity.kt, ejecuta "flutter clean" y vuelve a instalar.',
        )
      else ...[
        _Row(
          s.hceSupported,
          'Emulación de tarjeta (HCE)',
          s.hceSupported ? null : 'Este teléfono no soporta HCE. Usa el QR de respaldo.',
        ),
        _Row(
          s.nfcEnabled,
          'NFC del teléfono',
          s.nfcEnabled ? null : 'Actívalo en Ajustes > NFC.',
        ),
        _Row(
          s.serviceRegistered,
          'Servicio de tarjeta instalado',
          s.serviceRegistered
              ? null
              : 'Revisa AndroidManifest.xml y res/xml/apduservice.xml y reinstala la app.',
        ),
        _Row(
          s.hasCredential && s.active,
          'Credencial lista en el teléfono',
          s.hasCredential
              ? (s.active ? null : 'La credencial está inactiva.')
              : 'No guardada (${s.vaultError ?? 'sin datos'}). Cierra sesión y vuelve a entrar.',
        ),
      ],
    ];

    final ready = s.ready;
    final color = ready ? NexoColors.green : NexoColors.warning;

    return Container(
      margin: const EdgeInsets.only(top: 12),
      padding: const EdgeInsets.fromLTRB(16, 14, 16, 14),
      decoration: BoxDecoration(
        color: NexoColors.navyDark,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: color.withValues(alpha: 0.6)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            ready ? 'Tarjeta lista: acerca el teléfono al lector' : 'La tarjeta NO está lista',
            style: TextStyle(color: color, fontWeight: FontWeight.w700, fontSize: 15),
          ),
          const SizedBox(height: 8),
          for (final r in rows) r,
          if (touch != null) ...[
            const SizedBox(height: 6),
            Text(touch, style: const TextStyle(color: Colors.white60, fontSize: 12.5)),
          ],
        ],
      ),
    );
  }

  static String? _touchText(HceStatus s) {
    if (s.nativeMissing) return null;
    if (s.lastTouchAt <= 0) {
      return 'El lector aún no ha tocado este teléfono.';
    }
    final secs = DateTime.now()
        .difference(DateTime.fromMillisecondsSinceEpoch(s.lastTouchAt))
        .inSeconds;
    final ago = secs < 60
        ? 'hace $secs s'
        : secs < 3600
            ? 'hace ${secs ~/ 60} min'
            : 'hace ${secs ~/ 3600} h';
    return 'Último toque del lector: $ago → ${s.lastResult ?? 'sin dato'}';
  }
}

class _Row extends StatelessWidget {
  const _Row(this.ok, this.title, this.hint);

  final bool ok;
  final String title;
  final String? hint;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 6),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(
            ok ? Icons.check_circle : Icons.error_outline,
            size: 18,
            color: ok ? NexoColors.green : NexoColors.errorText,
          ),
          const SizedBox(width: 8),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title, style: const TextStyle(color: Colors.white, fontSize: 14)),
                if (hint != null)
                  Text(hint!, style: const TextStyle(color: Colors.white60, fontSize: 12.5)),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
