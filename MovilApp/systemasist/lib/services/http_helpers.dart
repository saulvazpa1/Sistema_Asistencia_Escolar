import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:http/http.dart' as http;

import '../core/app_config.dart';
import '../core/app_exceptions.dart';

/// Ejecuta una petición con timeout y traduce los fallos de red a [NetworkException].
Future<http.Response> guardedRequest(
  Future<http.Response> Function() send,
) async {
  try {
    return await send().timeout(AppConfig.requestTimeout);
  } on TimeoutException {
    throw const NetworkException('La conexión tardó demasiado. Intenta de nuevo.');
  } on HandshakeException {
    throw const NetworkException('No se pudo establecer una conexión segura.');
  } on SocketException {
    throw const NetworkException('Sin conexión a Internet.');
  } on http.ClientException {
    throw const NetworkException('No se pudo contactar al servidor.');
  }
}

/// Decodifica el cuerpo como objeto JSON (UTF-8). Devuelve `null` si no lo es.
Map<String, dynamic>? decodeJsonObject(http.Response response) {
  if (response.bodyBytes.isEmpty) return null;
  try {
    final decoded = jsonDecode(utf8.decode(response.bodyBytes));
    return decoded is Map<String, dynamic> ? decoded : null;
  } on FormatException {
    return null;
  }
}

/// Construye un [ApiException] a partir de una respuesta no exitosa.
ApiException apiErrorFromResponse(
  http.Response response, {
  String fallback = 'Ocurrió un error inesperado.',
}) {
  final body = decodeJsonObject(response);
  final serverMessage = (body?['mensaje'] ?? body?['message'] ?? body?['detail']);
  final status = response.statusCode;
  return ApiException(
    serverMessage is String && serverMessage.isNotEmpty
        ? serverMessage
        : fallback,
    statusCode: status,
    retryable: status >= 500 || status == 408 || status == 429,
  );
}

const Map<String, String> jsonHeaders = {
  'Content-Type': 'application/json; charset=utf-8',
  'Accept': 'application/json',
};
