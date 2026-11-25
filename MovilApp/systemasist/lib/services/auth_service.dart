import 'dart:convert';

import 'package:http/http.dart' as http;

import '../core/app_config.dart';
import '../core/app_exceptions.dart';
import '../models/auth_session.dart';
import '../models/student.dart';
import 'http_helpers.dart';

class AuthService {
  AuthService({http.Client? client}) : _client = client ?? http.Client();

  final http.Client _client;

  Future<CredentialStatus> credentialStatus(AuthSession session) async {
    if (AppConfig.useMock) {
      return const CredentialStatus(activa: true, telegramVinculado: true);
    }

    final response = await guardedRequest(
      () => _client.get(
        Uri.parse('${AppConfig.baseUrl}/credencial/estado'),
        headers: {...jsonHeaders, 'Authorization': 'Bearer ${session.token}'},
      ),
    );

    if (response.statusCode == 401) {
      throw const SessionExpiredException();
    }

    if (response.statusCode != 200) {
      throw apiErrorFromResponse(response);
    }

    final json = decodeJsonObject(response);

    if (json == null) {
      throw const ApiException('Respuesta inválida del servidor.');
    }

    return CredentialStatus(
      activa: json['activa'] as bool? ?? false,
      telegramVinculado: json['telegramVinculado'] as bool? ?? false,
    );
  }

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

  Future<bool> credentialIsActive(AuthSession session) async {
    if (AppConfig.useMock) return true;

    final response = await guardedRequest(
      () => _client.get(
        Uri.parse('${AppConfig.baseUrl}/credencial/estado'),
        headers: {...jsonHeaders, 'Authorization': 'Bearer ${session.token}'},
      ),
    );
    if (response.statusCode == 401) throw const SessionExpiredException();
    if (response.statusCode != 200) throw apiErrorFromResponse(response);
    return decodeJsonObject(response)?['activa'] as bool? ?? true;
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

    return AuthSession(
      token: 'mock-token-20258TTH89',
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

class CredentialStatus {
  final bool activa;
  final bool telegramVinculado;

  const CredentialStatus({
    required this.activa,
    required this.telegramVinculado,
  });
}
