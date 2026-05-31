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

  Future<UserModel> _loadUserModel(User user) async {
    final doc = await FirebaseFirestore.instance
        .collection('users')
        .doc(user.uid)
        .get();
    if (doc.exists && doc.data() != null) {
      final data = doc.data()!;
      return UserModel.fromJson({...data, 'id': user.uid});
    }
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
    try {
      _currentUser = await _loadUserModel(user);
    } catch (_) {
      final initials = (user.displayName?.isNotEmpty == true)
          ? user.displayName![0].toUpperCase()
          : 'U';
      _currentUser = UserModel(
        id: user.uid,
        username: user.email ?? '',
        name: user.displayName ?? '',
        email: user.email ?? '',
        password: '',
        avatarInitials: initials,
        joinedAt: DateTime.now(),
      );
    }
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
      try {
        _currentUser = await _loadUserModel(credential.user!);
      } catch (_) {
        final u = credential.user!;
        final initials = (u.displayName?.isNotEmpty == true)
            ? u.displayName![0].toUpperCase()
            : 'U';
        _currentUser = UserModel(
          id: u.uid,
          username: u.email ?? '',
          name: u.displayName ?? '',
          email: u.email ?? '',
          password: '',
          avatarInitials: initials,
          joinedAt: DateTime.now(),
        );
      }
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

      // Firestore에서 실제 저장된 데이터를 읽어 단일 소스로 통일
      _currentUser = await _loadUserModel(user);
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