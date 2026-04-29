import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/i18n/locale_provider.dart';
import '../../../models/workout_record_model.dart';
import '../../../services/workout_records_service.dart';

enum ReportTab { daily, weekly, monthly }

final reportTabProvider = StateProvider<ReportTab>((ref) => ReportTab.daily);

final reportDataProvider = Provider<Map<String, dynamic>>((ref) {
  final tab = ref.watch(reportTabProvider);
  final records = ref.watch(workoutRecordsProvider);
  final isKo = ref.watch(selectedLanguageProvider) == 'ko';

  switch (tab) {
    case ReportTab.daily:
      return _buildDailyData(records, isKo);
    case ReportTab.weekly:
      return _buildWeeklyData(records);
    case ReportTab.monthly:
      return _buildMonthlyData(records);
  }
});

// ── Helpers ───────────────────────────────────────────────────────────────

DateTime _dateOnly(DateTime dt) => DateTime(dt.year, dt.month, dt.day);

Map<String, dynamic> _emptyData() => {
      'postureScores': <double>[],
      'reps': <double>[],
      'workoutMinutes': <double>[],
      'labels': <String>[],
      'totalWorkouts': 0,
      'totalReps': 0,
      'avgScore': 0.0,
      'totalMinutes': 0,
      'avgAchievement': 0.0,
    };

// Chronological by unique workout day, labeled "1일차"/"Day 1"
Map<String, dynamic> _buildDailyData(List<WorkoutRecordModel> records, bool isKo) {
  final Map<DateTime, List<WorkoutRecordModel>> byDay = {};
  for (final r in records) {
    final day = _dateOnly(r.date);
    byDay.putIfAbsent(day, () => []).add(r);
  }

  final sortedDays = byDay.keys.toList()..sort();
  final recentDays = sortedDays.length > 7
      ? sortedDays.sublist(sortedDays.length - 7)
      : sortedDays;

  if (recentDays.isEmpty) return _emptyData();

  final startIdx = sortedDays.length - recentDays.length;
  final scores = <double>[];
  final reps = <double>[];
  final minutes = <double>[];
  final labels = <String>[];

  for (int i = 0; i < recentDays.length; i++) {
    final dayRecs = byDay[recentDays[i]]!;
    final n = startIdx + i + 1;
    labels.add(isKo ? '$n일차' : 'Day $n');
    scores.add(dayRecs.fold(0.0, (s, r) => s + r.postureScore) / dayRecs.length);
    reps.add(dayRecs.fold(0.0, (s, r) => s + r.totalReps));
    minutes.add(dayRecs.fold(0, (s, r) => s + r.durationSeconds) / 60.0);
  }

  final totalReps = reps.fold(0.0, (a, b) => a + b).toInt();
  final totalMins = minutes.fold(0.0, (a, b) => a + b).toInt();
  final validScores = scores.where((s) => s > 0).toList();
  final avgScore = validScores.isEmpty
      ? 0.0
      : validScores.fold(0.0, (a, b) => a + b) / validScores.length;

  return {
    'postureScores': scores,
    'reps': reps,
    'workoutMinutes': minutes,
    'labels': labels,
    'totalWorkouts': records.length,
    'totalReps': totalReps,
    'avgScore': avgScore,
    'totalMinutes': totalMins,
    'avgAchievement': avgScore,
  };
}

Map<String, dynamic> _buildWeeklyData(List<WorkoutRecordModel> records) {
  final now = DateTime.now();
  // Current week starts on Monday
  final currentMonday = _dateOnly(now)
      .subtract(Duration(days: now.weekday - 1));

  // Last 8 weeks: index 0 = 7 weeks ago, index 7 = current week
  final weekStarts = List.generate(
      8, (i) => currentMonday.subtract(Duration(days: (7 - i) * 7)));

  final scores = <double>[];
  final reps = <double>[];
  final minutes = <double>[];
  // Actual Monday dates as "M/D" labels so new users see real dates
  final labels = weekStarts.map((ws) => '${ws.month}/${ws.day}').toList();

  for (final weekStart in weekStarts) {
    final weekEnd = weekStart.add(const Duration(days: 7));
    final weekRecs = records
        .where((r) =>
            !_dateOnly(r.date).isBefore(weekStart) &&
            _dateOnly(r.date).isBefore(weekEnd))
        .toList();
    scores.add(weekRecs.isEmpty
        ? 0
        : weekRecs.fold(0.0, (s, r) => s + r.postureScore) /
            weekRecs.length);
    reps.add(
        weekRecs.fold(0.0, (s, r) => s + r.totalReps).toDouble());
    minutes.add(
        weekRecs.fold(0, (s, r) => s + r.durationSeconds) / 60.0);
  }

  final totalWorkouts = records
      .where((r) =>
          !_dateOnly(r.date).isBefore(weekStarts.first))
      .length;
  final totalReps = reps.fold(0.0, (a, b) => a + b).toInt();
  final totalMins = minutes.fold(0.0, (a, b) => a + b).toInt();
  final validScores = scores.where((s) => s > 0).toList();
  final avgScore = validScores.isEmpty
      ? 0.0
      : validScores.fold(0.0, (a, b) => a + b) / validScores.length;

  return {
    'postureScores': scores,
    'reps': reps,
    'workoutMinutes': minutes,
    'labels': labels,
    'totalWorkouts': totalWorkouts,
    'totalReps': totalReps,
    'avgScore': avgScore,
    'totalMinutes': totalMins,
    'avgAchievement': avgScore,
  };
}

Map<String, dynamic> _buildMonthlyData(List<WorkoutRecordModel> records) {
  final now = DateTime.now();
  // Last 12 months: index 0 = 11 months ago, index 11 = current month
  final months = List.generate(12, (i) {
    final m = now.month - (11 - i);
    final y = now.year + (m <= 0 ? -1 : 0);
    final adjustedM = m <= 0 ? m + 12 : m;
    return DateTime(y, adjustedM);
  });

  final labels = [
    'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
    'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'
  ];
  final monthLabels =
      months.map((m) => labels[m.month - 1]).toList();

  final scores = <double>[];
  final reps = <double>[];
  final minutes = <double>[];

  for (final month in months) {
    final monthRecs = records
        .where((r) =>
            r.date.year == month.year && r.date.month == month.month)
        .toList();
    scores.add(monthRecs.isEmpty
        ? 0
        : monthRecs.fold(0.0, (s, r) => s + r.postureScore) /
            monthRecs.length);
    reps.add(
        monthRecs.fold(0.0, (s, r) => s + r.totalReps).toDouble());
    minutes.add(
        monthRecs.fold(0, (s, r) => s + r.durationSeconds) / 60.0);
  }

  final totalWorkouts = records
      .where((r) => !DateTime(r.date.year, r.date.month)
          .isBefore(months.first))
      .length;
  final totalReps = reps.fold(0.0, (a, b) => a + b).toInt();
  final totalMins = minutes.fold(0.0, (a, b) => a + b).toInt();
  final validScores = scores.where((s) => s > 0).toList();
  final avgScore = validScores.isEmpty
      ? 0.0
      : validScores.fold(0.0, (a, b) => a + b) / validScores.length;

  return {
    'postureScores': scores,
    'reps': reps,
    'workoutMinutes': minutes,
    'labels': monthLabels,
    'totalWorkouts': totalWorkouts,
    'totalReps': totalReps,
    'avgScore': avgScore,
    'totalMinutes': totalMins,
    'avgAchievement': avgScore,
  };
}
