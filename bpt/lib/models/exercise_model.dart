import 'package:flutter/material.dart';

enum ExerciseType { reps, duration }

enum DifficultyLevel { beginner, intermediate, advanced }

class ExerciseModel {
  final String id;
  final String name;
  final String nameKr;
  final String description;
  final IconData icon;
  final ExerciseType type;
  final int defaultReps;
  final int defaultSets;
  final int defaultDurationSeconds;
  final List<String> targetMuscles;
  final DifficultyLevel difficulty;
  final Color accentColor;

  const ExerciseModel({
    required this.id,
    required this.name,
    required this.nameKr,
    required this.description,
    required this.icon,
    required this.type,
    required this.defaultReps,
    required this.defaultSets,
    required this.defaultDurationSeconds,
    required this.targetMuscles,
    required this.difficulty,
    required this.accentColor,
  });

  String get difficultyLabel {
    switch (difficulty) {
      case DifficultyLevel.beginner:
        return 'Beginner';
      case DifficultyLevel.intermediate:
        return 'Intermediate';
      case DifficultyLevel.advanced:
        return 'Advanced';
    }
  }
}
