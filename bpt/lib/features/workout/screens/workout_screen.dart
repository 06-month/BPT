import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/constants/route_constants.dart';
import '../../../core/i18n/locale_provider.dart';
import '../../../core/theme/app_colors.dart';
import '../../../data/mock_data.dart';
import '../providers/workout_provider.dart';

class WorkoutScreen extends ConsumerStatefulWidget {
  const WorkoutScreen({super.key, required this.exerciseId});
  final String exerciseId;

  @override
  ConsumerState<WorkoutScreen> createState() => _WorkoutScreenState();
}

class _WorkoutScreenState extends ConsumerState<WorkoutScreen>
    with SingleTickerProviderStateMixin {
  late AnimationController _pulseCtrl;

  @override
  void initState() {
    super.initState();
    _pulseCtrl = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 800),
    )..repeat(reverse: true);

    WidgetsBinding.instance.addPostFrameCallback((_) {
      // initialize() is always called by the caller before navigation.
      // Only fall back to defaults if exercise doesn't match (direct navigation edge case).
      final w = ref.read(workoutProvider);
      if (w.exerciseId != widget.exerciseId) {
        final ex = findExercise(widget.exerciseId);
        ref.read(workoutProvider.notifier).initialize(
              widget.exerciseId,
              ex.defaultReps == 0 ? ex.defaultDurationSeconds : ex.defaultReps,
              ex.defaultSets,
            );
      }
      ref.read(workoutProvider.notifier).startCountdown();
    });
  }

  @override
  void dispose() {
    _pulseCtrl.dispose();
    super.dispose();
  }

  void _onComplete(WorkoutState w) {
    context.pushReplacement(
      RouteConstants.workoutResult,
      extra: {
        'exerciseId': w.exerciseId,
        'exerciseName': findExercise(w.exerciseId).name,
        'exerciseNameKr': findExercise(w.exerciseId).nameKr,
        'totalReps': w.currentReps,
        'correctReps': w.correctReps,
        'incorrectReps': w.incorrectReps,
        'elapsedSeconds': w.elapsedSeconds,
        'postureScore': w.postureScore,
        'feedbackHistory': w.feedbackHistory,
        'targetReps': w.targetReps,
        'targetSets': w.targetSets,
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    final s = ref.watch(appStringsProvider);
    final w = ref.watch(workoutProvider);
    final ex = findExercise(widget.exerciseId);
    final exName = s.locale == 'ko' ? ex.nameKr : ex.name;

    ref.listen(workoutProvider, (prev, next) {
      if (next.status == WorkoutStatus.complete &&
          prev?.status != WorkoutStatus.complete) {
        Future.delayed(const Duration(milliseconds: 600), () {
          if (mounted) _onComplete(next);
        });
      }
    });

    return Scaffold(
      backgroundColor: Colors.black,
      body: Stack(
        fit: StackFit.expand,
        children: [
          _CameraPlaceholder(isPoseDetected: w.isPoseDetected, strings: s),
          if (w.status == WorkoutStatus.active ||
              w.status == WorkoutStatus.paused)
            const _SkeletonOverlay(),
          _GradientOverlay(),
          if (w.status == WorkoutStatus.countdown)
            _CountdownOverlay(value: w.countdownValue, strings: s),
          Positioned(
            top: 0,
            left: 0,
            right: 0,
            child: _TopBar(
              exerciseName: exName,
              elapsed: w.elapsedFormatted,
              status: w.status,
              onPause: () =>
                  ref.read(workoutProvider.notifier).pauseWorkout(),
              onResume: () =>
                  ref.read(workoutProvider.notifier).resumeWorkout(),
              onStop: () {
                ref.read(workoutProvider.notifier).stopWorkout();
                _onComplete(ref.read(workoutProvider));
              },
            ),
          ),
          Positioned(
            bottom: 0,
            left: 0,
            right: 0,
            child: _BottomOverlay(state: w, pulseCtrl: _pulseCtrl),
          ),
          Positioned(
            top: 110,
            right: 20,
            child: _SetIndicator(
              current: w.currentSet,
              total: w.targetSets,
              setLabel: s.set,
            ),
          ),
        ],
      ),
    );
  }
}

// ── Camera Placeholder ─────────────────────────────────────────────────────
class _CameraPlaceholder extends StatelessWidget {
  const _CameraPlaceholder(
      {required this.isPoseDetected, required this.strings});
  final bool isPoseDetected;
  final dynamic strings;

  @override
  Widget build(BuildContext context) {
    final s = strings;
    return Container(
      color: const Color(0xFF0A0E1A),
      child: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              isPoseDetected
                  ? Icons.person_rounded
                  : Icons.camera_alt_outlined,
              color: Colors.white12,
              size: 80,
            ),
            const SizedBox(height: 12),
            Text(
              isPoseDetected ? s.poseDetected : s.cameraPreview,
              style: const TextStyle(color: Colors.white24, fontSize: 13),
            ),
          ],
        ),
      ),
    );
  }
}

// ── Skeleton Overlay ───────────────────────────────────────────────────────
class _SkeletonOverlay extends StatefulWidget {
  const _SkeletonOverlay();

  @override
  State<_SkeletonOverlay> createState() => _SkeletonOverlayState();
}

class _SkeletonOverlayState extends State<_SkeletonOverlay>
    with SingleTickerProviderStateMixin {
  late AnimationController _ctrl;
  late Animation<double> _anim;

  @override
  void initState() {
    super.initState();
    _ctrl = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1200),
    )..repeat(reverse: true);
    _anim = CurvedAnimation(parent: _ctrl, curve: Curves.easeInOut);
  }

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _anim,
      builder: (_, __) => CustomPaint(
        painter: _SkeletonPainter(_anim.value),
        size: Size.infinite,
      ),
    );
  }
}

class _SkeletonPainter extends CustomPainter {
  _SkeletonPainter(this.t);
  final double t;

  @override
  void paint(Canvas canvas, Size size) {
    final w = size.width;
    final h = size.height;
    final cx = w / 2;

    final paint = Paint()
      ..color = AppColors.primary.withValues(alpha: 0.6 + 0.4 * t)
      ..strokeWidth = 3
      ..strokeCap = StrokeCap.round
      ..style = PaintingStyle.stroke;

    final dotPaint = Paint()
      ..color = AppColors.primary.withValues(alpha: 0.9)
      ..style = PaintingStyle.fill;

    final squat = t * 0.12;
    final joints = <Offset>[
      Offset(cx, h * (0.18 + squat)),
      Offset(cx, h * (0.26 + squat)),
      Offset(cx - 0.08 * w, h * (0.30 + squat)),
      Offset(cx + 0.08 * w, h * (0.30 + squat)),
      Offset(cx - 0.12 * w, h * (0.42 + squat)),
      Offset(cx + 0.12 * w, h * (0.42 + squat)),
      Offset(cx - 0.14 * w, h * (0.54 + squat)),
      Offset(cx + 0.14 * w, h * (0.54 + squat)),
      Offset(cx, h * (0.46 + squat)),
      Offset(cx - 0.07 * w, h * (0.48 + squat)),
      Offset(cx + 0.07 * w, h * (0.48 + squat)),
      Offset(cx - 0.09 * w, h * (0.62 + squat)),
      Offset(cx + 0.09 * w, h * (0.62 + squat)),
      Offset(cx - 0.08 * w, h * (0.76 + squat)),
      Offset(cx + 0.08 * w, h * (0.76 + squat)),
    ];

    const connections = [
      [0, 1], [1, 2], [1, 3],
      [2, 4], [4, 6], [3, 5], [5, 7],
      [2, 9], [3, 10], [9, 10],
      [9, 11], [10, 12], [11, 13], [12, 14],
    ];

    for (final c in connections) {
      canvas.drawLine(joints[c[0]], joints[c[1]], paint);
    }
    for (final j in joints) {
      canvas.drawCircle(j, 5, dotPaint);
    }
  }

  @override
  bool shouldRepaint(_SkeletonPainter old) => old.t != t;
}

// ── Gradient Overlay ───────────────────────────────────────────────────────
class _GradientOverlay extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Container(
          height: 200,
          decoration: const BoxDecoration(
            gradient: LinearGradient(
              begin: Alignment.topCenter,
              end: Alignment.bottomCenter,
              colors: [Colors.black87, Colors.transparent],
            ),
          ),
        ),
        const Spacer(),
        Container(
          height: 300,
          decoration: const BoxDecoration(
            gradient: LinearGradient(
              begin: Alignment.bottomCenter,
              end: Alignment.topCenter,
              colors: [Colors.black87, Colors.transparent],
            ),
          ),
        ),
      ],
    );
  }
}

// ── Countdown Overlay ──────────────────────────────────────────────────────
class _CountdownOverlay extends StatelessWidget {
  const _CountdownOverlay({required this.value, required this.strings});
  final int value;
  final dynamic strings;

  @override
  Widget build(BuildContext context) {
    final s = strings;
    return Container(
      color: Colors.black54,
      child: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Text(
              value <= 0 ? 'GO!' : '$value',
              style: TextStyle(
                color: value <= 0 ? AppColors.primary : Colors.white,
                fontSize: 96,
                fontWeight: FontWeight.w900,
              ),
            ),
            const SizedBox(height: 16),
            Text(
              s.getReady,
              style: TextStyle(
                color: Colors.white.withValues(alpha: 0.6),
                fontSize: 18,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// ── Top Bar ────────────────────────────────────────────────────────────────
class _TopBar extends StatelessWidget {
  const _TopBar({
    required this.exerciseName,
    required this.elapsed,
    required this.status,
    required this.onPause,
    required this.onResume,
    required this.onStop,
  });
  final String exerciseName;
  final String elapsed;
  final WorkoutStatus status;
  final VoidCallback onPause;
  final VoidCallback onResume;
  final VoidCallback onStop;

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
        child: Row(
          children: [
            GestureDetector(
              onTap: onStop,
              child: Container(
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: Colors.black45,
                  borderRadius: BorderRadius.circular(12),
                ),
                child: const Icon(Icons.close_rounded,
                    color: Colors.white, size: 20),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    exerciseName,
                    style: const TextStyle(
                      color: Colors.white,
                      fontWeight: FontWeight.w700,
                      fontSize: 16,
                    ),
                  ),
                  Text(
                    elapsed,
                    style: const TextStyle(
                      color: AppColors.primary,
                      fontWeight: FontWeight.w600,
                      fontSize: 14,
                    ),
                  ),
                ],
              ),
            ),
            GestureDetector(
              onTap: status == WorkoutStatus.active ? onPause : onResume,
              child: Container(
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: Colors.black45,
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Icon(
                  status == WorkoutStatus.active
                      ? Icons.pause_rounded
                      : Icons.play_arrow_rounded,
                  color: Colors.white,
                  size: 22,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// ── Set Indicator ──────────────────────────────────────────────────────────
class _SetIndicator extends StatelessWidget {
  const _SetIndicator({
    required this.current,
    required this.total,
    required this.setLabel,
  });
  final int current;
  final int total;
  final String setLabel;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      decoration: BoxDecoration(
        color: Colors.black54,
        borderRadius: BorderRadius.circular(20),
      ),
      child: Text(
        '$setLabel $current / $total',
        style: const TextStyle(
          color: Colors.white,
          fontSize: 12,
          fontWeight: FontWeight.w600,
        ),
      ),
    );
  }
}

// ── Bottom Overlay ─────────────────────────────────────────────────────────
class _BottomOverlay extends StatelessWidget {
  const _BottomOverlay({required this.state, required this.pulseCtrl});
  final WorkoutState state;
  final AnimationController pulseCtrl;

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      top: false,
      child: Padding(
        padding: const EdgeInsets.fromLTRB(20, 0, 20, 20),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: double.infinity,
              padding: const EdgeInsets.symmetric(
                  horizontal: 16, vertical: 10),
              decoration: BoxDecoration(
                color: Colors.black54,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(
                    color: AppColors.primary.withValues(alpha: 0.4)),
              ),
              child: Row(
                children: [
                  AnimatedBuilder(
                    animation: pulseCtrl,
                    builder: (_, __) => Container(
                      width: 8,
                      height: 8,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        color: AppColors.primary.withValues(
                            alpha: 0.4 + 0.6 * pulseCtrl.value),
                      ),
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Text(
                      state.feedbackMessage,
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 14,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),
            Row(
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        crossAxisAlignment: CrossAxisAlignment.baseline,
                        textBaseline: TextBaseline.alphabetic,
                        children: [
                          Text(
                            '${state.currentReps}',
                            style: const TextStyle(
                              color: Colors.white,
                              fontSize: 72,
                              fontWeight: FontWeight.w900,
                              height: 1,
                            ),
                          ),
                          const SizedBox(width: 6),
                          Text(
                            '/ ${state.targetReps}',
                            style: const TextStyle(
                              color: Colors.white54,
                              fontSize: 24,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 4),
                      ClipRRect(
                        borderRadius: BorderRadius.circular(4),
                        child: LinearProgressIndicator(
                          value: state.progress,
                          backgroundColor: Colors.white12,
                          valueColor: const AlwaysStoppedAnimation(
                              AppColors.primary),
                          minHeight: 6,
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(width: 16),
                Column(
                  children: [
                    _ScoreChip(
                      label: '✓ ${state.correctReps}',
                      color: AppColors.success,
                    ),
                    const SizedBox(height: 6),
                    _ScoreChip(
                      label: '✗ ${state.incorrectReps}',
                      color: AppColors.error,
                    ),
                  ],
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _ScoreChip extends StatelessWidget {
  const _ScoreChip({required this.label, required this.color});
  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.2),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: color.withValues(alpha: 0.4)),
      ),
      child: Text(
        label,
        style: TextStyle(
          color: color,
          fontWeight: FontWeight.w700,
          fontSize: 14,
        ),
      ),
    );
  }
}
