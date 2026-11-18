import 'student.dart';

/// Sesión del alumno: token + UID únicos y los datos de su credencial.
///
/// Respuesta esperada del login:
/// ```json
/// {
///   "token": "<token opaco>",
///   "uid": "<identificador único del alumno>",
///   "alumno": { "matricula": "...", "nombre_completo": "...", "curp": "...",
///               "carrera": "...", "grupo": "...", "foto_url": "...",
///               "credencial_activa": true, "telegram_vinculado": true }
/// }
/// ```
class AuthSession {
  const AuthSession({
    required this.token,
    required this.uid,
    required this.student,
  });

  final String token;
  final String uid;
  final Student student;

  AuthSession copyWith({Student? student}) =>
      AuthSession(token: token, uid: uid, student: student ?? this.student);

  factory AuthSession.fromLoginJson(Map<String, dynamic> json) {
    final token = json['token'];
    final uid = json['uid'];
    final alumno = json['alumno'];

    if (token is! String || token.isEmpty) {
      throw const FormatException('Respuesta sin "token".');
    }
    if (uid is! String || uid.isEmpty) {
      throw const FormatException('Respuesta sin "uid".');
    }
    if (alumno is! Map<String, dynamic>) {
      throw const FormatException('Respuesta sin datos de "alumno".');
    }
    return AuthSession(
      token: token,
      uid: uid,
      student: Student.fromJson(alumno),
    );
  }
}
