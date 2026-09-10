import 'package:flutter_riverpod/flutter_riverpod.dart';

enum Gender { male, female, preferNotToSay }

enum BmiCategory { underweight, normal, overweight, obese }

class OnboardingState {
  const OnboardingState({
    this.gender,
    this.heightCm = 176,
    this.weightKg = 71.5,
  });

  final Gender? gender;
  final double heightCm;
  final double weightKg;

  /// weight(kg) / height(m)^2
  double get bmi => weightKg / ((heightCm / 100) * (heightCm / 100));

  BmiCategory get bmiCategory {
    if (bmi < 18.5) return BmiCategory.underweight;
    if (bmi < 23) return BmiCategory.normal;
    if (bmi < 25) return BmiCategory.overweight;
    return BmiCategory.obese;
  }

  String get bmiCategoryLabel => switch (bmiCategory) {
        BmiCategory.underweight => '저체중',
        BmiCategory.normal => '정상 범위',
        BmiCategory.overweight => '과체중',
        BmiCategory.obese => '비만',
      };

  OnboardingState copyWith({
    Gender? gender,
    double? heightCm,
    double? weightKg,
  }) =>
      OnboardingState(
        gender: gender ?? this.gender,
        heightCm: heightCm ?? this.heightCm,
        weightKg: weightKg ?? this.weightKg,
      );
}

class OnboardingNotifier extends StateNotifier<OnboardingState> {
  OnboardingNotifier() : super(const OnboardingState());

  void selectGender(Gender gender) => state = state.copyWith(gender: gender);

  void setHeight(double heightCm) => state = state.copyWith(heightCm: heightCm);

  void setWeight(double weightKg) => state = state.copyWith(weightKg: weightKg);
}

final onboardingProvider =
    StateNotifierProvider<OnboardingNotifier, OnboardingState>(
  (ref) => OnboardingNotifier(),
);
