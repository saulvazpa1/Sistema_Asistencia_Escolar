import 'dart:convert';

import 'package:crypto/crypto.dart';

import 'student.dart';

class AuthSession {
  const AuthSession({
    required this.token,
    required this.uid,
    required this.student,
  });

  final String token;

  /// ID único de la credencial (`uid`); es lo que viaja por NFC / QR hacia el lector.
  final String uid;
  final Student student;

  String get signingKey => sha256.convert(utf8.encode(token)).toString();

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
