import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../models/user_model.dart';
import '../../../services/auth_service.dart';

final themeModeProvider = StateProvider<ThemeMode>((ref) => ThemeMode.system);

// ── Auth ───────────────────────────────────────────────────────────────────
class AuthNotifier extends ChangeNotifier {
  final FirebaseAuth _auth = FirebaseAuth.instance;
  final AuthService _authService = AuthService();

  UserModel? _currentUser;
  bool _isLoading = false;
  String? _error;

  UserModel? get currentUser => _currentUser;
  bool get isLoggedIn => _currentUser != null;
  bool get isLoading => _isLoading;
  String? get error => _error;

  Future<UserModel?> _loadFromFirestore(User user) async {
    // 로그인 직후 Firestore 보안 규칙이 토큰을 인식하지 못하는 타이밍 이슈 방지
    await user.getIdToken(true);
    final doc = await FirebaseFirestore.instance
        .collection('users')
        .doc(user.uid)
        .get();
    if (!doc.exists || doc.data() == null) return null;
    final data = doc.data()!;
    return UserModel(
      id: user.uid,
      username: data['username'] as String? ?? user.email ?? '',
      name: data['name'] as String? ?? user.displayName ?? '',
      email: data['email'] as String? ?? user.email ?? '',
      password: '',
      avatarInitials: data['avatarInitials'] as String? ??
          (user.displayName?.isNotEmpty == true
              ? user.displayName![0].toUpperCase()
              : 'U'),
      age: (data['age'] as num?)?.toInt() ?? 0,
      weightKg: (data['weightKg'] as num?)?.toDouble() ?? 0.0,
      heightCm: (data['heightCm'] as num?)?.toDouble() ?? 0.0,
      gender: data['gender'] as String?,
      workoutGoal: data['workoutGoal'] as String?,
      joinedAt: data['joinedAt'] != null
          ? (DateTime.tryParse(data['joinedAt'] as String? ?? '') ??
              DateTime.now())
          : DateTime.now(),
    );
  }

  UserModel _fallbackUser(User user) {
    final initials = (user.displayName?.isNotEmpty == true)
        ? user.displayName![0].toUpperCase()
        : 'U';
    return UserModel(
      id: user.uid,
      username: user.email ?? '',
      name: user.displayName ?? '',
      email: user.email ?? '',
      password: '',
      avatarInitials: initials,
      joinedAt: DateTime.now(),
    );
  }

  /// Firebase는 세션을 자동 유지 — currentUser가 있으면 복원
  Future<bool> tryAutoLogin() async {
    final user = _auth.currentUser;
    if (user == null) return false;
    _currentUser = await _loadFromFirestore(user) ?? _fallbackUser(user);
    notifyListeners();
    return true;
  }

  Future<void> login(String email, String password,
      {bool rememberMe = false}) async {
    _isLoading = true;
    _error = null;
    notifyListeners();

    try {
      final credential = await _auth.signInWithEmailAndPassword(
        email: email.trim(),
        password: password,
      );
      final u = credential.user!;
      _currentUser = await _loadFromFirestore(u) ?? _fallbackUser(u);
      _error = null;
    } on FirebaseAuthException catch (e) {
      _error = _mapFirebaseError(e.code);
    }

    _isLoading = false;
    notifyListeners();
  }

  Future<void> signUp({
    required String email,
    required String password,
    required String name,
    String? gender,
    double? heightCm,
    double? weightKg,
    String? workoutGoal,
  }) async {
    _isLoading = true;
    _error = null;
    notifyListeners();

    try {
      await _authService.signUpAndSaveData(
        email: email.trim(),
        password: password,
        name: name,
        age: 0,
        weight: weightKg,
        height: heightCm,
        gender: gender,
        goal: workoutGoal,
      );

      final user = _auth.currentUser!;
      await user.updateDisplayName(name);

      final initials = name.isNotEmpty ? name[0].toUpperCase() : 'U';
      _currentUser = UserModel(
        id: user.uid,
        username: email.trim(),
        name: name,
        email: email.trim(),
        password: '',
        avatarInitials: initials,
        age: 0,
        heightCm: heightCm ?? 0,
        weightKg: weightKg ?? 0,
        gender: gender,
        workoutGoal: workoutGoal,
        joinedAt: DateTime.now(),
      );
      _error = null;
    } on FirebaseAuthException catch (e) {
      _error = _mapFirebaseError(e.code);
    } catch (e) {
      _error = 'unknown_error';
    }

    _isLoading = false;
    notifyListeners();
  }

  Future<void> updateProfile(UserModel updated) async {
    await _auth.currentUser?.updateDisplayName(updated.name);
    _currentUser = updated;
    notifyListeners();
  }

  Future<void> logout() async {
    await _auth.signOut();
    _currentUser = null;
    _error = null;
    notifyListeners();
  }

  void clearError() {
    _error = null;
    notifyListeners();
  }

  String _mapFirebaseError(String code) {
    switch (code) {
      case 'email-already-in-use':
        return 'username_already_exists';
      case 'user-not-found':
      case 'wrong-password':
      case 'invalid-credential':
        return 'username_or_password_incorrect';
      case 'weak-password':
        return 'password_too_weak';
      case 'invalid-email':
        return 'invalid_email';
      default:
        return 'unknown_error';
    }
  }
}

final authNotifierProvider = ChangeNotifierProvider<AuthNotifier>(
  (ref) => AuthNotifier(),
);

final autoLoginProvider = StateProvider<bool>((ref) => false);