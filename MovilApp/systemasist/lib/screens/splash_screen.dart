import 'dart:math' as math;

import 'package:material_ui/material_ui.dart';

import '../core/app_theme.dart';

/// Splash de marca: logo minimalista de Bot Studios + aviso de copyright.
///
/// El logo se dibuja en código (sin assets) y se anima con una sola
/// [AnimationController]: aparece con escala + fundido, el wordmark sube y
/// los "ojos" del bot parpadean una vez al final.
class SplashScreen extends StatefulWidget {
  const SplashScreen({super.key});

  @override
  State<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends State<SplashScreen>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 1700),
  );

  late final Animation<double> _logoScale = CurvedAnimation(
    parent: _controller,
    curve: const Interval(0.0, 0.5, curve: Curves.easeOutBack),
  );
  late final Animation<double> _logoFade = CurvedAnimation(
    parent: _controller,
    curve: const Interval(0.0, 0.35, curve: Curves.easeOut),
  );
  late final Animation<double> _wordmark = CurvedAnimation(
    parent: _controller,
    curve: const Interval(0.35, 0.75, curve: Curves.easeOutCubic),
  );
  late final Animation<double> _footer = CurvedAnimation(
    parent: _controller,
    curve: const Interval(0.6, 1.0, curve: Curves.easeIn),
  );

  bool _started = false;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_started) return;
    _started = true;
    // Respeta "reducir movimiento" del sistema: muestra el estado final.
    if (MediaQuery.disableAnimationsOf(context)) {
      _controller.value = 1;
    } else {
      _controller.forward();
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  /// 0 = ojos abiertos, 1 = cerrados. Un parpadeo entre 80 % y 95 % de la animación.
  double _blink(double t) {
    if (t < 0.8 || t > 0.95) return 0;
    return math.sin((t - 0.8) / 0.15 * math.pi);
  }

  @override
  Widget build(BuildContext context) {
    final year = DateTime.now().year;

    return Scaffold(
      body: DecoratedBox(
        decoration: const BoxDecoration(
          gradient: RadialGradient(
            center: Alignment(0, -0.2),
            radius: 1.1,
            colors: [NexoColors.navy, NexoColors.navyDark],
          ),
        ),
        child: SafeArea(
          child: Semantics(
            label: 'Bot Studios',
            child: Column(
              children: [
                Expanded(
                  child: Center(
                    child: AnimatedBuilder(
                      animation: _controller,
                      builder: (context, _) {
                        return Column(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Opacity(
                              opacity: _logoFade.value.clamp(0.0, 1.0),
                              child: Transform.scale(
                                scale: 0.8 + 0.2 * _logoScale.value,
                                child: CustomPaint(
                                  size: const Size.square(132),
                                  painter: _BotMarkPainter(
                                    blink: _blink(_controller.value),
                                  ),
                                ),
                              ),
                            ),
                            const SizedBox(height: 28),
                            Opacity(
                              opacity: _wordmark.value.clamp(0.0, 1.0),
                              child: Transform.translate(
                                offset: Offset(0, 12 * (1 - _wordmark.value)),
                                child: const _Wordmark(),
                              ),
                            ),
                          ],
                        );
                      },
                    ),
                  ),
                ),
                FadeTransition(
                  opacity: _footer,
                  child: Padding(
                    padding: const EdgeInsets.fromLTRB(24, 0, 24, 24),
                    child: Text(
                      '© $year BotStudios. Todos los derechos reservados.',
                      textAlign: TextAlign.center,
                      style: const TextStyle(
                        color: Colors.white54,
                        fontSize: 12,
                        letterSpacing: 0.4,
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

/// "bot studios": minúsculas, "bot" en peso fuerte y "studios" ligero en verde.
class _Wordmark extends StatelessWidget {
  const _Wordmark();

  @override
  Widget build(BuildContext context) {
    return const Text.rich(
      TextSpan(
        children: [
          TextSpan(
            text: 'bot',
            style: TextStyle(color: Colors.white, fontWeight: FontWeight.w800),
          ),
          TextSpan(text: ' '),
          TextSpan(
            text: 'studios',
            style: TextStyle(color: NexoColors.green, fontWeight: FontWeight.w300),
          ),
        ],
      ),
      style: TextStyle(fontSize: 34, letterSpacing: 2.5, height: 1),
    );
  }
}

/// Marca: cabeza de robot geométrica (contorno redondeado, antena y dos ojos).
class _BotMarkPainter extends CustomPainter {
  const _BotMarkPainter({required this.blink});

  /// 0 = ojos abiertos, 1 = cerrados.
  final double blink;

  @override
  void paint(Canvas canvas, Size size) {
    final s = size.width;
    final stroke = s * 0.07;

    final line = Paint()
      ..color = NexoColors.green
      ..style = PaintingStyle.stroke
      ..strokeWidth = stroke
      ..strokeCap = StrokeCap.round;
    final fill = Paint()..color = NexoColors.green;
    final white = Paint()..color = Colors.white;

    // Cabeza
    final head = RRect.fromRectAndRadius(
      Rect.fromLTRB(s * 0.14, s * 0.28, s * 0.86, s * 0.88),
      Radius.circular(s * 0.22),
    );
    canvas.drawRRect(head, line);

    // Antena
    canvas.drawLine(Offset(s * 0.5, s * 0.28), Offset(s * 0.5, s * 0.14), line);
    canvas.drawCircle(Offset(s * 0.5, s * 0.09), s * 0.06, fill);

    // Orejas
    for (final x in [s * 0.05, s * 0.95]) {
      canvas.drawLine(Offset(x, s * 0.5), Offset(x, s * 0.66), line);
    }

    // Ojos (parpadean reduciendo su altura)
    final eyeH = s * 0.15 * (1 - 0.9 * blink);
    for (final cx in [s * 0.36, s * 0.64]) {
      canvas.drawRRect(
        RRect.fromRectAndRadius(
          Rect.fromCenter(
            center: Offset(cx, s * 0.58),
            width: s * 0.1,
            height: eyeH,
          ),
          Radius.circular(s * 0.05),
        ),
        white,
      );
    }
  }

  @override
  bool shouldRepaint(_BotMarkPainter old) => old.blink != blink;
}
