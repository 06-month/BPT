import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/constants/route_constants.dart';
import '../../../core/i18n/locale_provider.dart';
import '../../../core/theme/app_colors.dart';
import '../../../data/mock_data.dart';
import '../../../models/exercise_model.dart';
import '../../../models/workout_record_model.dart';
import '../../../features/workout/providers/workout_provider.dart';
import '../providers/home_provider.dart';

// ── File-level state for home exercise picker ──────────────────────────────
final _selectedExIdProvider =
    StateProvider<String>((ref) => mockExercises.first.id);
final _homeRepsProvider = StateProvider<int>(
    (ref) => mockExercises.first.defaultReps == 0
        ? mockExercises.first.defaultDurationSeconds
        : mockExercises.first.defaultReps);
final _homeSetsProvider =
    StateProvider<int>((ref) => mockExercises.first.defaultSets);

class HomeScreen extends ConsumerWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final s = ref.watch(appStringsProvider);
    final user = ref.watch(currentUserProvider);
    final summary = ref.watch(todaySummaryProvider);
    final recent = ref.watch(recentRecordsProvider);

    return Scaffold(
      body: CustomScrollView(
        slivers: [
          _BPTAppBar(name: user.name, strings: s),
          SliverPadding(
            padding: const EdgeInsets.fromLTRB(20, 0, 20, 120),
            sliver: SliverList(
              delegate: SliverChildListDelegate([
                if ((summary['streak'] as int) >= 2)
                  _StreakBanner(
                      streak: summary['streak'] as int, strings: s),
                const SizedBox(height: 20),
                _TodaySummaryCard(summary: summary, strings: s),
                const SizedBox(height: 28),
                _SectionHeader(title: s.myGoal),
                const SizedBox(height: 12),
                _WeeklyGoalCard(strings: s),
                const SizedBox(height: 28),
                _SectionHeader(
                  title: s.recentWorkouts,
                  trailing: s.seeAll,
                  onTrailingTap: () => context.go(RouteConstants.report),
                ),
                const SizedBox(height: 12),
                ...recent.map(
                    (r) => _RecentWorkoutTile(record: r, strings: s)),
                const SizedBox(height: 28),
                _SectionHeader(title: s.selectExercise),
                const SizedBox(height: 12),
                _ExercisePickerGrid(strings: s),
                const SizedBox(height: 16),
                _WorkoutConfigPanel(strings: s),
              ]),
            ),
          ),
        ],
      ),
      bottomSheet: _StartButton(strings: s),
    );
  }
}

// ── App Bar ────────────────────────────────────────────────────────────────
class _BPTAppBar extends StatelessWidget {
  const _BPTAppBar({required this.name, required this.strings});
  final String name;
  final dynamic strings;

  String _greeting(dynamic s) {
    final h = DateTime.now().hour;
    if (h < 12) return s.greetingMorning;
    if (h < 17) return s.greetingAfternoon;
    return s.greetingEvening;
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return SliverAppBar(
      floating: true,
      snap: true,
      backgroundColor: theme.scaffoldBackgroundColor,
      surfaceTintColor: Colors.transparent,
      elevation: 0,
      expandedHeight: 84,
      flexibleSpace: FlexibleSpaceBar(
        background: SafeArea(
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 20),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.center,
              children: [
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Text(
                      _greeting(strings),
                      style: theme.textTheme.bodyMedium?.copyWith(
                        color: theme.colorScheme.onSurface
                            .withValues(alpha: 0.55),
                      ),
                    ),
                    Text(
                      name.split(' ').first,
                      style: theme.textTheme.headlineSmall?.copyWith(
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                  ],
                ),
                const Spacer(),
                Container(
                  width: 48,
                  height: 48,
                  decoration: const BoxDecoration(
                    gradient: AppColors.primaryGradient,
                    shape: BoxShape.circle,
                  ),
                  child: const Icon(Icons.fitness_center_rounded,
                      color: Colors.white, size: 24),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

// ── Today Summary Card ─────────────────────────────────────────────────────
class _TodaySummaryCard extends StatelessWidget {
  const _TodaySummaryCard(
      {required this.summary, required this.strings});
  final Map<String, dynamic> summary;
  final dynamic strings;

  @override
  Widget build(BuildContext context) {
    final s = strings;
    return Container(
      padding: const EdgeInsets.all(22),
      decoration: BoxDecoration(
        gradient: AppColors.primaryGradient,
        borderRadius: BorderRadius.circular(20),
        boxShadow: [
          BoxShadow(
            color: AppColors.primary.withValues(alpha: 0.3),
            blurRadius: 20,
            offset: const Offset(0, 8),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            s.todaySummary,
            style: const TextStyle(
              color: Colors.white70,
              fontSize: 14,
              fontWeight: FontWeight.w600,
            ),
          ),
          const SizedBox(height: 18),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              _StatItem(
                value: '${summary['workoutsToday']}',
                label: s.workouts,
                icon: Icons.fitness_center_rounded,
              ),
              _StatItem(
                value: '${summary['totalReps']}',
                label: s.totalReps,
                icon: Icons.loop_rounded,
              ),
              _StatItem(
                value: '${summary['totalMinutes']}m',
                label: s.activeTime,
                icon: Icons.timer_outlined,
              ),
              _StatItem(
                value:
                    '${summary['avgPostureScore'].toStringAsFixed(0)}%',
                label: s.avgScore,
                icon: Icons.star_outline_rounded,
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _StatItem extends StatelessWidget {
  const _StatItem({
    required this.value,
    required this.label,
    required this.icon,
  });
  final String value;
  final String label;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Icon(icon, color: Colors.white70, size: 24),
        const SizedBox(height: 6),
        Text(
          value,
          style: const TextStyle(
            color: Colors.white,
            fontSize: 22,
            fontWeight: FontWeight.w800,
          ),
        ),
        const SizedBox(height: 2),
        Text(label,
            style: const TextStyle(
                color: Colors.white60,
                fontSize: 12,
                fontWeight: FontWeight.w500)),
      ],
    );
  }
}

// ── Streak Banner (맨 위, streak >= 2일 때만) ────────────────────────────────
class _StreakBanner extends StatelessWidget {
  const _StreakBanner({required this.streak, required this.strings});
  final int streak;
  final dynamic strings;

  @override
  Widget build(BuildContext context) {
    final s = strings;
    return Container(
      margin: const EdgeInsets.only(bottom: 4),
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 11),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          colors: [Color(0xFFFF6B35), Color(0xFFFF9500)],
        ),
        borderRadius: BorderRadius.circular(14),
      ),
      child: Row(
        children: [
          const Icon(Icons.local_fire_department_rounded,
              color: Colors.white, size: 20),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              s.locale == 'ko'
                  ? '$streak일 연속 운동 중! 잘 하고 있어요'
                  : '$streak-day streak! Keep it up!',
              style: const TextStyle(
                color: Colors.white,
                fontWeight: FontWeight.w700,
                fontSize: 14,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

// ── Weekly Goal Card ───────────────────────────────────────────────────────
class _WeeklyGoalCard extends ConsumerWidget {
  const _WeeklyGoalCard({required this.strings});
  final dynamic strings;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;
    final s = strings;
    final goal = ref.watch(weeklyWorkoutGoalProvider);
    final current = ref.watch(weeklyWorkoutsProvider);
    final progress = (current / goal).clamp(0.0, 1.0);

    final color = progress >= 1.0
        ? AppColors.scoreExcellent
        : progress >= 0.5
            ? AppColors.scoreGood
            : AppColors.primary;

    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: isDark ? AppColors.darkCard : AppColors.lightCard,
        borderRadius: BorderRadius.circular(16),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: color.withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: Icon(Icons.flag_rounded, color: color, size: 20),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      s.locale == 'ko' ? '주간 운동 목표' : 'Weekly Workout Goal',
                      style: theme.textTheme.titleSmall
                          ?.copyWith(fontWeight: FontWeight.w700),
                    ),
                    Text(
                      s.locale == 'ko'
                          ? '이번 주 $current / $goal 회'
                          : '$current / $goal this week',
                      style: theme.textTheme.bodySmall?.copyWith(
                        color: theme.colorScheme.onSurface
                            .withValues(alpha: 0.5),
                      ),
                    ),
                  ],
                ),
              ),
              Row(
                children: [
                  _CircleBtn(
                    icon: Icons.remove,
                    onTap: goal > 1
                        ? () => ref
                            .read(weeklyWorkoutGoalProvider.notifier)
                            .state = goal - 1
                        : null,
                  ),
                  const SizedBox(width: 10),
                  SizedBox(
                    width: 32,
                    child: Text(
                      '$goal',
                      textAlign: TextAlign.center,
                      style: theme.textTheme.titleMedium
                          ?.copyWith(fontWeight: FontWeight.w800),
                    ),
                  ),
                  const SizedBox(width: 10),
                  _CircleBtn(
                    icon: Icons.add,
                    onTap: goal < 14
                        ? () => ref
                            .read(weeklyWorkoutGoalProvider.notifier)
                            .state = goal + 1
                        : null,
                  ),
                ],
              ),
            ],
          ),
          const SizedBox(height: 14),
          Row(
            children: [
              Expanded(
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(6),
                  child: LinearProgressIndicator(
                    value: progress,
                    backgroundColor: color.withValues(alpha: 0.12),
                    valueColor: AlwaysStoppedAnimation<Color>(color),
                    minHeight: 8,
                  ),
                ),
              ),
              const SizedBox(width: 10),
              Text(
                '${(progress * 100).toInt()}%',
                style: TextStyle(
                  color: color,
                  fontWeight: FontWeight.w800,
                  fontSize: 13,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

// ── Section Header ─────────────────────────────────────────────────────────
class _SectionHeader extends StatelessWidget {
  const _SectionHeader({
    required this.title,
    this.trailing,
    this.onTrailingTap,
  });
  final String title;
  final String? trailing;
  final VoidCallback? onTrailingTap;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(
          title,
          style: theme.textTheme.titleMedium?.copyWith(
            fontWeight: FontWeight.w700,
          ),
        ),
        if (trailing != null)
          GestureDetector(
            onTap: onTrailingTap,
            child: Text(
              trailing!,
              style: const TextStyle(
                color: AppColors.primary,
                fontWeight: FontWeight.w600,
                fontSize: 14,
              ),
            ),
          ),
      ],
    );
  }
}

// ── Recent Workout Tile ────────────────────────────────────────────────────
class _RecentWorkoutTile extends StatelessWidget {
  const _RecentWorkoutTile(
      {required this.record, required this.strings});
  final WorkoutRecordModel record;
  final dynamic strings;

  String _timeAgo(DateTime date, dynamic s) {
    final diff = DateTime.now().difference(date);
    if (diff.inDays == 0) return s.today;
    if (diff.inDays == 1) return s.yesterday;
    return '${diff.inDays}${s.daysAgo}';
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;
    final score = record.postureScore;
    final s = strings;

    final scoreColor = score >= 90
        ? AppColors.scoreExcellent
        : score >= 75
            ? AppColors.scoreGood
            : score >= 60
                ? AppColors.scoreFair
                : AppColors.scorePoor;

    final ex = findExercise(record.exerciseId);

    return GestureDetector(
      onTap: () => context.push(
        RouteConstants.workoutResult,
        extra: {
          'exerciseId': record.exerciseId,
          'exerciseName': record.exerciseName,
          'exerciseNameKr': ex.nameKr,
          'totalReps': record.totalReps,
          'correctReps': record.correctReps,
          'incorrectReps': record.incorrectReps,
          'elapsedSeconds': record.durationSeconds,
          'postureScore': record.postureScore,
          'feedbackHistory': record.feedbackNotes,
          'targetSets': 0,
          'isHistory': true,
          'date': record.date,
        },
      ),
      child: Container(
        margin: const EdgeInsets.only(bottom: 10),
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: isDark ? AppColors.darkCard : AppColors.lightCard,
          borderRadius: BorderRadius.circular(14),
        ),
        child: Row(
          children: [
            Container(
              width: 50,
              height: 50,
              decoration: BoxDecoration(
                color: ex.accentColor.withValues(alpha: 0.12),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Padding(
                padding: const EdgeInsets.all(10),
                child: Image.asset(ex.imagePath),
              ),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    s.locale == 'ko' ? ex.nameKr : record.exerciseName,
                    style: theme.textTheme.bodyMedium
                        ?.copyWith(fontWeight: FontWeight.w700),
                  ),
                  const SizedBox(height: 3),
                  Text(
                    record.totalReps > 0
                        ? '${record.totalReps} ${s.reps}  •  ${record.durationFormatted}'
                        : record.durationFormatted,
                    style: theme.textTheme.bodySmall?.copyWith(
                      color: theme.colorScheme.onSurface
                          .withValues(alpha: 0.55),
                    ),
                  ),
                ],
              ),
            ),
            Column(
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                Text(
                  '${score.toInt()}%',
                  style: TextStyle(
                    color: scoreColor,
                    fontWeight: FontWeight.w800,
                    fontSize: 16,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  _timeAgo(record.date, s),
                  style: theme.textTheme.bodySmall?.copyWith(
                    color: theme.colorScheme.onSurface
                        .withValues(alpha: 0.45),
                  ),
                ),
              ],
            ),
            const SizedBox(width: 4),
            Icon(Icons.chevron_right_rounded,
                color:
                    theme.colorScheme.onSurface.withValues(alpha: 0.3),
                size: 18),
          ],
        ),
      ),
    );
  }
}

// ── Exercise Picker Grid ───────────────────────────────────────────────────
class _ExercisePickerGrid extends ConsumerWidget {
  const _ExercisePickerGrid({required this.strings});
  final dynamic strings;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final s = strings;
    final selectedId = ref.watch(_selectedExIdProvider);

    return GridView.builder(
      shrinkWrap: true,
      padding: EdgeInsets.zero,
      physics: const NeverScrollableScrollPhysics(),
      gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
        crossAxisCount: 2,
        crossAxisSpacing: 12,
        mainAxisSpacing: 12,
        childAspectRatio: 1.35,
      ),
      itemCount: mockExercises.length,
      itemBuilder: (context, i) {
        final ex = mockExercises[i];
        final isSelected = ex.id == selectedId;
        final theme = Theme.of(context);
        final isDark = theme.brightness == Brightness.dark;
        final diffLabel = ex.difficultyLabel == 'Beginner'
            ? s.beginner
            : ex.difficultyLabel == 'Intermediate'
                ? s.intermediate
                : s.advanced;

        return GestureDetector(
          onTap: () {
            ref.read(_selectedExIdProvider.notifier).state = ex.id;
            ref.read(_homeRepsProvider.notifier).state =
                ex.defaultReps == 0
                    ? ex.defaultDurationSeconds
                    : ex.defaultReps;
            ref.read(_homeSetsProvider.notifier).state =
                ex.defaultSets;
          },
          child: AnimatedContainer(
            duration: const Duration(milliseconds: 200),
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: isSelected
                  ? ex.accentColor.withValues(alpha: 0.12)
                  : (isDark ? AppColors.darkCard : AppColors.lightCard),
              borderRadius: BorderRadius.circular(16),
              border: Border.all(
                color: isSelected
                    ? ex.accentColor
                    : Colors.transparent,
                width: 2,
              ),
              boxShadow: isSelected
                  ? [
                      BoxShadow(
                        color: ex.accentColor.withValues(alpha: 0.2),
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
                    Image.asset(ex.imagePath,
                        width: 30, height: 30),
                    const Spacer(),
                    if (isSelected)
                      Icon(Icons.check_circle_rounded,
                          color: ex.accentColor, size: 20),
                  ],
                ),
                const Spacer(),
                Text(
                  s.locale == 'ko' ? ex.nameKr : ex.name,
                  style: theme.textTheme.titleSmall?.copyWith(
                      fontWeight: FontWeight.w700),
                ),
                const SizedBox(height: 2),
                Text(
                  diffLabel,
                  style: TextStyle(
                    color: ex.accentColor,
                    fontSize: 12,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
          ),
        );
      },
    );
  }
}

// ── Workout Config Panel ───────────────────────────────────────────────────
class _WorkoutConfigPanel extends ConsumerWidget {
  const _WorkoutConfigPanel({required this.strings});
  final dynamic strings;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final s = strings;
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;
    final selectedId = ref.watch(_selectedExIdProvider);
    final reps = ref.watch(_homeRepsProvider);
    final sets = ref.watch(_homeSetsProvider);
    final ex =
        mockExercises.firstWhere((e) => e.id == selectedId);

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
          const SizedBox(height: 18),
          if (ex.type == ExerciseType.reps)
            _StepControl(
              label: s.repsPerSet,
              value: reps,
              min: 5,
              max: 50,
              step: 1,
              onChanged: (v) =>
                  ref.read(_homeRepsProvider.notifier).state = v,
            )
          else
            _StepControl(
              label: s.durationSeconds,
              value: reps,
              min: 10,
              max: 300,
              step: 10,
              onChanged: (v) =>
                  ref.read(_homeRepsProvider.notifier).state = v,
            ),
          const SizedBox(height: 14),
          _StepControl(
            label: s.sets,
            value: sets,
            min: 1,
            max: 10,
            step: 1,
            onChanged: (v) =>
                ref.read(_homeSetsProvider.notifier).state = v,
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
        Expanded(
            child: Text(label, style: theme.textTheme.bodyMedium)),
        Row(
          children: [
            _CircleBtn(
              icon: Icons.remove,
              onTap:
                  value > min ? () => onChanged(value - step) : null,
            ),
            const SizedBox(width: 14),
            SizedBox(
              width: 40,
              child: Text(
                '$value',
                textAlign: TextAlign.center,
                style: theme.textTheme.titleMedium
                    ?.copyWith(fontWeight: FontWeight.w800),
              ),
            ),
            const SizedBox(width: 14),
            _CircleBtn(
              icon: Icons.add,
              onTap:
                  value < max ? () => onChanged(value + step) : null,
            ),
          ],
        ),
      ],
    );
  }
}

class _CircleBtn extends StatelessWidget {
  const _CircleBtn({required this.icon, required this.onTap});
  final IconData icon;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final enabled = onTap != null;
    return GestureDetector(
      onTap: onTap,
      child: Container(
        width: 36,
        height: 36,
        decoration: BoxDecoration(
          color: enabled
              ? AppColors.primary.withValues(alpha: 0.12)
              : Colors.grey.withValues(alpha: 0.08),
          shape: BoxShape.circle,
        ),
        child: Icon(
          icon,
          size: 18,
          color: enabled ? AppColors.primary : Colors.grey,
        ),
      ),
    );
  }
}

// ── Start Button (bottom sheet) ────────────────────────────────────────────
class _StartButton extends ConsumerWidget {
  const _StartButton({required this.strings});
  final dynamic strings;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final s = strings;
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;
    final selectedId = ref.watch(_selectedExIdProvider);
    final reps = ref.watch(_homeRepsProvider);
    final sets = ref.watch(_homeSetsProvider);
    final ex =
        mockExercises.firstWhere((e) => e.id == selectedId);
    final exName = s.locale == 'ko' ? ex.nameKr : ex.name;
    final unit = ex.type == ExerciseType.duration ? 's' : ' ${s.reps}';

    return Container(
      padding: const EdgeInsets.fromLTRB(20, 14, 20, 0),
      decoration: BoxDecoration(
        color: isDark ? AppColors.darkSurface : AppColors.lightSurface,
        border: Border(
          top: BorderSide(
            color: isDark
                ? AppColors.darkDivider
                : AppColors.lightDivider,
          ),
        ),
      ),
      child: SafeArea(
        top: false,
        child: ElevatedButton.icon(
          onPressed: () {
            ref.read(workoutProvider.notifier).initialize(
                  selectedId,
                  reps,
                  sets,
                );
            context.push(RouteConstants.workout, extra: selectedId);
          },
          icon: const Icon(Icons.play_arrow_rounded, size: 26),
          label: Text(
              '${s.start} $exName  •  $sets × $reps$unit'),
          style: ElevatedButton.styleFrom(
            backgroundColor: ex.accentColor,
          ),
        ),
      ),
    );
  }
}
