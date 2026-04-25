import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../data/mock_data.dart';
import '../../../models/exercise_model.dart';
import '../../../models/user_model.dart';
import '../../../models/workout_record_model.dart';

final currentUserProvider = Provider<UserModel>((ref) => mockUser);

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
