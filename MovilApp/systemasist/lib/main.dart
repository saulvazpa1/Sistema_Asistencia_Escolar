import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import 'core/app_config.dart';
import 'core/app_theme.dart';
import 'models/auth_session.dart';
import 'screens/digital_id_screen.dart';
import 'screens/login_screen.dart';
import 'services/access_service.dart';
import 'services/auth_service.dart';
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

  AuthSession? _session;
  bool _booting = true;

  @override
  void initState() {
    super.initState();
    _restoreSession();
  }

  // ------ La credencial ya descargada se recupera del alamcenamiento cifrado ------
  Future<void> _restoreSession() async {
    final session = await _storage.loadSession();
    if (!mounted) return;
    setState(() {
      _session = session;
      _booting = false;
    });
  }

  Future<void> _handleLoggedIn(AuthSession session) async {
    // -------- Mostrar Error si falla LoginScreen --------

    await _storage.saveSession(session);

    if (!mounted) return;
    setState(() => _session = session);
  }

  Future<void> _handleLogOut() async {
    await _storage.clear();
    if (!mounted) return;
    setState(() => _session = null);
  }

  @override
  Widget build(BuildContext context) {
    final session = _session;

    final Widget home;

    if (_booting) {
      home = const Scaffold(body: Center(child: CircularProgressIndicator()));
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
        onLogout: _handleLogOut,
      );
    }

    return MaterialApp(
      title: 'Nexo Escolar',
      debugShowCheckedModeBanner: false,
      theme: buildNexoTheme(),
      home: home,
    );
  }
}
