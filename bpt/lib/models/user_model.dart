class UserModel {
  final String id;
  final String name;
  final String email;
  final String avatarInitials;
  final int age;
  final double weightKg;
  final double heightCm;
  final int totalWorkouts;
  final int streakDays;
  final DateTime joinedAt;

  const UserModel({
    required this.id,
    required this.name,
    required this.email,
    required this.avatarInitials,
    required this.age,
    required this.weightKg,
    required this.heightCm,
    required this.totalWorkouts,
    required this.streakDays,
    required this.joinedAt,
  });

  UserModel copyWith({
    String? name,
    String? email,
    String? avatarInitials,
    int? age,
    double? weightKg,
    double? heightCm,
  }) {
    return UserModel(
      id: id,
      name: name ?? this.name,
      email: email ?? this.email,
      avatarInitials: avatarInitials ?? this.avatarInitials,
      age: age ?? this.age,
      weightKg: weightKg ?? this.weightKg,
      heightCm: heightCm ?? this.heightCm,
      totalWorkouts: totalWorkouts,
      streakDays: streakDays,
      joinedAt: joinedAt,
    );
  }
}
