import 'dart:convert';

class WorkoutRecordModel {
  final String id;
  final String exerciseId;
  final String exerciseName;
  final DateTime date;
  final int totalReps;
  final int correctReps;
  final int incorrectReps;
  final int durationSeconds;
  final double postureScore;
  final List<String> feedbackNotes;
  final int targetReps;
  final int targetSets;

  const WorkoutRecordModel({
    required this.id,
    required this.exerciseId,
    required this.exerciseName,
    required this.date,
    required this.totalReps,
    required this.correctReps,
    required this.incorrectReps,
    required this.durationSeconds,
    required this.postureScore,
    required this.feedbackNotes,
    this.targetReps = 0,
    this.targetSets = 1,
  });

  int get accuracy =>
      totalReps == 0 ? 0 : ((correctReps / totalReps) * 100).round();

  int get achievement =>
      targetReps == 0 ? 100 : ((correctReps / targetReps) * 100).clamp(0.0, 100.0).round();

  String get durationFormatted {
    final m = durationSeconds ~/ 60;
    final s = durationSeconds % 60;
    return '${m}m ${s}s';
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'exerciseId': exerciseId,
        'exerciseName': exerciseName,
        'date': date.toIso8601String(),
        'totalReps': totalReps,
        'correctReps': correctReps,
        'incorrectReps': incorrectReps,
        'durationSeconds': durationSeconds,
        'postureScore': postureScore,
        'feedbackNotes': feedbackNotes,
        'targetReps': targetReps,
        'targetSets': targetSets,
      };

  factory WorkoutRecordModel.fromJson(Map<String, dynamic> json) =>
      WorkoutRecordModel(
        id: json['id'] as String? ?? '',
        exerciseId: json['exerciseId'] as String? ?? '',
        exerciseName: json['exerciseName'] as String? ?? '',
        date: json['date'] != null
            ? DateTime.parse(json['date'] as String)
            : DateTime.now(),
        totalReps: (json['totalReps'] as num?)?.toInt() ?? 0,
        correctReps: (json['correctReps'] as num?)?.toInt() ?? 0,
        incorrectReps: (json['incorrectReps'] as num?)?.toInt() ?? 0,
        durationSeconds: (json['durationSeconds'] as num?)?.toInt() ?? 0,
        postureScore: (json['postureScore'] as num?)?.toDouble() ?? 0.0,
        feedbackNotes:
            (json['feedbackNotes'] as List?)?.cast<String>() ?? [],
        targetReps: (json['targetReps'] as num?)?.toInt() ?? 0,
        targetSets: (json['targetSets'] as num?)?.toInt() ?? 1,
      );

  String toJsonString() => jsonEncode(toJson());
  factory WorkoutRecordModel.fromJsonString(String s) =>
      WorkoutRecordModel.fromJson(jsonDecode(s) as Map<String, dynamic>);
}
