import 'package:flutter/material.dart';

import '../models/exercise_model.dart';
import '../models/user_model.dart';
import '../models/workout_record_model.dart';

// ── Mock User ──────────────────────────────────────────────────────────────
final mockUser = UserModel(
  id: 'u001',
  name: 'Jin Jeong',
  email: 'jinjeong619@gmail.com',
  avatarInitials: 'JJ',
  age: 24,
  weightKg: 70,
  heightCm: 175,
  totalWorkouts: 48,
  streakDays: 7,
  joinedAt: DateTime(2025, 1, 15),
);

// ── Mock Exercises ─────────────────────────────────────────────────────────
final mockExercises = <ExerciseModel>[
  const ExerciseModel(
    id: 'squat',
    name: 'Squat',
    nameKr: '스쿼트',
    description: 'Compound lower-body movement targeting quads & glutes.',
    icon: Icons.accessibility_new_rounded,
    type: ExerciseType.reps,
    defaultReps: 15,
    defaultSets: 3,
    defaultDurationSeconds: 0,
    targetMuscles: ['Quads', 'Glutes', 'Hamstrings', 'Core'],
    difficulty: DifficultyLevel.beginner,
    accentColor: Color(0xFF00C6AE),
  ),
  const ExerciseModel(
    id: 'pushup',
    name: 'Push-up',
    nameKr: '푸시업',
    description: 'Upper-body push targeting chest, shoulders & triceps.',
    icon: Icons.fitness_center_rounded,
    type: ExerciseType.reps,
    defaultReps: 12,
    defaultSets: 3,
    defaultDurationSeconds: 0,
    targetMuscles: ['Chest', 'Shoulders', 'Triceps', 'Core'],
    difficulty: DifficultyLevel.beginner,
    accentColor: Color(0xFFFF6B35),
  ),
  const ExerciseModel(
    id: 'lunge',
    name: 'Lunge',
    nameKr: '런지',
    description: 'Unilateral lower-body movement improving balance & strength.',
    icon: Icons.directions_walk_rounded,
    type: ExerciseType.reps,
    defaultReps: 12,
    defaultSets: 3,
    defaultDurationSeconds: 0,
    targetMuscles: ['Quads', 'Glutes', 'Hamstrings'],
    difficulty: DifficultyLevel.intermediate,
    accentColor: Color(0xFF8B5CF6),
  ),
  const ExerciseModel(
    id: 'plank',
    name: 'Plank',
    nameKr: '플랭크',
    description: 'Isometric core hold for stability & endurance.',
    icon: Icons.straighten_rounded,
    type: ExerciseType.duration,
    defaultReps: 0,
    defaultSets: 3,
    defaultDurationSeconds: 60,
    targetMuscles: ['Core', 'Shoulders', 'Back'],
    difficulty: DifficultyLevel.beginner,
    accentColor: Color(0xFFF59E0B),
  ),
];

ExerciseModel findExercise(String id) =>
    mockExercises.firstWhere((e) => e.id == id, orElse: () => mockExercises[0]);

// ── Mock Workout Records ───────────────────────────────────────────────────
final mockWorkoutRecords = <WorkoutRecordModel>[
  WorkoutRecordModel(
    id: 'r001',
    exerciseId: 'squat',
    exerciseName: 'Squat',
    date: DateTime.now().subtract(const Duration(days: 0)),
    totalReps: 15,
    correctReps: 13,
    incorrectReps: 2,
    durationSeconds: 320,
    postureScore: 88,
    feedbackNotes: ['Great depth!', 'Watch knee alignment on rep 4 & 9'],
  ),
  WorkoutRecordModel(
    id: 'r002',
    exerciseId: 'pushup',
    exerciseName: 'Push-up',
    date: DateTime.now().subtract(const Duration(days: 1)),
    totalReps: 12,
    correctReps: 11,
    incorrectReps: 1,
    durationSeconds: 240,
    postureScore: 92,
    feedbackNotes: ['Excellent form!', 'Keep core tight throughout'],
  ),
  WorkoutRecordModel(
    id: 'r003',
    exerciseId: 'lunge',
    exerciseName: 'Lunge',
    date: DateTime.now().subtract(const Duration(days: 2)),
    totalReps: 12,
    correctReps: 10,
    incorrectReps: 2,
    durationSeconds: 280,
    postureScore: 80,
    feedbackNotes: ['Good balance', 'Lower your back knee more'],
  ),
  WorkoutRecordModel(
    id: 'r004',
    exerciseId: 'plank',
    exerciseName: 'Plank',
    date: DateTime.now().subtract(const Duration(days: 3)),
    totalReps: 0,
    correctReps: 0,
    incorrectReps: 0,
    durationSeconds: 180,
    postureScore: 95,
    feedbackNotes: ['Perfect alignment!', 'Hip slightly too high at 1:10'],
  ),
  WorkoutRecordModel(
    id: 'r005',
    exerciseId: 'squat',
    exerciseName: 'Squat',
    date: DateTime.now().subtract(const Duration(days: 4)),
    totalReps: 15,
    correctReps: 12,
    incorrectReps: 3,
    durationSeconds: 310,
    postureScore: 82,
    feedbackNotes: ['Consistent pace', 'Toes pointing forward more'],
  ),
  WorkoutRecordModel(
    id: 'r006',
    exerciseId: 'pushup',
    exerciseName: 'Push-up',
    date: DateTime.now().subtract(const Duration(days: 5)),
    totalReps: 10,
    correctReps: 9,
    incorrectReps: 1,
    durationSeconds: 200,
    postureScore: 90,
    feedbackNotes: ['Great chest activation', 'Lock out elbows at top'],
  ),
  WorkoutRecordModel(
    id: 'r007',
    exerciseId: 'squat',
    exerciseName: 'Squat',
    date: DateTime.now().subtract(const Duration(days: 7)),
    totalReps: 20,
    correctReps: 17,
    incorrectReps: 3,
    durationSeconds: 420,
    postureScore: 85,
    feedbackNotes: ['Strong set!', 'Maintain neutral spine'],
  ),
];

// ── Chart Mock Data ────────────────────────────────────────────────────────
final dailyPostureScores = [78.0, 82.0, 80.0, 85.0, 88.0, 84.0, 92.0];
final weeklyReps = [45.0, 60.0, 38.0, 72.0, 55.0, 80.0, 68.0];
final monthlyWorkoutMinutes = [120.0, 90.0, 150.0, 200.0, 175.0, 220.0, 190.0,
  240.0, 210.0, 180.0, 230.0, 260.0];

// Real-time feedback pool
const workoutFeedbacks = [
  'Great form! Keep going!',
  'Keep your back straight',
  'Lower your hips more',
  'Perfect depth!',
  'Control your descent',
  'Excellent posture!',
  'Engage your core',
  'Eyes forward',
  'Breathe out on the way up',
  'Full range of motion!',
];
