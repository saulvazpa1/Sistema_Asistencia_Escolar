import 'dart:typed_data';

import 'package:image_picker/image_picker.dart';

/// Toma o elige la fotografía de la credencial (cámara frontal o galería).
///
/// La imagen se reduce al elegirla (720x960, calidad 80) para que pese poco, ya que se guarda
/// cifrada junto con la sesión en el almacenamiento seguro.
class PhotoService {
  PhotoService({ImagePicker? picker}) : _picker = picker ?? ImagePicker();

  final ImagePicker _picker;

  /// Límite de seguridad del tamaño final.
  static const int maxBytes = 1500000;

  /// Devuelve los bytes de la imagen, o `null` si el usuario cancela.
  Future<Uint8List?> pick(ImageSource source) async {
    final file = await _picker.pickImage(
      source: source,
      maxWidth: 720,
      maxHeight: 960,
      imageQuality: 80,
      preferredCameraDevice: CameraDevice.front,
    );
    if (file == null) return null;

    final bytes = await file.readAsBytes();
    if (bytes.length > maxBytes) {
      throw const FormatException('La imagen es demasiado grande.');
    }
    return bytes;
  }
}
