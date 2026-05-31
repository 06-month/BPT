import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

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

  // ── 로컬 캐시 (SharedPreferences, UID별 격리) ────────────────────────────
  static String _cacheKey(String uid) => 'bpt_user_cache_$uid';

  Future<void> _cacheUser(UserModel user) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_cacheKey(user.id), user.toJsonString());
  }

  Future<UserModel?> _loadCachedUser(String uid) async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final raw = prefs.getString(_cacheKey(uid));
      if (raw == null) return null;
      return UserModel.fromJsonString(raw);
    } catch (_) {
      return null;
    }
  }

  // ── Firestore 조회 ────────────────────────────────────────────────────────
  Future<UserModel?> _loadFromFirestore(User user) async {
    try {
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
        birthDate: data['birthDate'] != null
            ? DateTime.tryParse(data['birthDate'].toString())
            : null,
        weightKg: (data['weightKg'] as num?)?.toDouble() ?? 0.0,
        heightCm: (data['heightCm'] as num?)?.toDouble() ?? 0.0,
        gender: data['gender'] as String?,
        workoutGoal: data['workoutGoal'] as String?,
        joinedAt: data['joinedAt'] != null
            ? (DateTime.tryParse(data['joinedAt'].toString()) ?? DateTime.now())
            : DateTime.now(),
      );
    } catch (_) {
      return null;
    }
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
    final fromFirestore = await _loadFromFirestore(user);
    if (fromFirestore != null) {
      _currentUser = fromFirestore;
      await _cacheUser(fromFirestore); // Firestore 최신값으로 캐시 갱신
    } else {
      _currentUser = await _loadCachedUser(user.uid) ?? _fallbackUser(user);
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
      final u = credential.user!;
      final fromFirestore = await _loadFromFirestore(u);
      if (fromFirestore != null) {
        _currentUser = fromFirestore;
        await _cacheUser(fromFirestore); // Firestore 최신값으로 캐시 갱신
      } else {
        _currentUser = await _loadCachedUser(u.uid) ?? _fallbackUser(u);
      }
      _error = null;
    } on FirebaseAuthException catch (e) {
      _error = _mapFirebaseError(e.code);
    } catch (_) {
      _error = 'unknown_error';
    }

    _isLoading = false;
    notifyListeners();
  }

  Future<void> signUp({
    required String email,
    required String password,
    required String name,
    DateTime? birthDate,
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
        birthDate: birthDate,
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
        birthDate: birthDate,
        heightCm: heightCm ?? 0,
        weightKg: weightKg ?? 0,
        gender: gender,
        workoutGoal: workoutGoal,
        joinedAt: DateTime.now(),
      );
      // 로컬 캐시에 저장 — 로그아웃 후 재로그인 시 Firestore 없이도 복원 가능
      await _cacheUser(_currentUser!);
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
    await _cacheUser(updated);
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