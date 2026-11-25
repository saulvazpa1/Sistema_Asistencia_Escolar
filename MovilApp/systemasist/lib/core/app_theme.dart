import 'package:material_ui/material_ui.dart';

/// Paleta corporativa NexoEscolar (tomada de los maquetados del proyecto).
abstract final class NexoColors {
  static const Color navy = Color(0xFF1B365D);
  static const Color navyDark = Color(0xFF14213A);
  static const Color green = Color(0xFF27A844);
  static const Color card = Color(0xFFEEF1F5);
  static const Color cardText = Color(0xFF1B2330);
  static const Color field = Color(0xFF2A3744);
  static const Color fieldBorder = Color(0xFFA9B4C2);
  static const Color fieldHint = Color(0xFF8795A6);
  static const Color modal = Color(0xFF24272B);
  static const Color danger = Color(0xFFA30B30);
  static const Color errorText = Color(0xFFFF8A80);
  static const Color warning = Color(0xFFF2A93B);
}

ThemeData buildNexoTheme() {
  final scheme =
      ColorScheme.fromSeed(
        seedColor: NexoColors.green,
        brightness: Brightness.dark,
      ).copyWith(
        primary: NexoColors.green,
        onPrimary: Colors.white,
        surface: NexoColors.navy,
        error: NexoColors.errorText,
      );

  return ThemeData(
    useMaterial3: true,
    colorScheme: scheme,
    scaffoldBackgroundColor: NexoColors.navy,
    filledButtonTheme: FilledButtonThemeData(
      style: FilledButton.styleFrom(
        backgroundColor: NexoColors.green,
        foregroundColor: Colors.white,
        minimumSize: const Size.fromHeight(52),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
        textStyle: const TextStyle(fontSize: 18, fontWeight: FontWeight.w600),
      ),
    ),
    outlinedButtonTheme: OutlinedButtonThemeData(
      style: OutlinedButton.styleFrom(
        foregroundColor: Colors.white,
        side: const BorderSide(color: NexoColors.fieldBorder),
        minimumSize: const Size.fromHeight(48),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
      ),
    ),
  );
}
