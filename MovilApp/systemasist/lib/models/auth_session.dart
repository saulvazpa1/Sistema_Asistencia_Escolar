import 'student.dart';

// ----------- Sesión del alumno con token + UID unicos y los datos de su credencial

class AuthSession {
  AuthSession({required this.token, required this.uid, required this.student});

  final String token;
  final String uid;
  final Student student;

  factory AuthSession.fromLoginJson(Map<String, dynamic> json) {
    final token = json['token'];
    final uid = json['uid'];
    final alumno = json['alumno'];

    if (token is! String || token.isEmpty) {
      throw const FormatException('Token inválido en la respuesta del login.');
    }
    if (uid is! String || uid.isEmpty) {
      throw const FormatException('UID inválido en la respuesta del login.');
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
