import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/constants/route_constants.dart';
import '../../../core/i18n/locale_provider.dart';
import '../../../core/theme/app_colors.dart';
import '../../../data/mock_data.dart';
import '../../../models/exercise_model.dart';

final _selectedExerciseIdProvider = StateProvider<String>((ref) => 'squat');
final _targetRepsProvider = StateProvider<int>((ref) => 15);
final _targetSetsProvider = StateProvider<int>((ref) => 3);

class ExerciseSelectionScreen extends ConsumerWidget {
  const ExerciseSelectionScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final s = ref.watch(appStringsProvider);
    final selectedId = ref.watch(_selectedExerciseIdProvider);
    final selectedEx = mockExercises.firstWhere((e) => e.id == selectedId);
    final targetReps = ref.watch(_targetRepsProvider);
    final targetSets = ref.watch(_targetSetsProvider);
    final theme = Theme.of(context);

    return Scaffold(
      appBar: AppBar(
        title: Text(s.selectExercise),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_ios_rounded),
          onPressed: () => context.pop(),
        ),
      ),
      body: Column(
        children: [
          Expanded(
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(20),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    s.chooseExercise,
                    style: theme.textTheme.titleLarge
                        ?.copyWith(fontWeight: FontWeight.w700),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    s.aiTrackForm,
                    style: theme.textTheme.bodyMedium?.copyWith(
                      color: theme.colorScheme.onSurface.withValues(alpha: 0.5),
                    ),
                  ),
                  const SizedBox(height: 20),
                  GridView.builder(
                    shrinkWrap: true,
                    physics: const NeverScrollableScrollPhysics(),
                    gridDelegate:
                        const SliverGridDelegateWithFixedCrossAxisCount(
                      crossAxisCount: 2,
                      crossAxisSpacing: 12,
                      mainAxisSpacing: 12,
                      childAspectRatio: 1.1,
                    ),
                    itemCount: mockExercises.length,
                    itemBuilder: (ctx, i) {
                      final ex = mockExercises[i];
                      final isSelected = ex.id == selectedId;
                      return _ExerciseCard(
                        exercise: ex,
                        isSelected: isSelected,
                        strings: s,
                        onTap: () {
                          ref.read(_selectedExerciseIdProvider.notifier).state =
                              ex.id;
                          ref.read(_targetRepsProvider.notifier).state =
                              ex.defaultReps == 0
                                  ? ex.defaultDurationSeconds
                                  : ex.defaultReps;
                          ref.read(_targetSetsProvider.notifier).state =
                              ex.defaultSets;
                        },
                      );
                    },
                  ),
                  const SizedBox(height: 28),
                  _ConfigPanel(
                    exercise: selectedEx,
                    targetReps: targetReps,
                    targetSets: targetSets,
                    strings: s,
                    onRepsChanged: (v) =>
                        ref.read(_targetRepsProvider.notifier).state = v,
                    onSetsChanged: (v) =>
                        ref.read(_targetSetsProvider.notifier).state = v,
                  ),
                ],
              ),
            ),
          ),
          _BottomCTA(
            exercise: selectedEx,
            reps: targetReps,
            sets: targetSets,
            strings: s,
            onStart: () {
              context.push(
                RouteConstants.nativePoseWorkout,
                extra: {
                  'exerciseId': selectedEx.id,
                  'targetReps': targetReps,
                  'targetSets': targetSets,
                },
              );
            },
          ),
        ],
      ),
    );
  }
}

// ── Exercise Card ──────────────────────────────────────────────────────────
class _ExerciseCard extends StatelessWidget {
  const _ExerciseCard({
    required this.exercise,
    required this.isSelected,
    required this.strings,
    required this.onTap,
  });
  final ExerciseModel exercise;
  final bool isSelected;
  final dynamic strings;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;
    final s = strings;
    final localDiffLabel = exercise.difficultyLabel == 'Beginner'
        ? s.beginner
        : exercise.difficultyLabel == 'Intermediate'
            ? s.intermediate
            : s.advanced;

    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: isSelected
              ? exercise.accentColor.withValues(alpha: 0.12)
              : (isDark ? AppColors.darkCard : AppColors.lightCard),
          borderRadius: BorderRadius.circular(16),
          border: Border.all(
            color: isSelected ? exercise.accentColor : Colors.transparent,
            width: 2,
          ),
          boxShadow: isSelected
              ? [
                  BoxShadow(
                    color: exercise.accentColor.withValues(alpha: 0.2),
                    blurRadius: 12,
                    offset: const Offset(0, 4),
                  )
                ]
              : null,
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: exercise.accentColor.withValues(alpha: 0.15),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Image.asset(exercise.imagePath, width: 22, height: 22),
                ),
                const Spacer(),
                if (isSelected)
                  Icon(Icons.check_circle_rounded,
                      color: exercise.accentColor, size: 20),
              ],
            ),
            const Spacer(),
            Text(
              s.locale == 'ko' ? exercise.nameKr : exercise.name,
              style: theme.textTheme.titleSmall
                  ?.copyWith(fontWeight: FontWeight.w700),
            ),
            const SizedBox(height: 2),
            Text(
              localDiffLabel,
              style: TextStyle(
                color: exercise.accentColor,
                fontSize: 11,
                fontWeight: FontWeight.w500,
              ),
            ),
            const SizedBox(height: 4),
            Row(
              children: [
                ...exercise.targetMuscles.take(2).map(
                      (m) => Container(
                        margin: const EdgeInsets.only(right: 4),
                        padding: const EdgeInsets.symmetric(
                            horizontal: 6, vertical: 2),
                        decoration: BoxDecoration(
                          color: exercise.accentColor.withValues(alpha: 0.1),
                          borderRadius: BorderRadius.circular(4),
                        ),
                        child: Text(
                          m,
                          style: TextStyle(
                            color: exercise.accentColor,
                            fontSize: 9,
                            fontWeight: FontWeight.w500,
                          ),
                        ),
                      ),
                    ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

// ── Config Panel ───────────────────────────────────────────────────────────
class _ConfigPanel extends StatelessWidget {
  const _ConfigPanel({
    required this.exercise,
    required this.targetReps,
    required this.targetSets,
    required this.strings,
    required this.onRepsChanged,
    required this.onSetsChanged,
  });
  final ExerciseModel exercise;
  final int targetReps;
  final int targetSets;
  final dynamic strings;
  final ValueChanged<int> onRepsChanged;
  final ValueChanged<int> onSetsChanged;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;
    final s = strings;

    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: isDark ? AppColors.darkCard : AppColors.lightCard,
        borderRadius: BorderRadius.circular(16),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            s.configureWorkout,
            style: theme.textTheme.titleSmall
                ?.copyWith(fontWeight: FontWeight.w700),
          ),
          const SizedBox(height: 16),
          if (exercise.type == ExerciseType.reps)
            _StepControl(
              label: s.repsPerSet,
              value: targetReps,
              min: 5,
              max: 50,
              step: 1,
              onChanged: onRepsChanged,
            ),
          if (exercise.type == ExerciseType.duration)
            _StepControl(
              label: s.durationSeconds,
              value: targetReps == 0
                  ? exercise.defaultDurationSeconds
                  : targetReps,
              min: 10,
              max: 300,
              step: 10,
              onChanged: onRepsChanged,
            ),
          const SizedBox(height: 12),
          _StepControl(
            label: s.sets,
            value: targetSets,
            min: 1,
            max: 10,
            step: 1,
            onChanged: onSetsChanged,
          ),
        ],
      ),
    );
  }
}

class _StepControl extends StatelessWidget {
  const _StepControl({
    required this.label,
    required this.value,
    required this.min,
    required this.max,
    required this.step,
    required this.onChanged,
  });
  final String label;
  final int value;
  final int min;
  final int max;
  final int step;
  final ValueChanged<int> onChanged;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Row(
      children: [
        Expanded(child: Text(label, style: theme.textTheme.bodyMedium)),
        Row(
          children: [
            _CircleButton(
              icon: Icons.remove,
              onTap: value > min ? () => onChanged(value - step) : null,
            ),
            const SizedBox(width: 12),
            SizedBox(
              width: 36,
              child: Text(
                '$value',
                textAlign: TextAlign.center,
                style: theme.textTheme.titleMedium
                    ?.copyWith(fontWeight: FontWeight.w700),
              ),
            ),
            const SizedBox(width: 12),
            _CircleButton(
              icon: Icons.add,
              onTap: value < max ? () => onChanged(value + step) : null,
            ),
          ],
        ),
      ],
    );
  }
}

class _CircleButton extends StatelessWidget {
  const _CircleButton({required this.icon, required this.onTap});
  final IconData icon;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final enabled = onTap != null;
    return GestureDetector(
      onTap: onTap,
      child: Container(
        width: 32,
        height: 32,
        decoration: BoxDecoration(
          color: enabled
              ? AppColors.primary.withValues(alpha: 0.12)
              : Colors.grey.withValues(alpha: 0.08),
          shape: BoxShape.circle,
        ),
        child: Icon(
          icon,
          size: 16,
          color: enabled ? AppColors.primary : Colors.grey,
        ),
      ),
    );
  }
}

// ── Bottom CTA ─────────────────────────────────────────────────────────────
class _BottomCTA extends StatelessWidget {
  const _BottomCTA({
    required this.exercise,
    required this.reps,
    required this.sets,
    required this.strings,
    required this.onStart,
  });
  final ExerciseModel exercise;
  final int reps;
  final int sets;
  final dynamic strings;
  final VoidCallback onStart;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;
    final s = strings;
    final exName = s.locale == 'ko' ? exercise.nameKr : exercise.name;
    final startLabel = s.locale == 'ko'
        ? '$exName $reps * $sets 시작'
        : 'Start $exName $reps × $sets';

    return Container(
      padding: const EdgeInsets.fromLTRB(20, 16, 20, 32),
      decoration: BoxDecoration(
        color: isDark ? AppColors.darkSurface : AppColors.lightSurface,
        border: Border(
          top: BorderSide(
            color: isDark ? AppColors.darkDivider : AppColors.lightDivider,
          ),
        ),
      ),
      child: SafeArea(
        top: false,
        child: ElevatedButton(
          onPressed: onStart,
          style: ElevatedButton.styleFrom(
            backgroundColor: AppColors.primary,
            minimumSize: const Size(double.infinity, 54),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(14),
            ),
          ),
          child: Text(startLabel),
        ),
      ),
    );
  }
}
