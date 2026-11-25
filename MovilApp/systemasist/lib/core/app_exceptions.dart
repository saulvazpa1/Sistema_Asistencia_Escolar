/// Error devuelto por el backend o por la capa de red.
class ApiException implements Exception {
  const ApiException(this.message, {this.statusCode, this.retryable = false});

  /// Mensaje apto para mostrar al usuario (español).
  final String message;
  final int? statusCode;

  /// `true` si vale la pena reintentar automáticamente (red caída, 5xx, 429...).
  final bool retryable;

  @override
  String toString() => 'ApiException($statusCode): $message';
}

/// Sin conexión, timeout o fallo TLS. Siempre reintentable.
class NetworkException extends ApiException {
  const NetworkException(super.message) : super(retryable: true);
}

/// El servidor rechazó el token (401): hay que volver a iniciar sesión.
class SessionExpiredException extends ApiException {
  const SessionExpiredException()
      : super('Tu sesión ya no es válida (se abrió en otro teléfono o expiró). Inicia sesión de nuevo.', statusCode: 401);
}
