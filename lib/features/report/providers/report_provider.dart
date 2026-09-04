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
      return _buildWeeklyData(records, isKo);
    case ReportTab.monthly:
      return _buildMonthlyData(records, isKo);
  }
});

// ── Helpers ───────────────────────────────────────────────────────────────

DateTime _dateOnly(DateTime dt) => DateTime(dt.year, dt.month, dt.day);

Map<String, dynamic> _buildSummary({
  required List<double> scores,
  required List<double> reps,
  required List<double> minutes,
  required List<WorkoutRecordModel> windowRecords,
}) {
  final totalReps = reps.fold(0.0, (a, b) => a + b).toInt();
  final totalMins = minutes.fold(0.0, (a, b) => a + b).toInt();
  final validScores = scores.where((s) => s > 0).toList();
  final avgScore = validScores.isEmpty
      ? 0.0
      : validScores.fold(0.0, (a, b) => a + b) / validScores.length;
  return {
    'totalWorkouts': windowRecords.length,
    'totalReps': totalReps,
    'avgScore': avgScore,
    'totalMinutes': totalMins,
    'avgAchievement': avgScore,
  };
}

// ── Daily: 오늘 포함 최근 7 달력 일 ──────────────────────────────────────────
Map<String, dynamic> _buildDailyData(
    List<WorkoutRecordModel> records, bool isKo) {
  final today = _dateOnly(DateTime.now());
  // index 0 = 6일 전, index 6 = 오늘
  final days = List.generate(7, (i) => today.subtract(Duration(days: 6 - i)));

  final labels = days.map((d) => '${d.month}/${d.day}').toList();
  final scores = <double>[];
  final reps = <double>[];
  final minutes = <double>[];

  for (final day in days) {
    final dayRecs =
        records.where((r) => _dateOnly(r.date) == day).toList();
    scores.add(dayRecs.isEmpty
        ? 0
        : dayRecs.fold(0.0, (s, r) => s + r.postureScore) / dayRecs.length);
    reps.add(dayRecs.fold(0.0, (s, r) => s + r.totalReps.toDouble()));
    minutes.add(dayRecs.fold(0, (s, r) => s + r.durationSeconds) / 60.0);
  }

  final windowRecs =
      records.where((r) => !_dateOnly(r.date).isBefore(days.first)).toList();

  return {
    'postureScores': scores,
    'reps': reps,
    'workoutMinutes': minutes,
    'labels': labels,
    ..._buildSummary(
        scores: scores,
        reps: reps,
        minutes: minutes,
        windowRecords: windowRecs),
  };
}

// ── Weekly: 현재 주 포함 최근 6주 ────────────────────────────────────────────
Map<String, dynamic> _buildWeeklyData(
    List<WorkoutRecordModel> records, bool isKo) {
  final now = DateTime.now();
  final currentMonday =
      _dateOnly(now).subtract(Duration(days: now.weekday - 1));

  // index 0 = 5주 전 월요일, index 5 = 이번 주 월요일
  final weekStarts = List.generate(
      6, (i) => currentMonday.subtract(Duration(days: (5 - i) * 7)));

  final labels = weekStarts.asMap().entries.map((e) {
    final ws = e.value;
    final isCurrentWeek = e.key == weekStarts.length - 1;
    if (isCurrentWeek) return isKo ? '이번주' : 'Now';
    return '${ws.month}/${ws.day}';
  }).toList();

  final scores = <double>[];
  final reps = <double>[];
  final minutes = <double>[];

  for (final weekStart in weekStarts) {
    final weekEnd = weekStart.add(const Duration(days: 7));
    final weekRecs = records
        .where((r) =>
            !_dateOnly(r.date).isBefore(weekStart) &&
            _dateOnly(r.date).isBefore(weekEnd))
        .toList();
    scores.add(weekRecs.isEmpty
        ? 0
        : weekRecs.fold(0.0, (s, r) => s + r.postureScore) / weekRecs.length);
    reps.add(weekRecs.fold(0.0, (s, r) => s + r.totalReps.toDouble()));
    minutes
        .add(weekRecs.fold(0, (s, r) => s + r.durationSeconds) / 60.0);
  }

  final windowRecs = records
      .where((r) => !_dateOnly(r.date).isBefore(weekStarts.first))
      .toList();

  return {
    'postureScores': scores,
    'reps': reps,
    'workoutMinutes': minutes,
    'labels': labels,
    ..._buildSummary(
        scores: scores,
        reps: reps,
        minutes: minutes,
        windowRecords: windowRecs),
  };
}

// ── Monthly: 현재 달 포함 최근 6개월 ─────────────────────────────────────────
Map<String, dynamic> _buildMonthlyData(
    List<WorkoutRecordModel> records, bool isKo) {
  final now = DateTime.now();
  // index 0 = 5달 전, index 5 = 이번 달
  final months = List.generate(6, (i) {
    final offset = 5 - i;
    int m = now.month - offset;
    int y = now.year;
    while (m <= 0) {
      m += 12;
      y--;
    }
    return DateTime(y, m);
  });

  final koMonths = ['1월','2월','3월','4월','5월','6월',
                    '7월','8월','9월','10월','11월','12월'];
  final enMonths = ['Jan','Feb','Mar','Apr','May','Jun',
                    'Jul','Aug','Sep','Oct','Nov','Dec'];

  final labels = months.map((m) {
    final isCurrentMonth = m.year == now.year && m.month == now.month;
    final base = isKo ? koMonths[m.month - 1] : enMonths[m.month - 1];
    return isCurrentMonth ? (isKo ? '이번달' : 'Now') : base;
  }).toList();

  final scores = <double>[];
  final reps = <double>[];
  final minutes = <double>[];

  for (final month in months) {
    final monthRecs = records
        .where((r) => r.date.year == month.year && r.date.month == month.month)
        .toList();
    scores.add(monthRecs.isEmpty
        ? 0
        : monthRecs.fold(0.0, (s, r) => s + r.postureScore) /
            monthRecs.length);
    reps.add(monthRecs.fold(0.0, (s, r) => s + r.totalReps.toDouble()));
    minutes
        .add(monthRecs.fold(0, (s, r) => s + r.durationSeconds) / 60.0);
  }

  final windowRecs = records
      .where((r) =>
          r.date.year > months.first.year ||
          (r.date.year == months.first.year &&
              r.date.month >= months.first.month))
      .toList();

  return {
    'postureScores': scores,
    'reps': reps,
    'workoutMinutes': minutes,
    'labels': labels,
    ..._buildSummary(
        scores: scores,
        reps: reps,
        minutes: minutes,
        windowRecords: windowRecs),
  };
}
