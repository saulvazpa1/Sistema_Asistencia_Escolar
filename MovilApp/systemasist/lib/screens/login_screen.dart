import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../core/app_exceptions.dart';
import '../core/app_theme.dart';
import '../models/auth_session.dart';
import '../services/auth_service.dart';
import '../widgets/nexo_logo.dart';

/// Inicio de sesión del alumno (matrícula + contraseña).
class LoginScreen extends StatefulWidget {
  const LoginScreen({
    super.key,
    required this.authService,
    required this.onLoggedIn,
  });

  final AuthService authService;

  /// El padre persiste la sesión cifrada y navega a la credencial.
  final Future<void> Function(AuthSession session) onLoggedIn;

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _formKey = GlobalKey<FormState>();
  final _matriculaCtrl = TextEditingController();
  final _passwordCtrl = TextEditingController();
  final _passwordFocus = FocusNode();

  bool _loading = false;
  bool _obscure = true;
  String? _error;

  static final RegExp _matriculaRegExp = RegExp(r'^[A-Za-z0-9]{6,20}$');

  @override
  void dispose() {
    _matriculaCtrl.dispose();
    _passwordCtrl.dispose();
    _passwordFocus.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (_loading) return;
    FocusScope.of(context).unfocus();
    if (!(_formKey.currentState?.validate() ?? false)) return;

    setState(() {
      _loading = true;
      _error = null;
    });

    try {
      final session = await widget.authService.login(
        matricula: _matriculaCtrl.text,
        password: _passwordCtrl.text,
      );
      TextInput.finishAutofillContext(); // ofrece guardar credenciales al gestor del sistema
      await widget.onLoggedIn(session);
      // Si todo sale bien, el padre reemplaza esta pantalla; no hay setState posterior.
    } on ApiException catch (e) {
      _showError(e.message);
    } catch (_) {
      _showError(
        'No se pudo guardar la sesión de forma segura. Intenta de nuevo.',
      );
    }
  }

  void _showError(String message) {
    if (!mounted) return;
    setState(() {
      _loading = false;
      _error = message;
    });
  }

  InputDecoration _decoration({
    required String hint,
    required IconData icon,
    Widget? suffix,
  }) {
    OutlineInputBorder border(Color color, [double width = 1.5]) =>
        OutlineInputBorder(
          borderRadius: BorderRadius.circular(8),
          borderSide: BorderSide(color: color, width: width),
        );

    return InputDecoration(
      hintText: hint,
      hintStyle: const TextStyle(color: NexoColors.fieldHint),
      prefixIcon: Icon(icon, color: NexoColors.fieldHint),
      suffixIcon: suffix,
      filled: true,
      fillColor: NexoColors.field,
      contentPadding: const EdgeInsets.symmetric(vertical: 16),
      border: border(NexoColors.fieldBorder),
      enabledBorder: border(NexoColors.fieldBorder),
      focusedBorder: border(NexoColors.green, 2),
      errorBorder: border(NexoColors.errorText),
      focusedErrorBorder: border(NexoColors.errorText, 2),
      errorStyle: const TextStyle(color: NexoColors.errorText),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.symmetric(horizontal: 28, vertical: 24),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 420),
              child: AutofillGroup(
                child: Form(
                  key: _formKey,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      const Center(child: NexoLogo(size: 110)),
                      const SizedBox(height: 16),
                      const Text(
                        'NexoEscolar',
                        textAlign: TextAlign.center,
                        style: TextStyle(
                          color: Colors.white,
                          fontSize: 34,
                          fontWeight: FontWeight.w800,
                        ),
                      ),
                      const SizedBox(height: 28),
                      const Text(
                        'Ingresa tu matrícula',
                        textAlign: TextAlign.center,
                        style: TextStyle(color: Colors.white, fontSize: 20),
                      ),
                      const SizedBox(height: 10),
                      TextFormField(
                        controller: _matriculaCtrl,
                        enabled: !_loading,
                        style: const TextStyle(color: Colors.white),
                        textCapitalization: TextCapitalization.characters,
                        keyboardType:
                            TextInputType.visiblePassword, // sin autocorrección
                        textInputAction: TextInputAction.next,
                        autofillHints: const [AutofillHints.username],
                        inputFormatters: [
                          FilteringTextInputFormatter.allow(
                            RegExp(r'[A-Za-z0-9]'),
                          ),
                          LengthLimitingTextInputFormatter(20),
                        ],
                        decoration: _decoration(
                          hint: '20258TTH89',
                          icon: Icons.person,
                        ),
                        onFieldSubmitted: (_) => _passwordFocus.requestFocus(),
                        validator: (value) {
                          final v = value?.trim() ?? '';
                          if (v.isEmpty) return 'Ingresa tu matrícula';
                          if (!_matriculaRegExp.hasMatch(v)) {
                            return 'Matrícula no válida (6 a 20 letras o números)';
                          }
                          return null;
                        },
                      ),
                      const SizedBox(height: 22),
                      const Text(
                        'Ingresa tu contraseña',
                        textAlign: TextAlign.center,
                        style: TextStyle(color: Colors.white, fontSize: 20),
                      ),
                      const SizedBox(height: 10),
                      TextFormField(
                        controller: _passwordCtrl,
                        focusNode: _passwordFocus,
                        enabled: !_loading,
                        obscureText: _obscure,
                        enableSuggestions: false,
                        autocorrect: false,
                        style: const TextStyle(color: Colors.white),
                        textInputAction: TextInputAction.done,
                        autofillHints: const [AutofillHints.password],
                        decoration: _decoration(
                          hint: '••••••••',
                          icon: Icons.lock,
                          suffix: IconButton(
                            tooltip: _obscure
                                ? 'Mostrar contraseña'
                                : 'Ocultar contraseña',
                            icon: Icon(
                              _obscure
                                  ? Icons.visibility
                                  : Icons.visibility_off,
                              color: NexoColors.fieldHint,
                            ),
                            onPressed: () =>
                                setState(() => _obscure = !_obscure),
                          ),
                        ),
                        onFieldSubmitted: (_) => _submit(),
                        validator: (value) => (value == null || value.isEmpty)
                            ? 'Ingresa tu contraseña'
                            : null,
                      ),
                      if (_error != null) ...[
                        const SizedBox(height: 18),
                        Semantics(
                          liveRegion: true,
                          child: Container(
                            padding: const EdgeInsets.all(12),
                            decoration: BoxDecoration(
                              color: NexoColors.danger.withValues(alpha: 0.25),
                              border: Border.all(color: NexoColors.errorText),
                              borderRadius: BorderRadius.circular(8),
                            ),
                            child: Row(
                              children: [
                                const Icon(
                                  Icons.error_outline,
                                  color: NexoColors.errorText,
                                ),
                                const SizedBox(width: 10),
                                Expanded(
                                  child: Text(
                                    _error!,
                                    style: const TextStyle(color: Colors.white),
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ),
                      ],
                      const SizedBox(height: 30),
                      Center(
                        child: SizedBox(
                          width: 200,
                          child: FilledButton(
                            onPressed: _loading ? null : _submit,
                            child: _loading
                                ? const SizedBox(
                                    width: 24,
                                    height: 24,
                                    child: CircularProgressIndicator(
                                      strokeWidth: 3,
                                      color: Colors.white,
                                    ),
                                  )
                                : const Text('Iniciar'),
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
