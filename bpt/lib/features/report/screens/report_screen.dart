import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/constants/route_constants.dart';
import '../../../core/i18n/locale_provider.dart';
import '../../../core/theme/app_colors.dart';
import '../../../data/mock_data.dart';
import '../providers/report_provider.dart';

class ReportScreen extends ConsumerWidget {
  const ReportScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final s = ref.watch(appStringsProvider);
    final tab = ref.watch(reportTabProvider);
    final data = ref.watch(reportDataProvider);

    return Scaffold(
      appBar: AppBar(title: Text(s.report)),
      body: Column(
        children: [
          _TabSelector(current: tab, strings: s,
              onChanged: (t) =>
                  ref.read(reportTabProvider.notifier).state = t),
          Expanded(
            child: SingleChildScrollView(
              padding: const EdgeInsets.fromLTRB(20, 16, 20, 100),
              child: Column(
                children: [
                  _SummaryRow(data: data, strings: s),
                  const SizedBox(height: 24),
                  _ChartCard(
                    title: s.postureScoreChart,
                    subtitle: s.postureScoreSubtitle,
                    chart: _PostureLineChart(
                      scores: (data['postureScores'] as List).cast<double>(),
                      labels: (data['labels'] as List).cast<String>(),
                    ),
                  ),
                  const SizedBox(height: 16),
                  _ChartCard(
                    title: s.repVolume,
                    subtitle: s.repVolumeSubtitle,
                    chart: _RepsBarChart(
                      reps: (data['reps'] as List).cast<double>(),
                      labels: (data['labels'] as List).cast<String>(),
                    ),
                  ),
                  const SizedBox(height: 16),
                  _ChartCard(
                    title: s.activeTimeChart,
                    subtitle: s.activeTimeSubtitle,
                    chart: _WorkoutTimeLineChart(
                      minutes:
                          (data['workoutMinutes'] as List).cast<double>(),
                      labels: (data['labels'] as List).cast<String>(),
                    ),
                  ),
                  const SizedBox(height: 24),
                  _RecentRecordsSection(strings: s),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

// ── Tab Selector ───────────────────────────────────────────────────────────
class _TabSelector extends StatelessWidget {
  const _TabSelector(
      {required this.current,
      required this.onChanged,
      required this.strings});
  final ReportTab current;
  final ValueChanged<ReportTab> onChanged;
  final dynamic strings;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;
    final s = strings;
    final labels = [s.daily, s.weekly, s.monthly];

    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
      padding: const EdgeInsets.all(4),
      decoration: BoxDecoration(
        color: isDark ? AppColors.darkCard : AppColors.lightInputFill,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        children: ReportTab.values.asMap().entries.map((entry) {
          final t = entry.value;
          final selected = t == current;
          return Expanded(
            child: GestureDetector(
              onTap: () => onChanged(t),
              child: AnimatedContainer(
                duration: const Duration(milliseconds: 200),
                padding: const EdgeInsets.symmetric(vertical: 8),
                decoration: BoxDecoration(
                  color: selected ? AppColors.primary : Colors.transparent,
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Text(
                  labels[entry.key],
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    color: selected
                        ? Colors.white
                        : theme.colorScheme.onSurface.withValues(alpha: 0.5),
                    fontWeight: selected ? FontWeight.w700 : FontWeight.w400,
                    fontSize: 13,
                  ),
                ),
              ),
            ),
          );
        }).toList(),
      ),
    );
  }
}

// ── Summary Row ────────────────────────────────────────────────────────────
class _SummaryRow extends StatelessWidget {
  const _SummaryRow({required this.data, required this.strings});
  final Map<String, dynamic> data;
  final dynamic strings;

  @override
  Widget build(BuildContext context) {
    final s = strings;
    final avg = data['avgScore'] as double;
    final achievement = data['avgAchievement'] as double? ?? 0.0;
    return Column(
      children: [
        Row(
          children: [
            Expanded(
                child: _SummaryCard(
                    label: s.workouts,
                    value: '${data['totalWorkouts']}',
                    icon: Icons.fitness_center_rounded,
                    color: AppColors.primary)),
            const SizedBox(width: 10),
            Expanded(
                child: _SummaryCard(
                    label: s.totalReps,
                    value: '${data['totalReps']}',
                    icon: Icons.loop_rounded,
                    color: AppColors.secondary)),
            const SizedBox(width: 10),
            Expanded(
                child: _SummaryCard(
                    label: s.avgScore,
                    value: '${avg.toStringAsFixed(1)}%',
                    icon: Icons.star_rounded,
                    color: AppColors.warning)),
            const SizedBox(width: 10),
            Expanded(
                child: _SummaryCard(
                    label: s.minutes,
                    value: '${data['totalMinutes']}',
                    icon: Icons.timer_outlined,
                    color: AppColors.info)),
          ],
        ),
        const SizedBox(height: 12),
        _AchievementSummaryBar(achievement: achievement, strings: s),
      ],
    );
  }
}

class _SummaryCard extends StatelessWidget {
  const _SummaryCard({
    required this.label,
    required this.value,
    required this.icon,
    required this.color,
  });
  final String label;
  final String value;
  final IconData icon;
  final Color color;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 6),
      decoration: BoxDecoration(
        color: isDark ? AppColors.darkCard : AppColors.lightCard,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        children: [
          Icon(icon, color: color, size: 18),
          const SizedBox(height: 5),
          Text(value,
              style: TextStyle(
                  color: color,
                  fontWeight: FontWeight.w800,
                  fontSize: 14)),
          const SizedBox(height: 2),
          Text(
            label,
            style: theme.textTheme.labelSmall?.copyWith(
              fontSize: 9,
              color: theme.colorScheme.onSurface.withValues(alpha: 0.45),
            ),
            textAlign: TextAlign.center,
          ),
        ],
      ),
    );
  }
}

// ── Achievement Summary Bar ────────────────────────────────────────────────
class _AchievementSummaryBar extends StatelessWidget {
  const _AchievementSummaryBar(
      {required this.achievement, required this.strings});
  final double achievement;
  final dynamic strings;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;
    final s = strings;
    final color = achievement >= 90
        ? AppColors.scoreExcellent
        : achievement >= 75
            ? AppColors.scoreGood
            : AppColors.scoreFair;

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      decoration: BoxDecoration(
        color: isDark ? AppColors.darkCard : AppColors.lightCard,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        children: [
          Icon(Icons.flag_rounded, color: color, size: 16),
          const SizedBox(width: 8),
          Text(
            s.locale == 'ko' ? '평균 목표 달성률' : 'Avg Goal Achievement',
            style: theme.textTheme.bodySmall
                ?.copyWith(fontWeight: FontWeight.w600),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: ClipRRect(
              borderRadius: BorderRadius.circular(4),
              child: LinearProgressIndicator(
                value: achievement / 100,
                backgroundColor: color.withValues(alpha: 0.12),
                valueColor: AlwaysStoppedAnimation<Color>(color),
                minHeight: 7,
              ),
            ),
          ),
          const SizedBox(width: 10),
          Text(
            '${achievement.toInt()}%',
            style: TextStyle(
                color: color, fontWeight: FontWeight.w800, fontSize: 13),
          ),
        ],
      ),
    );
  }
}

// ── Chart Card ─────────────────────────────────────────────────────────────
class _ChartCard extends StatelessWidget {
  const _ChartCard(
      {required this.title,
      required this.subtitle,
      required this.chart});
  final String title;
  final String subtitle;
  final Widget chart;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: isDark ? AppColors.darkCard : AppColors.lightCard,
        borderRadius: BorderRadius.circular(16),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title,
              style: theme.textTheme.titleSmall
                  ?.copyWith(fontWeight: FontWeight.w700)),
          const SizedBox(height: 2),
          Text(subtitle,
              style: theme.textTheme.bodySmall?.copyWith(
                  color: theme.colorScheme.onSurface.withValues(alpha: 0.45),
                  fontSize: 12)),
          const SizedBox(height: 20),
          SizedBox(height: 180, child: chart),
        ],
      ),
    );
  }
}

// ── Shared chart helpers ───────────────────────────────────────────────────
double _niceMax(List<double> values, double base) {
  if (values.isEmpty) return base;
  final max = values.reduce((a, b) => a > b ? a : b);
  return ((max * 1.15) / base).ceil() * base;
}

double _niceInterval(double maxY, int steps) =>
    ((maxY / steps) / 5).ceil() * 5;

Widget _bottomLabel(
    double v, List<String> labels, TextStyle style, int step) {
  final i = v.toInt();
  if (i < 0 || i >= labels.length || i % step != 0) return const SizedBox();
  return Padding(
    padding: const EdgeInsets.only(top: 6),
    child: Text(labels[i], style: style),
  );
}

// ── Posture Line Chart ─────────────────────────────────────────────────────
class _PostureLineChart extends StatelessWidget {
  const _PostureLineChart({required this.scores, required this.labels});
  final List<double> scores;
  final List<String> labels;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final textStyle = TextStyle(
        color: theme.colorScheme.onSurface.withValues(alpha: 0.45),
        fontSize: 10);
    final step = labels.length > 8 ? 2 : 1;

    return LineChart(LineChartData(
      minY: 55,
      maxY: 100,
      gridData: FlGridData(
        show: true,
        drawVerticalLine: false,
        horizontalInterval: 15,
        getDrawingHorizontalLine: (_) => FlLine(
            color: theme.dividerColor.withValues(alpha: 0.6), strokeWidth: 0.8),
      ),
      borderData: FlBorderData(show: false),
      titlesData: FlTitlesData(
        leftTitles: AxisTitles(
          sideTitles: SideTitles(
            showTitles: true,
            reservedSize: 36,
            interval: 15,
            getTitlesWidget: (v, _) =>
                Text('${v.toInt()}', style: textStyle),
          ),
        ),
        bottomTitles: AxisTitles(
          sideTitles: SideTitles(
            showTitles: true,
            interval: 1,
            getTitlesWidget: (v, _) =>
                _bottomLabel(v, labels, textStyle, step),
          ),
        ),
        rightTitles:
            const AxisTitles(sideTitles: SideTitles(showTitles: false)),
        topTitles:
            const AxisTitles(sideTitles: SideTitles(showTitles: false)),
      ),
      lineBarsData: [
        LineChartBarData(
          spots: scores
              .asMap()
              .entries
              .map((e) => FlSpot(e.key.toDouble(), e.value))
              .toList(),
          isCurved: true,
          curveSmoothness: 0.35,
          color: AppColors.primary,
          barWidth: 2.5,
          dotData: FlDotData(
            show: true,
            getDotPainter: (_, __, ___, ____) => FlDotCirclePainter(
              radius: 3,
              color: AppColors.primary,
              strokeColor: Colors.white,
              strokeWidth: 1.5,
            ),
          ),
          belowBarData: BarAreaData(
            show: true,
            gradient: LinearGradient(
              begin: Alignment.topCenter,
              end: Alignment.bottomCenter,
              colors: [
                AppColors.primary.withValues(alpha: 0.22),
                AppColors.primary.withValues(alpha: 0.0),
              ],
            ),
          ),
        ),
      ],
    ));
  }
}

// ── Reps Bar Chart ─────────────────────────────────────────────────────────
class _RepsBarChart extends StatelessWidget {
  const _RepsBarChart({required this.reps, required this.labels});
  final List<double> reps;
  final List<String> labels;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final textStyle = TextStyle(
        color: theme.colorScheme.onSurface.withValues(alpha: 0.45),
        fontSize: 10);
    final step = labels.length > 8 ? 2 : 1;

    final maxY = _niceMax(reps, 50);
    final yInterval = _niceInterval(maxY, 4).toDouble();

    return BarChart(BarChartData(
      maxY: maxY,
      gridData: FlGridData(
        show: true,
        drawVerticalLine: false,
        horizontalInterval: yInterval,
        getDrawingHorizontalLine: (_) => FlLine(
            color: theme.dividerColor.withValues(alpha: 0.6), strokeWidth: 0.8),
      ),
      borderData: FlBorderData(show: false),
      titlesData: FlTitlesData(
        leftTitles: AxisTitles(
          sideTitles: SideTitles(
            showTitles: true,
            reservedSize: 40,
            interval: yInterval,
            getTitlesWidget: (v, _) =>
                Text('${v.toInt()}', style: textStyle),
          ),
        ),
        bottomTitles: AxisTitles(
          sideTitles: SideTitles(
            showTitles: true,
            interval: 1,
            getTitlesWidget: (v, _) =>
                _bottomLabel(v, labels, textStyle, step),
          ),
        ),
        rightTitles:
            const AxisTitles(sideTitles: SideTitles(showTitles: false)),
        topTitles:
            const AxisTitles(sideTitles: SideTitles(showTitles: false)),
      ),
      barGroups: reps
          .asMap()
          .entries
          .map((e) => BarChartGroupData(
                x: e.key,
                barRods: [
                  BarChartRodData(
                    toY: e.value,
                    gradient: AppColors.orangeGradient,
                    width: labels.length > 8 ? 8 : 14,
                    borderRadius: const BorderRadius.vertical(
                        top: Radius.circular(5)),
                  ),
                ],
              ))
          .toList(),
    ));
  }
}

// ── Workout Time Line Chart ────────────────────────────────────────────────
class _WorkoutTimeLineChart extends StatelessWidget {
  const _WorkoutTimeLineChart(
      {required this.minutes, required this.labels});
  final List<double> minutes;
  final List<String> labels;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final textStyle = TextStyle(
        color: theme.colorScheme.onSurface.withValues(alpha: 0.45),
        fontSize: 10);
    final step = labels.length > 8 ? 2 : 1;

    final maxY = _niceMax(minutes, 50);
    final yInterval = _niceInterval(maxY, 4).toDouble();

    return LineChart(LineChartData(
      minY: 0,
      maxY: maxY,
      gridData: FlGridData(
        show: true,
        drawVerticalLine: false,
        horizontalInterval: yInterval,
        getDrawingHorizontalLine: (_) => FlLine(
            color: theme.dividerColor.withValues(alpha: 0.6), strokeWidth: 0.8),
      ),
      borderData: FlBorderData(show: false),
      titlesData: FlTitlesData(
        leftTitles: AxisTitles(
          sideTitles: SideTitles(
            showTitles: true,
            reservedSize: 40,
            interval: yInterval,
            getTitlesWidget: (v, _) =>
                Text('${v.toInt()}', style: textStyle),
          ),
        ),
        bottomTitles: AxisTitles(
          sideTitles: SideTitles(
            showTitles: true,
            interval: 1,
            getTitlesWidget: (v, _) =>
                _bottomLabel(v, labels, textStyle, step),
          ),
        ),
        rightTitles:
            const AxisTitles(sideTitles: SideTitles(showTitles: false)),
        topTitles:
            const AxisTitles(sideTitles: SideTitles(showTitles: false)),
      ),
      lineBarsData: [
        LineChartBarData(
          spots: minutes
              .asMap()
              .entries
              .map((e) => FlSpot(e.key.toDouble(), e.value))
              .toList(),
          isCurved: true,
          curveSmoothness: 0.35,
          color: AppColors.info,
          barWidth: 2.5,
          dotData: FlDotData(
            show: true,
            getDotPainter: (_, __, ___, ____) => FlDotCirclePainter(
              radius: 3,
              color: AppColors.info,
              strokeColor: Colors.white,
              strokeWidth: 1.5,
            ),
          ),
          belowBarData: BarAreaData(
            show: true,
            gradient: LinearGradient(
              begin: Alignment.topCenter,
              end: Alignment.bottomCenter,
              colors: [
                AppColors.info.withValues(alpha: 0.2),
                AppColors.info.withValues(alpha: 0.0),
              ],
            ),
          ),
        ),
      ],
    ));
  }
}

// ── Recent Records ─────────────────────────────────────────────────────────
class _RecentRecordsSection extends StatelessWidget {
  const _RecentRecordsSection({required this.strings});
  final dynamic strings;

  String _formatDate(DateTime date, dynamic s) {
    final now = DateTime.now();
    final diff = now.difference(date).inDays;
    if (diff == 0) return s.today;
    if (diff == 1) return s.yesterday;
    return '${date.month}/${date.day}/${date.year}';
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;
    final s = strings;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(s.workoutHistory,
            style: theme.textTheme.titleMedium
                ?.copyWith(fontWeight: FontWeight.w700)),
        const SizedBox(height: 12),
        ...mockWorkoutRecords.map((r) {
              final scoreColor = r.postureScore >= 90
                  ? AppColors.scoreExcellent
                  : r.postureScore >= 75
                      ? AppColors.scoreGood
                      : AppColors.scoreFair;
              return GestureDetector(
                onTap: () => context.push(
                  RouteConstants.workoutResult,
                  extra: {
                    'exerciseId': r.exerciseId,
                    'exerciseName': r.exerciseName,
                    'exerciseNameKr': findExercise(r.exerciseId).nameKr,
                    'totalReps': r.totalReps,
                    'correctReps': r.correctReps,
                    'incorrectReps': r.incorrectReps,
                    'elapsedSeconds': r.durationSeconds,
                    'postureScore': r.postureScore,
                    'feedbackHistory': r.feedbackNotes,
                    'targetSets': 0,
                    'isHistory': true,
                    'date': r.date,
                  },
                ),
                child: Container(
                  margin: const EdgeInsets.only(bottom: 10),
                  padding: const EdgeInsets.all(14),
                  decoration: BoxDecoration(
                    color: isDark ? AppColors.darkCard : AppColors.lightCard,
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Row(
                    children: [
                      Container(
                        width: 40,
                        height: 40,
                        decoration: BoxDecoration(
                          color: scoreColor.withValues(alpha: 0.12),
                          borderRadius: BorderRadius.circular(10),
                        ),
                        child: Image.asset(
                          findExercise(r.exerciseId).imagePath,
                          width: 24,
                          height: 24,
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(r.exerciseName,
                                style: theme.textTheme.bodyMedium
                                    ?.copyWith(fontWeight: FontWeight.w600)),
                            const SizedBox(height: 2),
                            Text(_formatDate(r.date, s),
                                style: theme.textTheme.bodySmall?.copyWith(
                                  color: theme.colorScheme.onSurface
                                      .withValues(alpha: 0.45),
                                )),
                          ],
                        ),
                      ),
                      Column(
                        crossAxisAlignment: CrossAxisAlignment.end,
                        children: [
                          Text(
                            '${r.postureScore.toInt()}%',
                            style: TextStyle(
                              color: scoreColor,
                              fontWeight: FontWeight.w700,
                              fontSize: 14,
                            ),
                          ),
                          const SizedBox(height: 3),
                          if (r.targetReps > 0)
                            Row(
                              children: [
                                Icon(Icons.flag_rounded,
                                    size: 10,
                                    color: theme.colorScheme.onSurface
                                        .withValues(alpha: 0.4)),
                                const SizedBox(width: 3),
                                Text(
                                  '${r.achievement}%',
                                  style: theme.textTheme.bodySmall?.copyWith(
                                    color: theme.colorScheme.onSurface
                                        .withValues(alpha: 0.55),
                                    fontWeight: FontWeight.w600,
                                    fontSize: 11,
                                  ),
                                ),
                              ],
                            )
                          else
                            Text(
                              r.totalReps > 0
                                  ? '${r.totalReps} ${s.reps}'
                                  : r.durationFormatted,
                              style: theme.textTheme.bodySmall?.copyWith(
                                color: theme.colorScheme.onSurface
                                    .withValues(alpha: 0.45),
                              ),
                            ),
                        ],
                      ),
                      const SizedBox(width: 6),
                      Icon(Icons.chevron_right_rounded,
                          color: theme.colorScheme.onSurface
                              .withValues(alpha: 0.3),
                          size: 18),
                    ],
                  ),
                ),
              );
            }),
      ],
    );
  }
}
