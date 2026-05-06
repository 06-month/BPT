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
    // 학번이나 다른 정보가 있다면 여기에 추가
  }) async {
    try {
      // 1. Auth 계정 생성
      UserCredential userCredential = await _auth.createUserWithEmailAndPassword(
        email: email,
        password: password,
      );

      // 2. 생성된 UID로 Firestore에 문서 생성
      await _firestore.collection('users').doc(userCredential.user!.uid).set({
        'uid': userCredential.user!.uid,
        'email': email,
        'name': name,
        'createdAt': FieldValue.serverTimestamp(),
      });
    } catch (e) {
      rethrow; // 에러를 UI 쪽으로 던져서 알림을 띄울 수 있게 함
    }
  }
}