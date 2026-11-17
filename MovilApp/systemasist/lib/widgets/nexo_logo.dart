import 'package:flutter/material.dart';

import '../core/app_theme.dart';

class NexoLogo extends StatelessWidget {
  const NexoLogo({super.key, this.size = 56});

  final double size;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: size,
      height: size,
      child: Stack(
        alignment: Alignment.center,
        children: [
          Align(
            alignment: Alignment.topCenter,
            child: CustomPaint(
              size: Size(size * 0.30, size * 0.42),
              painter: _HexagonPainter(),
            ),
          ),
          Align(
            alignment: const Alignment(0, 0.45),
            child: Transform.rotate(
              angle: 0.75,
              child: Icon(Icons.edit, size: size * 0.62, color: Colors.white),
            ),
          ),
          Align(
            alignment: const Alignment(0, 0.45),
            child: Transform.rotate(
              angle: -0.75,
              child: Icon(
                Icons.straighten,
                size: size * 0.62,
                color: Colors.white,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _HexagonPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final w = size.width;
    final h = size.height;
    final path = Path()
      ..moveTo(w * 0.5, 0)
      ..lineTo(w, h * 0.25)
      ..lineTo(w, h * 0.75)
      ..lineTo(w * 0.5, h)
      ..lineTo(0, h * 0.75)
      ..lineTo(0, h * 0.25)
      ..close();

    canvas.drawPath(path, Paint()..color = NexoColors.green);
    canvas.drawPath(
      path,
      Paint()
        ..style = PaintingStyle.stroke
        ..strokeWidth = 1.5
        ..color = const Color(0xFF14602A),
    );
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}
