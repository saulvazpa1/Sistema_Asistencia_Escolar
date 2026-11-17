class CheckInPoint {
  const CheckInPoint({required this.pointId, required this.tagUid});

  final String pointId;

  final String tagUid;
}

// --------- Respuesta del backend al registrar un acceso (entrada/salida) ---------
class AccessResult {
  const AccessResult({
    required this.ok,
    required this.tipo,
    required this.mensaje,
    required this.fechaHora,
  });

  final bool ok;

  // ------- Entrada o salida, según la configuración del punto de acceso. -------
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
      fechaHora:
          (rawDate is String ? DateTime.tryParse(rawDate) : null)?.toLocal() ??
          DateTime.now(),
    );
  }
}
