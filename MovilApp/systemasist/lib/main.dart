import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import 'core/app_config.dart';
import 'core/app_theme.dart';
import 'models/auth_session.dart';
import 'screens/digital_id_screen.dart';
import 'screens/login_screen.dart';
import 'screens/spashScreen.dart';
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

  @override
  void initState() {
    super.initState();
    _restoreSession();
  }

  /// La credencial ya descargada se recupera del almacenamiento cifrado (funciona offline).
  Future<void> _restoreSession() async {
    // La lectura cifrada y el tiempo mínimo del splash corren en paralelo.
    final results = await Future.wait<Object?>([
      _storage.loadSession(),
      Future<void>.delayed(AppConfig.splashMinDuration),
    ]);
    final session = results.first as AuthSession?;
<<<<<<< HEAD
=======
    if (session != null)
      await _hce.sync(session); // re-sincroniza la copia del servicio HCE
>>>>>>> temp-cambios
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
<<<<<<< HEAD
=======
    await _hce.sync(session);
>>>>>>> temp-cambios
    if (!mounted) return;
    setState(() => _session = session);
  }

<<<<<<< HEAD
  Future<void> _handleLogout() async {
=======
  /// Guarda la foto nueva (cifrada junto con la sesión) y actualiza la credencial en pantalla.
  Future<void> _handlePhotoChanged(Uint8List bytes) async {
    final current = _session;
    if (current == null) return;
    final updated = current.copyWith(student: current.student.withPhoto(bytes));
    await _storage.saveSession(updated);
    if (!mounted) return;
    setState(() => _session = updated);
  }

  Future<void> _handleLogout() async {
    await _hce.clear(); // el lector de la puerta deja de recibir la credencial
>>>>>>> temp-cambios
    await _storage.clear();
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
      );
    } else {
      home = DigitalIdScreen(
        key: ValueKey(session.uid),
        session: session,
        accessService: _accessService,
        onLogout: _handleLogout,
<<<<<<< HEAD
=======
        onPhotoChanged: _handlePhotoChanged,
>>>>>>> temp-cambios
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
