import 'package:firebase_auth/firebase_auth.dart';
import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/workout_record_model.dart';
import 'local_storage_service.dart';

class WorkoutRecordsNotifier
    extends StateNotifier<List<WorkoutRecordModel>> {
  final LocalStorageService _storage;

  WorkoutRecordsNotifier(this._storage)
      : super(_storage.loadRecords());

  Future<void> addRecord(WorkoutRecordModel record) async {
    await _storage.addRecord(record);
    state = [record, ...state];
  }

  /// Returns the number of consecutive days (ending today or yesterday)
  /// that had at least one workout.
  int get streakDays {
    if (state.isEmpty) return 0;

    final today = _dateOnly(DateTime.now());
    final uniqueDays = state
        .map((r) => _dateOnly(r.date))
        .toSet()
        .toList()
      ..sort((a, b) => b.compareTo(a));

    // Streak must include today or yesterday to be active.
    final diff = today.difference(uniqueDays.first).inDays;
    if (diff > 1) return 0;

    int streak = 1;
    for (int i = 1; i < uniqueDays.length; i++) {
      final expected =
          uniqueDays[i - 1].subtract(const Duration(days: 1));
      if (uniqueDays[i] == expected) {
        streak++;
      } else {
        break;
      }
    }
    return streak;
  }

  DateTime _dateOnly(DateTime dt) =>
      DateTime(dt.year, dt.month, dt.day);
}

final workoutRecordsProvider = StateNotifierProvider<
    WorkoutRecordsNotifier, List<WorkoutRecordModel>>(
  (ref) => WorkoutRecordsNotifier(ref.watch(localStorageServiceProvider)),
);
