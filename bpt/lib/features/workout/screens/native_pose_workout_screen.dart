import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/i18n/locale_provider.dart';
import '../../../core/theme/app_colors.dart';
import '../../../data/mock_data.dart';

/// Preparation phases shown before the native camera PlatformView appears.
enum _PrepPhase { alignHint, countdown, live }

class NativePoseWorkoutScreen extends ConsumerStatefulWidget {
  const NativePoseWorkoutScreen({
    super.key,
    required this.exerciseId,
    this.targetReps = 15,
    this.targetSets = 3,
  });

  static const String viewType = 'bpt/native_pose_camera';
  static const Set<String> supportedExerciseIds = {
    'deadlift',
    'benchpress',
    'squat',
    'barbell-row',
    'pushup',
  };

  final String exerciseId;
  final int targetReps;
  final int targetSets;

  @override
  ConsumerState<NativePoseWorkoutScreen> createState() =>
      _NativePoseWorkoutScreenState();
}

class _NativePoseWorkoutScreenState
    extends ConsumerState<NativePoseWorkoutScreen> {
  // "카메라를 몸 전체가 보이도록 맞춰주세요" guidance duration before the countdown.
  static const Duration _alignHintDuration = Duration(milliseconds: 1800);

  Timer? _alignTimer;
  Timer? _countdownTimer;
  MethodChannel? _channel;

  _PrepPhase _phase = _PrepPhase.alignHint;
  int _count = 3;

  // Rep/set tracking, driven by the native evaluator updates over the channel.
  int _currentSet = 1;
  int _setStartRep = 0; // native cumulative rep at the start of the current set
  int _latestNativeRep = 0; // most recent native cumulative rep
  bool _setComplete = false;
  bool _workoutComplete = false;

  bool get _isSupportedExercise =>
      NativePoseWorkoutScreen.supportedExerciseIds.contains(widget.exerciseId);
  bool get _isIOS => !kIsWeb && defaultTargetPlatform == TargetPlatform.iOS;

  int get _repsThisSet {
    final v = _latestNativeRep - _setStartRep;
    if (v < 0) return 0;
    if (v > widget.targetReps) return widget.targetReps;
    return v;
  }

  @override
  void initState() {
    super.initState();
    // Only run the prep/countdown flow when we will actually show the camera.
    if (_isSupportedExercise && _isIOS) {
      _alignTimer = Timer(_alignHintDuration, _startCountdown);
    }
  }

  void _startCountdown() {
    if (!mounted) return;
    setState(() {
      _phase = _PrepPhase.countdown;
      _count = 3;
    });
    _countdownTimer = Timer.periodic(const Duration(seconds: 1), (timer) {
      if (!mounted) {
        timer.cancel();
        return;
      }
      if (_count <= 1) {
        timer.cancel();
        setState(() => _phase = _PrepPhase.live);
      } else {
        setState(() => _count -= 1);
      }
    });
  }

  void _onPlatformViewCreated(int id) {
    _channel = MethodChannel('${NativePoseWorkoutScreen.viewType}/$id');
    _channel!.setMethodCallHandler(_handleNativeCall);
  }

  Future<dynamic> _handleNativeCall(MethodCall call) async {
    if (call.method == 'onPoseUpdate') {
      final args = (call.arguments as Map).cast<String, dynamic>();
      final rep = (args['rep'] as num?)?.toInt() ?? _latestNativeRep;
      _onNativeUpdate(rep);
    }
    return null;
  }

  void _onNativeUpdate(int rep) {
    if (!mounted) return;
    setState(() {
      _latestNativeRep = rep;
      // Don't advance set state while a set-complete / done prompt is showing;
      // reps performed during the rest period are discarded on "next set".
      if (_setComplete || _workoutComplete) return;
      if (rep - _setStartRep >= widget.targetReps) {
        if (_currentSet < widget.targetSets) {
          _setComplete = true;
        } else {
          _workoutComplete = true;
        }
      }
    });
  }

  void _startNextSet() {
    setState(() {
      _currentSet += 1;
      _setStartRep = _latestNativeRep; // snapshot: discard rest-period reps
      _setComplete = false;
    });
  }

  void _finishWorkout() {
    if (mounted) Navigator.of(context).maybePop();
  }

  @override
  void dispose() {
    _alignTimer?.cancel();
    _countdownTimer?.cancel();
    _channel?.setMethodCallHandler(null);
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final s = ref.watch(appStringsProvider);
    final isKo = s.locale == 'ko';
    final exercise = findExercise(widget.exerciseId);
    final exName = isKo ? exercise.nameKr : exercise.name;

    return Scaffold(
      backgroundColor: Colors.black,
      appBar: AppBar(
        title: const Text('실시간 AI 코칭'),
        backgroundColor: Colors.black,
        foregroundColor: Colors.white,
        elevation: 0,
      ),
      body: _buildBody(context, exName, isKo, s.set),
    );
  }

  Widget _buildBody(
    BuildContext context,
    String exerciseName,
    bool isKo,
    String setLabel,
  ) {
    if (!_isSupportedExercise) {
      return _MessageState(
        icon: Icons.error_outline_rounded,
        title: '지원하지 않는 운동입니다.',
        message: 'exerciseId: ${widget.exerciseId}',
      );
    }

    if (!_isIOS) {
      return const _MessageState(
        icon: Icons.phone_iphone_rounded,
        title: 'iOS 전용 기능',
        message: '실시간 AI 카메라 코칭은 현재 iOS에서만 사용할 수 있습니다.',
      );
    }

    // Don't create the native UiKitView until the countdown has completed.
    if (_phase != _PrepPhase.live) {
      return _PrepOverlay(
        phase: _phase,
        count: _count,
        exerciseName: exerciseName,
      );
    }

    return Stack(
      fit: StackFit.expand,
      children: [
        UiKitView(
          viewType: NativePoseWorkoutScreen.viewType,
          creationParams: {'exerciseId': widget.exerciseId},
          creationParamsCodec: const StandardMessageCodec(),
          onPlatformViewCreated: _onPlatformViewCreated,
        ),
        if (!_setComplete && !_workoutComplete)
          Positioned(
            left: 0,
            right: 0,
            bottom: 0,
            child: _BottomHud(
              reps: _repsThisSet,
              targetReps: widget.targetReps,
              currentSet: _currentSet,
              totalSets: widget.targetSets,
              setLabel: setLabel,
            ),
          ),
        if (_setComplete)
          _SetCompleteOverlay(
            completedSet: _currentSet,
            nextSet: _currentSet + 1,
            totalSets: widget.targetSets,
            isKo: isKo,
            onNext: _startNextSet,
          ),
        if (_workoutComplete)
          _WorkoutCompleteOverlay(
            totalSets: widget.targetSets,
            isKo: isKo,
            onFinish: _finishWorkout,
          ),
      ],
    );
  }
}

/// Full-screen preparation UI shown before the native camera appears.
class _PrepOverlay extends StatelessWidget {
  const _PrepOverlay({
    required this.phase,
    required this.count,
    required this.exerciseName,
  });

  final _PrepPhase phase;
  final int count;
  final String exerciseName;

  @override
  Widget build(BuildContext context) {
    final isCountdown = phase == _PrepPhase.countdown;

    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              exerciseName,
              style: const TextStyle(
                color: AppColors.primary,
                fontSize: 16,
                fontWeight: FontWeight.w700,
              ),
            ),
            const SizedBox(height: 28),
            if (isCountdown) ...[
              const Text(
                '준비하세요',
                style: TextStyle(
                  color: Colors.white,
                  fontSize: 20,
                  fontWeight: FontWeight.w700,
                ),
              ),
              const SizedBox(height: 28),
              Container(
                width: 128,
                height: 128,
                alignment: Alignment.center,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: AppColors.primary.withValues(alpha: 0.14),
                  border: Border.all(color: AppColors.primary, width: 3),
                ),
                child: Text(
                  '$count',
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 64,
                    fontWeight: FontWeight.w800,
                  ),
                ),
              ),
            ] else ...[
              const Icon(
                Icons.accessibility_new_rounded,
                color: AppColors.primary,
                size: 56,
              ),
              const SizedBox(height: 24),
              const Text(
                '카메라를 몸 전체가 보이도록 맞춰주세요',
                textAlign: TextAlign.center,
                style: TextStyle(
                  color: Colors.white,
                  fontSize: 19,
                  fontWeight: FontWeight.w800,
                  height: 1.4,
                ),
              ),
              const SizedBox(height: 24),
              const SizedBox(
                width: 26,
                height: 26,
                child: CircularProgressIndicator(
                  strokeWidth: 2.4,
                  valueColor:
                      AlwaysStoppedAnimation<Color>(AppColors.primary),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

/// Bottom HUD over the live camera: current rep / target reps for this set.
class _BottomHud extends StatelessWidget {
  const _BottomHud({
    required this.reps,
    required this.targetReps,
    required this.currentSet,
    required this.totalSets,
    required this.setLabel,
  });

  final int reps;
  final int targetReps;
  final int currentSet;
  final int totalSets;
  final String setLabel;

  @override
  Widget build(BuildContext context) {
    final progress =
        targetReps == 0 ? 0.0 : (reps / targetReps).clamp(0.0, 1.0).toDouble();

    return DecoratedBox(
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.bottomCenter,
          end: Alignment.topCenter,
          colors: [Colors.black87, Colors.transparent],
        ),
      ),
      child: SafeArea(
        top: false,
        child: Padding(
          padding: const EdgeInsets.fromLTRB(20, 28, 20, 20),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                decoration: BoxDecoration(
                  color: Colors.black54,
                  borderRadius: BorderRadius.circular(20),
                ),
                child: Text(
                  '$setLabel $currentSet / $totalSets',
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 12,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
              const SizedBox(height: 12),
              Row(
                crossAxisAlignment: CrossAxisAlignment.baseline,
                textBaseline: TextBaseline.alphabetic,
                children: [
                  Text(
                    '$reps',
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 72,
                      fontWeight: FontWeight.w900,
                      height: 1,
                    ),
                  ),
                  const SizedBox(width: 6),
                  Text(
                    '/ $targetReps',
                    style: const TextStyle(
                      color: Colors.white54,
                      fontSize: 24,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 6),
              ClipRRect(
                borderRadius: BorderRadius.circular(4),
                child: LinearProgressIndicator(
                  value: progress,
                  backgroundColor: Colors.white12,
                  valueColor:
                      const AlwaysStoppedAnimation(AppColors.primary),
                  minHeight: 6,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// Set-complete prompt asking the user to continue to the next set.
class _SetCompleteOverlay extends StatelessWidget {
  const _SetCompleteOverlay({
    required this.completedSet,
    required this.nextSet,
    required this.totalSets,
    required this.isKo,
    required this.onNext,
  });

  final int completedSet;
  final int nextSet;
  final int totalSets;
  final bool isKo;
  final VoidCallback onNext;

  String _ordinalKr(int n) {
    const names = ['', '첫번째', '두번째', '세번째', '네번째', '다섯번째'];
    if (n < names.length) return names[n];
    return '$n번째';
  }

  String _ordinalEn(int n) {
    if (n == 1) return '1st';
    if (n == 2) return '2nd';
    if (n == 3) return '3rd';
    return '${n}th';
  }

  @override
  Widget build(BuildContext context) {
    final completedLabel =
        isKo ? _ordinalKr(completedSet) : _ordinalEn(completedSet);
    final nextLabel = isKo ? _ordinalKr(nextSet) : _ordinalEn(nextSet);

    final title =
        isKo ? '$completedLabel 세트 완료!' : 'Set $completedSet Complete!';
    final subtitle = isKo
        ? '$nextLabel 세트를 시작하려면 아래 버튼을 눌러주세요'
        : 'Press the button below to start set $nextSet';
    final btnLabel = isKo ? '$nextLabel 세트 시작하기' : 'Start Set $nextSet';

    return Container(
      color: Colors.black87,
      child: Center(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 32),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Container(
                width: 80,
                height: 80,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: AppColors.primary.withValues(alpha: 0.15),
                  border: Border.all(color: AppColors.primary, width: 2.5),
                ),
                child: const Icon(Icons.check_rounded,
                    color: AppColors.primary, size: 40),
              ),
              const SizedBox(height: 28),
              Text(
                title,
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 28,
                  fontWeight: FontWeight.w900,
                ),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 12),
              Text(
                subtitle,
                style: TextStyle(
                  color: Colors.white.withValues(alpha: 0.65),
                  fontSize: 15,
                ),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 8),
              Text(
                isKo
                    ? '$completedSet / $totalSets 세트 완료'
                    : '$completedSet / $totalSets sets done',
                style: TextStyle(
                  color: AppColors.primary.withValues(alpha: 0.8),
                  fontSize: 13,
                  fontWeight: FontWeight.w600,
                ),
              ),
              const SizedBox(height: 40),
              SizedBox(
                width: double.infinity,
                child: ElevatedButton(
                  onPressed: onNext,
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppColors.primary,
                    foregroundColor: Colors.white,
                    padding: const EdgeInsets.symmetric(vertical: 16),
                    shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(16)),
                  ),
                  child: Text(
                    btnLabel,
                    style: const TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// Final overlay shown after the last set is finished.
class _WorkoutCompleteOverlay extends StatelessWidget {
  const _WorkoutCompleteOverlay({
    required this.totalSets,
    required this.isKo,
    required this.onFinish,
  });

  final int totalSets;
  final bool isKo;
  final VoidCallback onFinish;

  @override
  Widget build(BuildContext context) {
    final title = isKo ? '운동 완료!' : 'Workout Complete!';
    final subtitle = isKo
        ? '$totalSets 세트를 모두 마쳤어요. 수고하셨습니다!'
        : 'You finished all $totalSets sets. Great job!';
    final btnLabel = isKo ? '완료' : 'Finish';

    return Container(
      color: Colors.black87,
      child: Center(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 32),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Container(
                width: 80,
                height: 80,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: AppColors.primary.withValues(alpha: 0.15),
                  border: Border.all(color: AppColors.primary, width: 2.5),
                ),
                child: const Icon(Icons.emoji_events_rounded,
                    color: AppColors.primary, size: 40),
              ),
              const SizedBox(height: 28),
              Text(
                title,
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 28,
                  fontWeight: FontWeight.w900,
                ),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 12),
              Text(
                subtitle,
                style: TextStyle(
                  color: Colors.white.withValues(alpha: 0.65),
                  fontSize: 15,
                ),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 40),
              SizedBox(
                width: double.infinity,
                child: ElevatedButton(
                  onPressed: onFinish,
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppColors.primary,
                    foregroundColor: Colors.white,
                    padding: const EdgeInsets.symmetric(vertical: 16),
                    shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(16)),
                  ),
                  child: Text(
                    btnLabel,
                    style: const TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _MessageState extends StatelessWidget {
  const _MessageState({
    required this.icon,
    required this.title,
    required this.message,
  });

  final IconData icon;
  final String title;
  final String message;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(28),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 46, color: AppColors.primary),
            const SizedBox(height: 16),
            Text(
              title,
              textAlign: TextAlign.center,
              style: const TextStyle(
                color: Colors.white,
                fontSize: 18,
                fontWeight: FontWeight.w800,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              message,
              textAlign: TextAlign.center,
              style: TextStyle(
                color: Colors.white.withValues(alpha: 0.72),
                fontSize: 14,
                height: 1.4,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
