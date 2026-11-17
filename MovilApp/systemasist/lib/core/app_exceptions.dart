// -------- Error devuelto por el backend o por la capa de red ---------

class ApiException implements Exception {
  const ApiException(this.message, {this.statusCode, this.retryable = false});

  final String message;
  final int? statusCode;

  final bool retryable;

  @override
  String toString() => 'ApiException($statusCode): $message';
}

// ---- Sin conexión a internet, o timeout de la petición HTTP -----

class NetworkException extends ApiException {
  const NetworkException(super.message) : super(retryable: true);
}

// -------- El servidor rechazo el token (401): hay que volver a iniciar sesion ----------
class SessionExpiredException extends ApiException {
  const SessionExpiredException()
    : super('Tu sesión expiró. Inicia sesión de nuevo.', statusCode: 401);
}
