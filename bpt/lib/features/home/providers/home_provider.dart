import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../data/mock_data.dart';
import '../../../features/auth/providers/auth_provider.dart';
import '../../../models/exercise_model.dart';
import '../../../models/user_model.dart';
import '../../../models/workout_record_model.dart';

final currentUserProvider = Provider<UserModel>((ref) {
  return ref.watch(authNotifierProvider).currentUser ?? mockUser;
});

final weeklyWorkoutGoalProvider = StateProvider<int>((ref) => 5);

final weeklyWorkoutsProvider = Provider<int>((ref) {
  final now = DateTime.now();
  final weekStart = DateTime(now.year, now.month, now.day)
      .subtract(Duration(days: now.weekday - 1));
  return mockWorkoutRecords
      .where((r) => !r.date.isBefore(weekStart))
      .length;
});

final recentRecordsProvider = Provider<List<WorkoutRecordModel>>(
  (ref) => mockWorkoutRecords.take(3).toList(),
);

final allRecordsProvider = Provider<List<WorkoutRecordModel>>(
  (ref) => mockWorkoutRecords,
);

final recommendedExerciseProvider = Provider<ExerciseModel>(
  (ref) => mockExercises[0],
);

// Today's summary aggregation
final todaySummaryProvider = Provider<Map<String, dynamic>>((ref) {
  final today = DateTime.now();
  final records = mockWorkoutRecords.where((r) {
    return r.date.year == today.year &&
        r.date.month == today.month &&
        r.date.day == today.day;
  }).toList();

  final totalReps = records.fold(0, (sum, r) => sum + r.totalReps);
  final totalSecs = records.fold(0, (sum, r) => sum + r.durationSeconds);
  final avgScore = records.isEmpty
      ? 0.0
      : records.fold(0.0, (sum, r) => sum + r.postureScore) / records.length;

  return {
    'workoutsToday': records.length,
    'totalReps': totalReps,
    'totalMinutes': totalSecs ~/ 60,
    'avgPostureScore': avgScore,
    'streak': mockUser.streakDays,
  };
});
