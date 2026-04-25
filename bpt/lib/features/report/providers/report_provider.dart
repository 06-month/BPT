import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../data/mock_data.dart';

enum ReportTab { daily, weekly, monthly }

final reportTabProvider = StateProvider<ReportTab>((ref) => ReportTab.weekly);

final reportDataProvider = Provider<Map<String, dynamic>>((ref) {
  final tab = ref.watch(reportTabProvider);

  switch (tab) {
    case ReportTab.daily:
      return {
        'postureScores': dailyPostureScores,
        'reps': weeklyReps.take(7).toList(),
        'workoutMinutes': [18.0, 24.0, 15.0, 28.0, 20.0, 32.0, 25.0],
        'labels': ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
        'totalWorkouts': 7,
        'totalReps': weeklyReps.take(7).fold(0.0, (a, b) => a + b).toInt(),
        'avgScore': dailyPostureScores.fold(0.0, (a, b) => a + b) /
            dailyPostureScores.length,
        'totalMinutes': 162,
      };
    case ReportTab.weekly:
      return {
        'postureScores': [82.0, 85.0, 79.0, 88.0, 91.0, 87.0, 93.0, 89.0],
        'reps': [120.0, 145.0, 98.0, 180.0, 160.0, 200.0, 175.0, 210.0],
        'workoutMinutes': [80.0, 95.0, 60.0, 120.0, 105.0, 140.0, 115.0, 155.0],
        'labels': ['W1', 'W2', 'W3', 'W4', 'W5', 'W6', 'W7', 'W8'],
        'totalWorkouts': 32,
        'totalReps': 1288,
        'avgScore': 86.6,
        'totalMinutes': 870,
      };
    case ReportTab.monthly:
      return {
        'postureScores': monthlyWorkoutMinutes
            .map((m) => 75.0 + m / 15.0)
            .toList(),
        'reps': monthlyWorkoutMinutes.map((m) => m * 2.2).toList(),
        'workoutMinutes': monthlyWorkoutMinutes,
        'labels': [
          'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
          'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'
        ],
        'totalWorkouts': 128,
        'totalReps': 5480,
        'avgScore': 87.2,
        'totalMinutes': 2365,
      };
  }
});
