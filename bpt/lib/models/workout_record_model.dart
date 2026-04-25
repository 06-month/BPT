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
  });

  int get accuracy =>
      totalReps == 0 ? 0 : ((correctReps / totalReps) * 100).round();

  String get durationFormatted {
    final m = durationSeconds ~/ 60;
    final s = durationSeconds % 60;
    return '${m}m ${s}s';
  }
}
