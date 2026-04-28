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

  // 목표 대비 정확하게 수행한 rep 달성률
  int get achievement =>
      targetReps == 0 ? 100 : ((correctReps / targetReps) * 100).clamp(0.0, 100.0).round();

  String get durationFormatted {
    final m = durationSeconds ~/ 60;
    final s = durationSeconds % 60;
    return '${m}m ${s}s';
  }
}
