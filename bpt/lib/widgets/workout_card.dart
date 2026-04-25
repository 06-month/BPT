import 'package:flutter/material.dart';

import '../core/theme/app_colors.dart';
import '../models/workout_record_model.dart';

class WorkoutCard extends StatelessWidget {
  const WorkoutCard({
    super.key,
    required this.record,
    this.onTap,
    this.compact = false,
  });

  final WorkoutRecordModel record;
  final VoidCallback? onTap;
  final bool compact;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;
    final score = record.postureScore;

    final scoreColor = score >= 90
        ? AppColors.scoreExcellent
        : score >= 75
            ? AppColors.scoreGood
            : score >= 60
                ? AppColors.scoreFair
                : AppColors.scorePoor;

    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: EdgeInsets.all(compact ? 12 : 16),
        decoration: BoxDecoration(
          color: isDark ? AppColors.darkCard : AppColors.lightCard,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(
            color: scoreColor.withValues(alpha: 0.15),
            width: 1,
          ),
        ),
        child: compact
            ? _compactLayout(theme, score, scoreColor)
            : _fullLayout(theme, score, scoreColor),
      ),
    );
  }

  Widget _fullLayout(ThemeData theme, double score, Color scoreColor) {
    return Row(
      children: [
        Container(
          width: 48,
          height: 48,
          decoration: BoxDecoration(
            color: AppColors.primary.withValues(alpha: 0.1),
            borderRadius: BorderRadius.circular(12),
          ),
          child: const Icon(Icons.fitness_center_rounded,
              color: AppColors.primary, size: 22),
        ),
        const SizedBox(width: 14),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                record.exerciseName,
                style: theme.textTheme.bodyMedium
                    ?.copyWith(fontWeight: FontWeight.w700),
              ),
              const SizedBox(height: 3),
              Text(
                record.totalReps > 0
                    ? '${record.totalReps} reps  •  ${record.durationFormatted}'
                    : record.durationFormatted,
                style: theme.textTheme.bodySmall?.copyWith(
                  color: theme.colorScheme.onSurface.withValues(alpha: 0.5),
                ),
              ),
              const SizedBox(height: 6),
              _AccuracyBar(accuracy: record.accuracy / 100.0),
            ],
          ),
        ),
        const SizedBox(width: 12),
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
              'Score',
              style: theme.textTheme.labelSmall?.copyWith(
                color: theme.colorScheme.onSurface.withValues(alpha: 0.4),
              ),
            ),
          ],
        ),
      ],
    );
  }

  Widget _compactLayout(ThemeData theme, double score, Color scoreColor) {
    return Row(
      children: [
        Expanded(
          child: Text(
            record.exerciseName,
            style:
                theme.textTheme.bodySmall?.copyWith(fontWeight: FontWeight.w600),
          ),
        ),
        Text(
          '${score.toInt()}%',
          style: TextStyle(
            color: scoreColor,
            fontWeight: FontWeight.w700,
            fontSize: 13,
          ),
        ),
      ],
    );
  }
}

class _AccuracyBar extends StatelessWidget {
  const _AccuracyBar({required this.accuracy});
  final double accuracy;

  @override
  Widget build(BuildContext context) {
    return ClipRRect(
      borderRadius: BorderRadius.circular(3),
      child: LinearProgressIndicator(
        value: accuracy,
        backgroundColor: AppColors.success.withValues(alpha: 0.12),
        valueColor: const AlwaysStoppedAnimation(AppColors.success),
        minHeight: 4,
      ),
    );
  }
}
