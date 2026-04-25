import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import '../core/theme/app_colors.dart';

/// Lightweight wrapper around fl_chart for common BPT chart patterns.
class MiniLineChart extends StatelessWidget {
  const MiniLineChart({
    super.key,
    required this.data,
    this.color = AppColors.primary,
    this.height = 60,
    this.showDots = false,
    this.showGrid = false,
  });

  final List<double> data;
  final Color color;
  final double height;
  final bool showDots;
  final bool showGrid;

  @override
  Widget build(BuildContext context) {
    if (data.isEmpty) return SizedBox(height: height);

    return SizedBox(
      height: height,
      child: LineChart(
        LineChartData(
          gridData: FlGridData(show: showGrid),
          borderData: FlBorderData(show: false),
          titlesData: const FlTitlesData(
            leftTitles:
                AxisTitles(sideTitles: SideTitles(showTitles: false)),
            rightTitles:
                AxisTitles(sideTitles: SideTitles(showTitles: false)),
            topTitles:
                AxisTitles(sideTitles: SideTitles(showTitles: false)),
            bottomTitles:
                AxisTitles(sideTitles: SideTitles(showTitles: false)),
          ),
          lineBarsData: [
            LineChartBarData(
              spots: data
                  .asMap()
                  .entries
                  .map((e) => FlSpot(e.key.toDouble(), e.value))
                  .toList(),
              isCurved: true,
              color: color,
              barWidth: 2.5,
              dotData: FlDotData(show: showDots),
              belowBarData: BarAreaData(
                show: true,
                gradient: LinearGradient(
                  begin: Alignment.topCenter,
                  end: Alignment.bottomCenter,
                  colors: [
                    color.withValues(alpha: 0.25),
                    color.withValues(alpha: 0.0),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class MiniBarChart extends StatelessWidget {
  const MiniBarChart({
    super.key,
    required this.data,
    this.color = AppColors.secondary,
    this.height = 60,
  });

  final List<double> data;
  final Color color;
  final double height;

  @override
  Widget build(BuildContext context) {
    if (data.isEmpty) return SizedBox(height: height);

    return SizedBox(
      height: height,
      child: BarChart(
        BarChartData(
          gridData: const FlGridData(show: false),
          borderData: FlBorderData(show: false),
          titlesData: const FlTitlesData(
            leftTitles:
                AxisTitles(sideTitles: SideTitles(showTitles: false)),
            rightTitles:
                AxisTitles(sideTitles: SideTitles(showTitles: false)),
            topTitles:
                AxisTitles(sideTitles: SideTitles(showTitles: false)),
            bottomTitles:
                AxisTitles(sideTitles: SideTitles(showTitles: false)),
          ),
          barGroups: data
              .asMap()
              .entries
              .map(
                (e) => BarChartGroupData(
                  x: e.key,
                  barRods: [
                    BarChartRodData(
                      toY: e.value,
                      color: color,
                      width: 8,
                      borderRadius: BorderRadius.circular(3),
                    ),
                  ],
                ),
              )
              .toList(),
        ),
      ),
    );
  }
}

/// A labeled score ring widget built with CustomPaint.
class ScoreRing extends StatelessWidget {
  const ScoreRing({
    super.key,
    required this.score,
    required this.maxScore,
    this.size = 100,
    this.strokeWidth = 8,
    this.color = AppColors.primary,
    this.centerLabel,
  });

  final double score;
  final double maxScore;
  final double size;
  final double strokeWidth;
  final Color color;
  final Widget? centerLabel;

  @override
  Widget build(BuildContext context) {
    final fraction = (score / maxScore).clamp(0.0, 1.0);
    final theme = Theme.of(context);

    return SizedBox(
      width: size,
      height: size,
      child: Stack(
        alignment: Alignment.center,
        children: [
          CircularProgressIndicator(
            value: fraction,
            strokeWidth: strokeWidth,
            backgroundColor:
                theme.colorScheme.onSurface.withValues(alpha: 0.08),
            valueColor: AlwaysStoppedAnimation(color),
            strokeCap: StrokeCap.round,
          ),
          centerLabel ??
              Text(
                '${score.toInt()}',
                style: TextStyle(
                  color: color,
                  fontWeight: FontWeight.w800,
                  fontSize: size * 0.22,
                ),
              ),
        ],
      ),
    );
  }
}
