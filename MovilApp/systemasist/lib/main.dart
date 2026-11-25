import 'dart:async';
import 'dart:typed_data';

import 'package:material_ui/material_ui.dart';
import 'package:flutter/services.dart';

import 'core/app_config.dart';
import 'core/app_exceptions.dart';
import 'core/app_theme.dart';
import 'models/auth_session.dart';
import 'screens/digital_id_screen.dart';
import 'screens/login_screen.dart';
import 'screens/splash_screen.dart';
import 'services/access_service.dart';
import 'services/auth_service.dart';
import 'services/hce_service.dart';
import 'services/secure_storage_service.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  AppConfig.assertSafeForRelease();
  await SystemChrome.setPreferredOrientations([DeviceOrientation.portraitUp]);
  runApp(const NexoEscolarApp());
}

class NexoEscolarApp extends StatefulWidget {
  const NexoEscolarApp({super.key});

  @override
  State<NexoEscolarApp> createState() => _NexoEscolarAppState();
}

class _NexoEscolarAppState extends State<NexoEscolarApp> {
  final _storage = SecureStorageService();
  final _authService = AuthService();
  final _accessService = AccessService();
  final _hce = const HceService();

  AuthSession? _session;
  bool _booting = true;
  String? _loginNotice;
  DateTime? _lastStatusCheck;

  @override
  void initState() {
    super.initState();
    _restoreSession();
  }

  /// La credencial ya descargada se recupera del almacenamiento cifrado (funciona offline).
  Future<void> _restoreSession() async {
    // La lectura cifrada y el tiempo mínimo del splash corren en paralelo.
    final results = await Future.wait<Object?>([
      _storage.loadSession().timeout(
        const Duration(seconds: 4),
        onTimeout: () => null,
      ),
      Future<void>.delayed(AppConfig.splashMinDuration),
    ]);
    final session = results.first as AuthSession?;
    // Re-sincroniza la copia del servicio HCE SIN bloquear el arranque.
    if (session != null) unawaited(_hce.sync(session));
    if (!mounted) return;
    setState(() {
      _session = session;
      _booting = false;
    });
  }

  Future<void> _handleLoggedIn(AuthSession session) async {
    await _storage.saveSession(
      session,
    ); // si falla, LoginScreen muestra el error
    await _hce.sync(session);
    if (!mounted) return;
    setState(() {
      _session = session;
      _loginNotice = null;
    });
  }

  /// Guarda la foto nueva (cifrada junto con la sesión) y actualiza la credencial en pantalla.
  Future<void> _handlePhotoChanged(Uint8List bytes) async {
    final current = _session;
    if (current == null) return;
    final updated = current.copyWith(student: current.student.withPhoto(bytes));
    await _storage.saveSession(updated);
    if (!mounted) return;
    setState(() => _session = updated);
  }

  /// Revisa con el servidor que la credencial siga vigente y ligada a este teléfono.
  /// - 401: la cuenta se abrió en otro teléfono (o expiró) -> cierra sesión aquí.
  /// - Dado de baja: marca la credencial inactiva y apaga la respuesta HCE.
  /// - Sin red u otro error: se ignora (la credencial sigue funcionando sin conexión).
  Future<void> _refreshCredentialStatus() async {
    final current = _session;
    if (current == null) return;

    final last = _lastStatusCheck;
    final now = DateTime.now();
    if (last != null && now.difference(last) < const Duration(seconds: 60))
      return;
    _lastStatusCheck = now;

    try {
      final status = await _authService.credentialStatus(current);
      if (status.activa == current.student.credencialActiva &&
          status.telegramVinculado == current.student.telegramVinculado) {
        return;
      }

      final updated = current.copyWith(
        student: current.student.copyWith(
          credencialActiva: status.activa,
          telegramVinculado: status.telegramVinculado,
        ),
      );
      await _storage.saveSession(updated);
      await _hce.sync(updated);
      if (!mounted) return;
      setState(() => _session = updated);
    } on SessionExpiredException catch (e) {
      _loginNotice = e.message;
      await _handleLogout();
    } on ApiException {
      // Sin conexión o servidor caído: no se toca la credencial local.
    }
  }

  Future<void> _handleLogout() async {
    unawaited(
      _hce.clear(),
    ); // el lector de la puerta deja de recibir la credencial
    await _storage.clear().timeout(
      const Duration(seconds: 4),
      onTimeout: () {},
    );
    if (!mounted) return;
    setState(() => _session = null);
  }

  @override
  Widget build(BuildContext context) {
    final session = _session;

    final Widget home;
    if (_booting) {
      home = const SplashScreen();
    } else if (session == null) {
      home = LoginScreen(
        authService: _authService,
        onLoggedIn: _handleLoggedIn,
        notice: _loginNotice,
      );
    } else {
      home = DigitalIdScreen(
        key: ValueKey(session.uid),
        session: session,
        accessService: _accessService,
        onLogout: _handleLogout,
        onPhotoChanged: _handlePhotoChanged,
        onRefreshStatus: _refreshCredentialStatus,
      );
    }

    return MaterialApp(
      title: 'NexoEscolar',
      debugShowCheckedModeBanner: false,
      theme: buildNexoTheme(),
      home: home,
    );
  }
}
