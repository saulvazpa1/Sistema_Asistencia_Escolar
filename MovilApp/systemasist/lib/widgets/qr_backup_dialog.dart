import 'dart:async';
import 'dart:convert';

import 'package:crypto/crypto.dart';
import 'package:flutter/material.dart';
import 'package:qr_flutter/qr_flutter.dart';

import '../core/app_config.dart';
import '../core/app_theme.dart';
import '../models/auth_session.dart';

Future<void> showQrBackupDialog(BuildContext context, AuthSession session) {
  return showDialog<void>(
    context: context,
    builder: (_) => _QrBackupDialog(session: session),
  );
}

class _QrBackupDialog extends StatefulWidget {
  const _QrBackupDialog({required this.session});

  final AuthSession session;

  @override
  State<_QrBackupDialog> createState() => _QrBackupDialogState();
}

class _QrBackupDialogState extends State<_QrBackupDialog> {
  Timer? _ticker;
  late String _payload;
  int _remaining = AppConfig.qrRefreshSeconds;

  @override
  void initState() {
    super.initState();
    _payload = _buildPayload();
    _ticker = Timer.periodic(const Duration(seconds: 1), (_) {
      if (!mounted) return;
      setState(() {
        _remaining--;
        if (_remaining <= 0) {
          _remaining = AppConfig.qrRefreshSeconds;
          _payload = _buildPayload();
        }
      });
    });
  }

  @override
  void dispose() {
    _ticker?.cancel();
    super.dispose();
  }

  String _buildPayload() {
    final ts = DateTime.now().millisecondsSinceEpoch ~/ 1000;
    final message = '${widget.session.uid}.$ts';
    final signature = Hmac(
      sha256,
      utf8.encode(widget.session.token),
    ).convert(utf8.encode(message)).toString();
    return jsonEncode({
      'v': 1,
      'uid': widget.session.uid,
      'ts': ts,
      'sig': signature,
    });
  }

  @override
  Widget build(BuildContext context) {
    final student = widget.session.student;

    return Dialog(
      backgroundColor: NexoColors.modal,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Text(
              'Código QR de respaldo',
              style: TextStyle(
                color: Colors.white,
                fontSize: 20,
                fontWeight: FontWeight.w700,
              ),
            ),
            const SizedBox(height: 4),
            Text(
              student.matricula,
              style: const TextStyle(color: Colors.white70),
            ),
            const SizedBox(height: 16),
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(8),
              ),
              child: QrImageView(
                data: _payload,
                size: 220,
                backgroundColor: Colors.white,
                errorCorrectionLevel: QrErrorCorrectLevel.M,
              ),
            ),
            const SizedBox(height: 12),
            Text(
              'Se actualiza en $_remaining s',
              style: const TextStyle(color: Colors.white70, fontSize: 13),
            ),
            const SizedBox(height: 6),
            const Text(
              'Muéstralo al personal de seguridad si el lector NFC no responde.',
              textAlign: TextAlign.center,
              style: TextStyle(color: Colors.white70, fontSize: 13),
            ),
            const SizedBox(height: 16),
            FilledButton(
              onPressed: () => Navigator.of(context).pop(),
              child: const Text('Cerrar'),
            ),
          ],
        ),
      ),
    );
  }
}
