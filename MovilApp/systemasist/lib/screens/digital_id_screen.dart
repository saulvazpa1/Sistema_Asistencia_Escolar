import 'dart:async';
import 'dart:typed_data';

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart' show ImageSource;

import '../core/app_config.dart';
import '../core/app_theme.dart';
import '../models/auth_session.dart';
import '../models/nfc_ui_state.dart';
import '../models/student.dart';
import '../services/access_service.dart';
import '../services/nfc_service.dart';
import '../services/photo_service.dart';
import '../widgets/nexo_logo.dart';
import '../widgets/nfc_status_banner.dart';
import '../widgets/nfc_transmit_panel.dart';
import '../widgets/properties_dialog.dart';
import '../widgets/qr_backup_dialog.dart';

/// Credencial digital + transmisión NFC (modo punto de acceso).
class DigitalIdScreen extends StatefulWidget {
  const DigitalIdScreen({
    super.key,
    required this.session,
    required this.accessService,
    required this.onLogout,
    required this.onPhotoChanged,
  });

  final AuthSession session;
  final AccessService accessService;

  /// Borra el almacenamiento cifrado y regresa al login.
  final Future<void> Function() onLogout;

  /// El padre guarda la foto nueva y reconstruye la credencial.
  final Future<void> Function(Uint8List bytes) onPhotoChanged;

  @override
  State<DigitalIdScreen> createState() => _DigitalIdScreenState();
}

class _DigitalIdScreenState extends State<DigitalIdScreen>
    with WidgetsBindingObserver {
  late final NfcService _nfc;
  final _photoService = PhotoService();
  bool _disabledDialogShown = false;

  Student get _student => widget.session.student;

  bool get _hceMode =>
      AppConfig.hceEnabledOnAndroid &&
      defaultTargetPlatform == TargetPlatform.android;

  bool get _autoStart =>
      AppConfig.autoStartScanOnAndroid &&
      defaultTargetPlatform == TargetPlatform.android &&
      _student.credencialActiva;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);

    _nfc = NfcService(accessService: widget.accessService, hceMode: _hceMode)
      ..onSessionExpired = _handleSessionExpired;
    unawaited(_bootNfc());
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _nfc.dispose(); // cierra la sesión NFC y libera timers / notifier
    super.dispose();
  }

  // --- Ciclo de vida --------------------------------------------------------

  @override
  void didChangeAppLifecycleState(AppLifecycleState lifecycle) {
    switch (lifecycle) {
      case AppLifecycleState.resumed:
        unawaited(_onResumed());
      case AppLifecycleState.paused:
      case AppLifecycleState.hidden:
        unawaited(
          _nfc.cancel(),
        ); // nunca dejar la sesión NFC abierta en segundo plano
      case AppLifecycleState.inactive:
      case AppLifecycleState.detached:
        break;
    }
  }

  Future<void> _bootNfc() async {
    await _nfc.refreshAvailability();
    if (!mounted) return;

    if (_nfc.isSupported && !_nfc.isEnabled && !_disabledDialogShown) {
      _disabledDialogShown = true;
      await showNfcDisabledDialog(context);
      return;
    }
    if (_nfc.isEnabled && _autoStart) await _nfc.startScan(widget.session);
  }

  /// Al volver de los ajustes el usuario pudo haber activado el NFC.
  Future<void> _onResumed() async {
    await _nfc.refreshAvailability();
    if (!mounted) return;
    final phase = _nfc.state.value.phase;
    if (_nfc.isEnabled && _autoStart && phase == NfcPhase.idle) {
      await _nfc.startScan(widget.session);
    }
  }

  void _handleSessionExpired() {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('Tu sesión expiró. Inicia sesión de nuevo.'),
      ),
    );
    unawaited(widget.onLogout());
  }

  // --- Acciones -------------------------------------------------------------

  void _startScan() => unawaited(_nfc.startScan(widget.session));

  void _retry() {
    if (_nfc.state.value.canRetry) {
      unawaited(_nfc.retrySend());
    } else {
      _startScan();
    }
  }

  Future<void> _confirmLogout() async {
    final confirmed = await showLogoutConfirmDialog(context);
    if (confirmed == true) await widget.onLogout();
  }

  /// Agregar / cambiar la foto: cámara o galería.
  Future<void> _changePhoto() async {
    final source = await showModalBottomSheet<ImageSource>(
      context: context,
      backgroundColor: NexoColors.modal,
      builder: (ctx) => SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            ListTile(
              leading: const Icon(Icons.photo_camera, color: Colors.white),
              title: const Text('Tomar foto'),
              onTap: () => Navigator.of(ctx).pop(ImageSource.camera),
            ),
            ListTile(
              leading: const Icon(Icons.photo_library, color: Colors.white),
              title: const Text('Elegir de la galería'),
              onTap: () => Navigator.of(ctx).pop(ImageSource.gallery),
            ),
          ],
        ),
      ),
    );
    if (source == null || !mounted) return;

    try {
      final bytes = await _photoService.pick(source);
      if (bytes == null || !mounted) return; // el usuario canceló
      await widget.onPhotoChanged(bytes);
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('No se pudo guardar la foto. Intenta con otra imagen.'),
        ),
      );
    }
  }

  Future<void> _openProperties() {
    return showPropertiesDialog(
      context,
      student: _student,
      nfcState: _nfc.state.value,
      onLogout: widget.onLogout,
    );
  }

  // --- UI -------------------------------------------------------------------

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: Column(
          children: [
            _Header(onLogout: _confirmLogout, onInfo: _openProperties),
            Expanded(
              child: SingleChildScrollView(
                padding: const EdgeInsets.fromLTRB(20, 4, 20, 24),
                child: Center(
                  child: ConstrainedBox(
                    constraints: const BoxConstraints(maxWidth: 460),
                    child: ValueListenableBuilder<NfcUiState>(
                      valueListenable: _nfc.state,
                      builder: (context, nfcState, _) => Column(
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: [
                          NfcStatusBanner(state: nfcState),
                          const Padding(
                            padding: EdgeInsets.only(bottom: 10),
                            child: Text(
                              'Escanea tu credencial',
                              style: TextStyle(
                                color: Colors.white,
                                fontSize: 20,
                              ),
                            ),
                          ),
                          _CredentialCard(
                            student: _student,
                            onAddPhoto: _changePhoto,
                          ),
                          const SizedBox(height: 16),
                          NfcTransmitPanel(
                            state: nfcState,
                            credentialActive: _student.credencialActiva,
                            hceMode: _hceMode,
                            onStart: _startScan,
                            onCancel: () => unawaited(_nfc.cancel()),
                            onRetry: _retry,
                          ),
                          const SizedBox(height: 8),
                          TextButton.icon(
                            onPressed: () =>
                                showQrBackupDialog(context, widget.session),
                            icon: const Icon(
                              Icons.qr_code_2,
                              color: Colors.white70,
                            ),
                            label: const Text(
                              'Mostrar código QR de respaldo',
                              style: TextStyle(color: Colors.white70),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _Header extends StatelessWidget {
  const _Header({required this.onLogout, required this.onInfo});

  final VoidCallback onLogout;
  final VoidCallback onInfo;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 12, 8, 8),
      child: Row(
        children: [
          const NexoLogo(size: 48),
          const SizedBox(width: 12),
          const Expanded(
            child: Text(
              'NexoEscolar',
              style: TextStyle(
                color: Colors.white,
                fontSize: 24,
                fontWeight: FontWeight.w800,
              ),
            ),
          ),
          IconButton(
            tooltip: 'Estado de la credencial',
            iconSize: 28,
            color: Colors.white70,
            onPressed: onInfo,
            icon: const Icon(Icons.info_outline),
          ),
          IconButton(
            tooltip: 'Cerrar sesión',
            iconSize: 30,
            color: Colors.white,
            onPressed: onLogout,
            icon: const Icon(Icons.logout),
          ),
        ],
      ),
    );
  }
}

/// Tarjeta institucional: foto, nombre, matrícula, CURP, carrera y grupo.
class _CredentialCard extends StatelessWidget {
  const _CredentialCard({required this.student, required this.onAddPhoto});

  final Student student;
  final VoidCallback onAddPhoto;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.fromLTRB(24, 28, 24, 24),
      decoration: BoxDecoration(
        color: NexoColors.card,
        borderRadius: BorderRadius.circular(8),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Center(
            child: _Photo(student: student, onAddPhoto: onAddPhoto),
          ),
          const SizedBox(height: 10),
          Center(
            child: Text(
              student.nombreCompleto,
              textAlign: TextAlign.center,
              style: const TextStyle(
                color: NexoColors.cardText,
                fontSize: 21,
                fontWeight: FontWeight.w800,
              ),
            ),
          ),
          const SizedBox(height: 18),
          _Field(label: 'MATRÍCULA', value: student.matricula),
          _Field(label: 'CURP', value: student.curp),
          _Field(label: 'CARRERA', value: student.carrera),
          _Field(label: 'GRUPO', value: student.grupo),
          if (!student.credencialActiva) ...[
            const SizedBox(height: 8),
            Container(
              width: double.infinity,
              padding: const EdgeInsets.symmetric(vertical: 8),
              decoration: BoxDecoration(
                color: NexoColors.danger,
                borderRadius: BorderRadius.circular(6),
              ),
              child: const Text(
                'CREDENCIAL INACTIVA',
                textAlign: TextAlign.center,
                style: TextStyle(
                  color: Colors.white,
                  fontWeight: FontWeight.w800,
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }
}

class _Field extends StatelessWidget {
  const _Field({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Text(
        '$label: $value',
        style: const TextStyle(color: NexoColors.cardText, fontSize: 18),
      ),
    );
  }
}

/// Fotografía del alumno (bytes base64 > URL > marcador de posición) + botón QR.
class _Photo extends StatelessWidget {
  const _Photo({required this.student, required this.onAddPhoto});

  final Student student;
  final VoidCallback onAddPhoto;

  static const double _width = 180;
  static const double _height = 230;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: _width + 14,
      height: _height + 14,
      child: Stack(
        children: [
          Positioned(
            left: 0,
            top: 0,
            child: ClipRRect(
              borderRadius: BorderRadius.circular(4),
              child: SizedBox(width: _width, height: _height, child: _image()),
            ),
          ),
          Positioned(
            right: 0,
            bottom: 0,
            child: Material(
              color: NexoColors.modal,
              shape: const CircleBorder(),
              child: IconButton(
                tooltip: 'Agregar o cambiar foto',
                onPressed: onAddPhoto,
                icon: const Icon(Icons.add_a_photo, color: Colors.white),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _image() {
    final bytes = student.fotoBytes;
    if (bytes != null) {
      return Image.memory(
        bytes,
        fit: BoxFit.cover,
        gaplessPlayback: true,
        errorBuilder: (_, _, _) => const _PhotoPlaceholder(),
      );
    }
    final url = student.fotoUrl;
    if (url != null) {
      return Image.network(
        url,
        fit: BoxFit.cover,
        errorBuilder: (_, _, _) => const _PhotoPlaceholder(),
        loadingBuilder: (context, child, progress) =>
            progress == null ? child : const _PhotoPlaceholder(loading: true),
      );
    }
    return const _PhotoPlaceholder();
  }
}

class _PhotoPlaceholder extends StatelessWidget {
  const _PhotoPlaceholder({this.loading = false});

  final bool loading;

  @override
  Widget build(BuildContext context) {
    return ColoredBox(
      color: const Color(0xFF6F757E),
      child: Center(
        child: loading
            ? const CircularProgressIndicator(color: Colors.white)
            : const Icon(Icons.person, size: 110, color: Colors.white70),
      ),
    );
  }
}
