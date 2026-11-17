import 'dart:convert';
import 'dart:typed_data';

// ------------- Datos del estudiante que mostrar en la crendencial -----------

class Student {
  Student({
    required this.matricula,
    required this.nombreCompleto,
    required this.curp,
    required this.carrera,
    required this.grupo,
    this.fotoUrl,
    this.fotoBase64,
    this.credencialActiva = true,
    this.telegramVinculado = false,
  });

  final String matricula;
  final String nombreCompleto;
  final String curp;
  final String carrera;
  final String grupo;

  // ----------- Fotografia via URL o en base64 ----------
  final String? fotoUrl;
  final String? fotoBase64;

  final bool credencialActiva;
  final bool telegramVinculado;

  // ------- Bytes de la foto decodificados una sola vez --------
  late final Uint8List? fotoBytes = _decodePhoto();

  Uint8List? _decodePhoto() {
    final raw = fotoBase64;
    if (raw == null || raw.isEmpty) return null;
    try {
      // ----- Aceptar tanto base64 puro como "data:image/png;base64,..." -----
      final comma = raw.indexOf(',');
      final clean = raw.startsWith('data:') && comma != -1
          ? raw.substring(comma + 1)
          : raw;
      return base64Decode(clean);
    } on FormatException {
      return null;
    }
  }

  factory Student.fromJson(Map<String, dynamic> json) {
    return Student(
      matricula: _requiredString(json, 'matricula'),
      nombreCompleto: _requiredString(json, 'nombre_completo'),
      curp: _requiredString(json, 'curp'),
      carrera: _requiredString(json, 'carrera'),
      grupo: _requiredString(json, 'grupo'),
      fotoUrl: _optionalString(json, 'foto_url'),
      fotoBase64: _optionalString(json, 'foto_base64'),
      credencialActiva: json['credencial_activa'] as bool? ?? true,
      telegramVinculado: json['telegram_vinculado'] as bool? ?? false,
    );
  }

  Map<String, dynamic> toJson() => {
    'matricula': matricula,
    'nombre_completo': nombreCompleto,
    'curp': curp,
    'carrera': carrera,
    'grupo': grupo,
    'foto_url': fotoUrl,
    'foto_base64': fotoBase64,
    'credencial_activa': credencialActiva,
    'telegram_vinculado': telegramVinculado,
  };

  static String _requiredString(Map<String, dynamic> json, String key) {
    final value = json[key];
    if (value is! String || value.trim().isEmpty) {
      throw FormatException('Campo "$key" ausente o inválido en el alumno.');
    }
    return value.trim();
  }

  static String? _optionalString(Map<String, dynamic> json, String key) {
    final value = json[key];
    return value is String && value.isNotEmpty ? value : null;
  }
}
