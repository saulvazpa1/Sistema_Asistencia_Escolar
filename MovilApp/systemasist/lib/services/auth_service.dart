import 'dart:convert';
import 'dart:math';

import 'package:http/http.dart' as http;

import '../core/app_config.dart';
import '../core/app_exceptions.dart';
import '../models/auth_session.dart';
import '../models/student.dart';
import 'http_helpers.dart';

class AuthService {
  AuthService({http.Client? client}) : _client = client ?? http.Client();

  final http.Client _client;

  Future<AuthSession> login({
    required String matricula,
    required String password,
  }) {
    final cleanMatricula = matricula.trim().toUpperCase();
    return AppConfig.useMock
        ? _mockLogin(cleanMatricula, password)
        : _remoteLogin(cleanMatricula, password);
  }

  Future<AuthSession> _remoteLogin(String matricula, String password) async {
    final response = await guardedRequest(
      () => _client.post(
        Uri.parse('${AppConfig.baseUrl}/auth/login'),
        headers: jsonHeaders,
        body: jsonEncode({
          'matricula': matricula,
          'usuario_password': password,
        }),
      ),
    );

    if (response.statusCode == 401) {
      throw const ApiException(
        'Matrícula o contraseña incorrectas.',
        statusCode: 401,
      );
    }
    if (response.statusCode != 200) {
      throw apiErrorFromResponse(
        response,
        fallback: 'No fue posible iniciar sesión (${response.statusCode}).',
      );
    }

    final json = decodeJsonObject(response);
    if (json == null) {
      throw const ApiException('Respuesta inválida del servidor.');
    }
    try {
      return AuthSession.fromLoginJson(json);
    } on FormatException catch (e) {
      throw ApiException('Respuesta inválida del servidor: ${e.message}');
    }
  }

  /// Simulación para desarrollo: matrícula `20258TTH89` / contraseña `nexo1234`.
  Future<AuthSession> _mockLogin(String matricula, String password) async {
    await Future<void>.delayed(const Duration(milliseconds: 800));

    if (matricula != '20258TTH89' || password != 'nexo1234') {
      throw const ApiException(
        'Matrícula o contraseña incorrectas.',
        statusCode: 401,
      );
    }

    final random = Random.secure();
    final token = base64UrlEncode(
      List<int>.generate(32, (_) => random.nextInt(256)),
    );

    return AuthSession(
      token: token,
      uid: 'uid-20258TTH89',
      student: Student(
        matricula: '20258TTH89',
        nombreCompleto: 'Bot Sanchez Perez',
        curp: 'CAFT09878HGJH',
        carrera: 'TTH',
        grupo: '4A',
        credencialActiva: true,
        telegramVinculado: true,
      ),
    );
  }
}
