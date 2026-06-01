import 'dart:math'; // Required for sine wave
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:phosphor_flutter/phosphor_flutter.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:cozy_app/core/theme.dart';
import 'package:cozy_app/data/providers.dart';

class EnergyFlowView extends ConsumerWidget {
  const EnergyFlowView({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final summaryAsync = ref.watch(dashboardSummaryProvider);
    
    // Safety check for data
    final current = summaryAsync.value?['current'] ?? {
      'solar_power_kw': 0.0,
      'grid_power_kw': 0.0,
      'battery_power_kw': 0.0,
      'ev_power_kw': 0.0, // Added EV
      'home_load_kw': 0.0,
      'battery_soc': 0.0,
    };

    final solar = (current['solar_power_kw'] as num).toDouble();
    final grid = (current['grid_power_kw'] as num).toDouble(); 
    final battery = (current['battery_power_kw'] as num).toDouble();
    final ev = (current['ev_power_kw'] as num).toDouble(); // EV Power
    final load = (current['home_load_kw'] as num).toDouble();
    final soc = (current['battery_soc'] as num).toDouble();

    return LayoutBuilder(
      builder: (context, constraints) {
        return Stack(
          clipBehavior: Clip.none,
          alignment: Alignment.center,
          children: [
            // 1. Energy Waves (Background Layer - Behind House)
            // Solar -> House (Top -> Center)
            if (solar > 0)
              Positioned.fill(
                child: _EnergyWave(
                  start: const Alignment(0, -0.9), // Higher start
                  end: const Alignment(0, 0),
                  color: AppTheme.warmYellow,
                ),
              ),

            // Grid <-> House (Right <-> Center)
            if (grid != 0)
              Positioned.fill(
                child: _EnergyWave(
                  start: const Alignment(0.8, -0.2), // From Pole
                  end: const Alignment(0.2, 0.1), 
                  color: AppTheme.charcoal,
                  reversed: grid < 0,
                ),
              ),

            // Battery <-> House (Left <-> Center)
            if (battery.abs() > 0)
              Positioned.fill(
                child: _EnergyWave(
                  start: const Alignment(-0.8, -0.1), // From Battery
                  end: const Alignment(-0.2, 0.1), 
                  color: AppTheme.terracotta,
                  reversed: battery < 0,
                ),
              ),

            // EV <-> House (Bottom Left <-> Center)
            if (ev.abs() > 0)
              Positioned.fill(
                child: _EnergyWave(
                  start: const Alignment(-0.7, 0.7), // From Car
                  end: const Alignment(0, 0.3), 
                  color: AppTheme.charcoal,
                  reversed: ev < 0,
                ),
              ),

            // 2. Visual Assets (Unified Scene)
            // House, Solar, Battery, EV, Grid all in one render
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 0, vertical: 20),
              child: Image.asset(
                'assets/images/combined_scene_v5.png',
                fit: BoxFit.contain,
              ).animate().fadeIn(duration: 800.ms),
            ),

            // 3. Data Bubbles (Foreground Layer) - Re-aligned to V5 Scene
            
            // Solar (Top Roof) - Higher above panels
            Positioned(
              top: 30,
              child: _DataBubble(
                value: "${solar.toStringAsFixed(1)} kW",
                label: "SOLAR",
                icon: PhosphorIcons.sun(PhosphorIconsStyle.fill),
                color: AppTheme.warmYellow,
                isPulse: solar > 0,
              ),
            ),

            // Grid (Far Right Pole) - Aligned with transformer
            Positioned(
              top: 140,
              right: 20,
              child: _DataBubble(
                value: "${grid.abs().toStringAsFixed(1)} kW",
                label: grid > 0 ? "IMPORT" : "EXP",
                icon: PhosphorIcons.lightning(PhosphorIconsStyle.fill),
                color: AppTheme.charcoal, 
                isPulse: grid != 0,
              ),
            ),

            // Battery (Left Wall) - Pulled in closer to orange box
            Positioned(
              top: 140,
              left: 40,
              child: _DataBubble(
                value: "${soc.toStringAsFixed(0)}%",
                label: battery > 0 ? "DISCHG" : (battery < 0 ? "CHG" : "BAT"),
                icon: PhosphorIcons.batteryCharging(PhosphorIconsStyle.fill),
                color: AppTheme.terracotta,
                isPulse: battery.abs() > 0.05,
              ),
            ),

            // EV (Bottom Left Car) - Aligned with car hood
            Positioned(
              bottom: 60,
              left: 20,
              child: _DataBubble(
                value: "${ev.abs().toStringAsFixed(1)} kW",
                label: "EV",
                icon: PhosphorIcons.car(PhosphorIconsStyle.fill),
                color: AppTheme.charcoal,
                isPulse: ev.abs() > 0.05,
              ),
            ),

             // House Load (Bottom Base) - Shifted right
            Positioned(
              bottom: 0,
              child: Transform.translate(
                offset: const Offset(60, 0),
                child: _DataBubble(
                  value: "${load.toStringAsFixed(1)} kW",
                  label: "HOME",
                  icon: PhosphorIcons.house(PhosphorIconsStyle.fill),
                  color: AppTheme.dullRed,
                  isPulse: load > 0.05,
                ),
              ),
            ),
          ],
        );
      },
    );
  }
}
// -----------------------------------------------------------------------------
// Animated Energy Wave Widget
// -----------------------------------------------------------------------------
class _EnergyWave extends StatefulWidget {
  final Alignment start;
  final Alignment end;
  final Color color;
  final bool reversed;

  const _EnergyWave({
    required this.start,
    required this.end,
    required this.color,
    this.reversed = false,
  });

  @override
  State<_EnergyWave> createState() => _EnergyWaveState();
}

class _EnergyWaveState extends State<_EnergyWave> with SingleTickerProviderStateMixin {
  late AnimationController _controller;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 2), // Slow, fluid wave
    )..repeat();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _controller,
      builder: (context, child) {
        return CustomPaint(
          painter: _WavePainter(
            start: widget.start,
            end: widget.end,
            color: widget.color,
            progress: _controller.value,
            reversed: widget.reversed,
          ),
        );
      },
    );
  }
}

class _WavePainter extends CustomPainter {
  final Alignment start;
  final Alignment end;
  final Color color;
  final double progress;
  final bool reversed;

  _WavePainter({
    required this.start,
    required this.end,
    required this.color,
    required this.progress,
    required this.reversed,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final p1 = Offset(
      (start.x + 1) / 2 * size.width,
      (start.y + 1) / 2 * size.height,
    );
    final p2 = Offset(
      (end.x + 1) / 2 * size.width,
      (end.y + 1) / 2 * size.height,
    );

    final glowLayers = [
      {'width': 80.0, 'opacity': 0.02, 'blur': 30.0},
      {'width': 55.0, 'opacity': 0.05, 'blur': 18.0},
      {'width': 35.0, 'opacity': 0.09, 'blur': 10.0},
      {'width': 18.0, 'opacity': 0.14, 'blur': 4.0},
      {'width': 8.0, 'opacity': 0.20, 'blur': 1.0},
    ];

    final path = Path();
    final angle = (p2 - p1).direction;

    // Generate Wave Path
    path.moveTo(p1.dx, p1.dy);

    const int segments = 20;
    for (int i = 0; i <= segments; i++) {
      final t = i / segments;
      // Calculate point on straight line
      final x = p1.dx + (p2.dx - p1.dx) * t;
      final y = p1.dy + (p2.dy - p1.dy) * t;

      // Add sine wave offset perpendicular to line
      // Flow moves from Start -> End usually. 
      // If Reversed: End -> Start.
      // Phase Shift: 2 * pi * t - (2 * pi * progress)
      
      double animationPhase = progress * 2 * pi;
      if (reversed) animationPhase *= -1;

      final waveAmplitude = 15.0 * sin(pi * t); // Taper at ends
      final waveOffset = sin(4 * pi * t - animationPhase) * waveAmplitude;

      // Rotate offset by angle + 90 degrees to be perpendicular
      final offsetX = waveOffset * cos(angle + pi / 2);
      final offsetY = waveOffset * sin(angle + pi / 2);

      path.lineTo(x + offsetX, y + offsetY);
    }

    // Draw progressive glow layers
    for (final layer in glowLayers) {
      final width = layer['width'] as double;
      final opacity = layer['opacity'] as double;
      final blur = layer['blur'] as double;

      final paint = Paint()
        ..color = color.withOpacity(opacity)
        ..style = PaintingStyle.stroke
        ..strokeWidth = width
        ..strokeCap = StrokeCap.round;

      if (blur > 0) {
        paint.maskFilter = MaskFilter.blur(BlurStyle.normal, blur);
      }

      canvas.drawPath(path, paint);
    }
  }

  @override
  bool shouldRepaint(covariant _WavePainter oldDelegate) {
    return oldDelegate.progress != progress || oldDelegate.color != color;
  }
}

class _DataBubble extends StatelessWidget {
  final String value;
  final String? label;
  final IconData icon;
  final Color color;
  final bool isPulse;

  const _DataBubble({
    required this.value,
    this.label,
    required this.icon,
    required this.color,
    this.isPulse = false,
  });

  @override
  Widget build(BuildContext context) {
    final bubble = Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(24),
        boxShadow: [
          BoxShadow(
            color: color.withOpacity(isPulse ? 0.25 : 0.15),
            blurRadius: isPulse ? 16 : 12,
            offset: const Offset(0, 4),
          ),
        ],
        border: Border.all(color: color.withOpacity(isPulse ? 0.2 : 0.1), width: 1.5),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            padding: const EdgeInsets.all(6),
            decoration: BoxDecoration(
              color: color.withOpacity(0.1),
              shape: BoxShape.circle,
            ),
            child: Icon(icon, size: 14, color: color),
          ),
          const SizedBox(width: 10),
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                value,
                style: const TextStyle(
                  color: AppTheme.charcoal,
                  fontWeight: FontWeight.bold,
                  fontSize: 15,
                ),
              ),
              if (label != null)
                Text(
                  label!,
                  style: TextStyle(
                    color: Colors.grey[600],
                    fontSize: 10,
                    fontWeight: FontWeight.w600,
                    letterSpacing: 0.8,
                  ),
                ),
            ],
          ),
        ],
      ),
    );

    if (isPulse) {
      // Elegant custom breathing pulse animation loop using flutter_animate
      return bubble
          .animate()
          .scale(duration: 300.ms, curve: Curves.easeOutBack)
          .then()
          .animate(onPlay: (controller) => controller.repeat(reverse: true))
          .scale(
            begin: const Offset(1, 1),
            end: const Offset(1.05, 1.05),
            duration: 1200.ms,
            curve: Curves.easeInOut,
          );
    } else {
      return bubble.animate().scale(duration: 300.ms, curve: Curves.easeOutBack);
    }
  }
}
