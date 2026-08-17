import 'package:cloud_firestore/cloud_firestore.dart';

class AuthService {
  final FirebaseFirestore _firestore = FirebaseFirestore.instance;

  // Firestore에 사용자 데이터만 저장 (계정 생성과 분리)
  Future<void> saveUserData({
    required String uid,
    required String name,
    required String email,
    DateTime? birthDate,
    double? weight,
    double? height,
    String? gender,
    String? goal,
  }) async {
    final initials = name.isNotEmpty ? name[0].toUpperCase() : 'U';
    await _firestore.collection('users').doc(uid).set({
      'id': uid,
      'uid': uid,
      'username': email,
      'name': name,
      'email': email,
      'password': '',
      'avatarInitials': initials,
      'birthDate': birthDate?.toIso8601String(),
      'weightKg': weight ?? 0.0,
      'heightCm': height ?? 0.0,
      'gender': gender,
      'workoutGoal': goal,
      'totalWorkouts': 0,
      'streakDays': 0,
      'joinedAt': DateTime.now().toIso8601String(),
      'createdAt': FieldValue.serverTimestamp(),
    }, SetOptions(merge: true));
  }
}