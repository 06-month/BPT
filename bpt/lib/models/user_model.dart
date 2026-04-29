import 'dart:convert';

class UserModel {
  final String id;
  final String username;
  final String name;
  final String email;
  final String password;
  final String avatarInitials;
  final int age;
  final double weightKg;
  final double heightCm;
  final String? gender;
  final String? workoutGoal;
  final int totalWorkouts;
  final int streakDays;
  final DateTime joinedAt;

  const UserModel({
    required this.id,
    required this.username,
    required this.name,
    required this.email,
    required this.password,
    required this.avatarInitials,
    this.age = 0,
    this.weightKg = 0,
    this.heightCm = 0,
    this.gender,
    this.workoutGoal,
    this.totalWorkouts = 0,
    this.streakDays = 0,
    required this.joinedAt,
  });

  UserModel copyWith({
    String? username,
    String? name,
    String? email,
    String? password,
    String? avatarInitials,
    int? age,
    double? weightKg,
    double? heightCm,
    String? gender,
    String? workoutGoal,
    int? totalWorkouts,
    int? streakDays,
  }) {
    return UserModel(
      id: id,
      username: username ?? this.username,
      name: name ?? this.name,
      email: email ?? this.email,
      password: password ?? this.password,
      avatarInitials: avatarInitials ?? this.avatarInitials,
      age: age ?? this.age,
      weightKg: weightKg ?? this.weightKg,
      heightCm: heightCm ?? this.heightCm,
      gender: gender ?? this.gender,
      workoutGoal: workoutGoal ?? this.workoutGoal,
      totalWorkouts: totalWorkouts ?? this.totalWorkouts,
      streakDays: streakDays ?? this.streakDays,
      joinedAt: joinedAt,
    );
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'username': username,
        'name': name,
        'email': email,
        'password': password,
        'avatarInitials': avatarInitials,
        'age': age,
        'weightKg': weightKg,
        'heightCm': heightCm,
        'gender': gender,
        'workoutGoal': workoutGoal,
        'totalWorkouts': totalWorkouts,
        'streakDays': streakDays,
        'joinedAt': joinedAt.toIso8601String(),
      };

  factory UserModel.fromJson(Map<String, dynamic> json) => UserModel(
        id: json['id'] as String? ?? '',
        username: json['username'] as String? ?? '',
        name: json['name'] as String? ?? '',
        email: json['email'] as String? ?? '',
        password: json['password'] as String? ?? '',
        avatarInitials: json['avatarInitials'] as String? ?? 'U',
        age: (json['age'] as num?)?.toInt() ?? 0,
        weightKg: (json['weightKg'] as num?)?.toDouble() ?? 0,
        heightCm: (json['heightCm'] as num?)?.toDouble() ?? 0,
        gender: json['gender'] as String?,
        workoutGoal: json['workoutGoal'] as String?,
        totalWorkouts: (json['totalWorkouts'] as num?)?.toInt() ?? 0,
        streakDays: (json['streakDays'] as num?)?.toInt() ?? 0,
        joinedAt: json['joinedAt'] != null
            ? DateTime.parse(json['joinedAt'] as String)
            : DateTime.now(),
      );

  String toJsonString() => jsonEncode(toJson());
  factory UserModel.fromJsonString(String s) =>
      UserModel.fromJson(jsonDecode(s) as Map<String, dynamic>);
}
