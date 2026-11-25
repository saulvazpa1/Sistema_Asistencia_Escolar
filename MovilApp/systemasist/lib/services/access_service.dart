import 'dart:convert';
import 'dart:io';

import 'package:http/http.dart' as http;

import '../core/app_config.dart';
import '../core/app_exceptions.dart';
import '../models/access_models.dart';
import '../models/auth_session.dart';
import 'http_helpers.dart';

/// Registro de acceso (entrada/salida) contra el backend.
///
/// Endpoint: POST {API_BASE_URL}/accesos
///   headers: Authorization: Bearer <token>
///   body:    { "uid", "punto_id", "tag_uid", "fecha_hora" (UTC ISO-8601), "plataforma" }
///   200/201: { "ok": true, "tipo": "entrada"|"salida", "mensaje": "...", "fecha_hora": "..." }
///   401:     token inválido/expirado -> [SessionExpiredException]
///   4xx:     rechazo de negocio (credencial inactiva, punto inválido...) -> no reintentable
///   5xx:     reintentable
class AccessService {
  AccessService({http.Client? client}) : _client = client ?? http.Client();

  final http.Client _client;

  // Solo para el modo simulación: alterna entrada / salida.
  static bool _mockNextIsEntry = true;

  Future<AccessResult> registerAccess(
    AuthSession session,
    CheckInPoint point,
  ) {
    return AppConfig.useMock
        ? _mockRegister(point)
        : _remoteRegister(session, point);
  }

  Future<AccessResult> _remoteRegister(
    AuthSession session,
    CheckInPoint point,
  ) async {
    final response = await guardedRequest(
      () => _client.post(
        Uri.parse('${AppConfig.baseUrl}/accesos'),
        headers: {
          ...jsonHeaders,
          'Authorization': 'Bearer ${session.token}',
        },
        body: jsonEncode({
          'uid': session.uid,
          'punto_id': point.pointId,
          'tag_uid': point.tagUid,
          'fecha_hora': DateTime.now().toUtc().toIso8601String(),
          'plataforma': Platform.operatingSystem,
        }),
      ),
    );

    if (response.statusCode == 401) throw const SessionExpiredException();

    if (response.statusCode != 200 && response.statusCode != 201) {
      throw apiErrorFromResponse(
        response,
        fallback: 'El servidor rechazó el registro (${response.statusCode}).',
      );
    }

    final json = decodeJsonObject(response);
    if (json == null) {
      throw const ApiException('Respuesta inválida del servidor.');
    }
    final result = AccessResult.fromJson(json);
    if (!result.ok) throw ApiException(result.mensaje);
    return result;
  }

  Future<AccessResult> _mockRegister(CheckInPoint point) async {
    await Future<void>.delayed(const Duration(milliseconds: 900));
    final isEntry = _mockNextIsEntry;
    _mockNextIsEntry = !_mockNextIsEntry;
    return AccessResult(
      ok: true,
      tipo: isEntry ? 'entrada' : 'salida',
      mensaje: isEntry ? 'Entrada registrada' : 'Salida registrada',
      fechaHora: DateTime.now(),
    );
  }
}
