import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../models/user_model.dart';

final themeModeProvider = StateProvider<ThemeMode>((ref) => ThemeMode.system);

// ── Auth ───────────────────────────────────────────────────────────────────
class AuthNotifier extends ChangeNotifier {
  final FirebaseAuth _auth = FirebaseAuth.instance;

  UserModel? _currentUser;
  bool _isLoading = false;
  String? _error;

  UserModel? get currentUser => _currentUser;
  bool get isLoggedIn => _currentUser != null;
  bool get isLoading => _isLoading;
  String? get error => _error;

  /// Firebase는 세션을 자동 유지 — currentUser가 있으면 복원
  Future<bool> tryAutoLogin() async {
    final user = _auth.currentUser;
    if (user == null) return false;
    _currentUser = UserModel(
      id: user.uid,
      username: user.email ?? '',
      name: user.displayName ?? '',
      email: user.email ?? '',
      password: '',
      avatarInitials: (user.displayName?.isNotEmpty == true)
          ? user.displayName![0].toUpperCase()
          : 'U',
      joinedAt: DateTime.now(),
    );
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
      final user = credential.user!;
      _currentUser = UserModel(
        id: user.uid,
        username: user.email ?? '',
        name: user.displayName ?? '',
        email: user.email ?? '',
        password: '',
        avatarInitials: (user.displayName?.isNotEmpty == true)
            ? user.displayName![0].toUpperCase()
            : 'U',
        joinedAt: DateTime.now(),
      );
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
      final credential = await _auth.createUserWithEmailAndPassword(
        email: email.trim(),
        password: password,
      );
      final user = credential.user!;

      // Firebase Auth에 displayName 저장
      await user.updateDisplayName(name);

      final initials = name.isNotEmpty ? name[0].toUpperCase() : 'U';
      _currentUser = UserModel(
        id: user.uid,
        username: email.trim(),
        name: name,
        email: email.trim(),
        password: '',
        avatarInitials: initials,
        gender: gender,
        heightCm: heightCm ?? 0,
        weightKg: weightKg ?? 0,
        workoutGoal: workoutGoal,
        joinedAt: DateTime.now(),
      );
      _error = null;
    } on FirebaseAuthException catch (e) {
      _error = _mapFirebaseError(e.code);
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