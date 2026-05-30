import 'package:firebase_auth/firebase_auth.dart';
import 'package:cloud_firestore/cloud_firestore.dart';

class AuthService {
  final FirebaseAuth _auth = FirebaseAuth.instance;
  final FirebaseFirestore _firestore = FirebaseFirestore.instance;

  // 회원가입 및 사용자 정보 DB 저장 함수
  Future<void> signUpAndSaveData({
    required String email,
    required String password,
    required String name,
    int? age,
    double? weight,
    double? height,
    String? gender,
    String? goal,
  }) async {
    try {
      // 1. Auth 계정 생성
      UserCredential userCredential = await _auth.createUserWithEmailAndPassword(
        email: email,
        password: password,
      );

      final uid = userCredential.user!.uid;
      final initials = name.isNotEmpty ? name[0].toUpperCase() : 'U';

      // 2. 생성된 UID로 Firestore에 문서 생성
      await _firestore.collection('users').doc(uid).set({
        'id': uid,
        'uid': uid,
        'username': email,
        'name': name,
        'email': email,
        'password': '',
        'avatarInitials': initials,
        'age': age ?? 0,
        'weightKg': weight ?? 0.0,
        'heightCm': height ?? 0.0,
        'gender': gender,
        'workoutGoal': goal,
        'totalWorkouts': 0,
        'streakDays': 0,
        'joinedAt': DateTime.now().toIso8601String(),
        'createdAt': FieldValue.serverTimestamp(),
      });
    } catch (e) {
      rethrow; // 에러를 UI 쪽으로 던져서 알림을 띄울 수 있게 함
    }
  }
}