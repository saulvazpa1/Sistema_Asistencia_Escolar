/// Punto de acceso físico (etiqueta NFC fija en la puerta) leído por el teléfono.
class CheckInPoint {
  const CheckInPoint({required this.pointId, required this.tagUid});

  /// Identificador lógico del punto (registro NDEF de texto/URI, p. ej. "NEXO:PUERTA_PRINCIPAL").
  /// Si la etiqueta no trae NDEF se usa el UID hexadecimal de la etiqueta.
  final String pointId;

  /// UID hexadecimal de la etiqueta (vacío si el sistema no lo expone).
  final String tagUid;
}

/// Respuesta del servidor al registrar un acceso.
class AccessResult {
  const AccessResult({
    required this.ok,
    required this.tipo,
    required this.mensaje,
    required this.fechaHora,
  });

  final bool ok;

  /// "entrada" o "salida" (lo determina el servidor según el último movimiento).
  final String tipo;
  final String mensaje;
  final DateTime fechaHora;

  bool get esEntrada => tipo.toLowerCase() == 'entrada';

  factory AccessResult.fromJson(Map<String, dynamic> json) {
    final rawDate = json['fecha_hora'];
    return AccessResult(
      ok: json['ok'] as bool? ?? true,
      tipo: (json['tipo'] as String?) ?? 'entrada',
      mensaje: (json['mensaje'] as String?) ?? 'Acceso registrado',
      fechaHora: (rawDate is String ? DateTime.tryParse(rawDate) : null)
              ?.toLocal() ??
          DateTime.now(),
    );
  }
}
