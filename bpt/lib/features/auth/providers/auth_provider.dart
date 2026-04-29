import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../models/user_model.dart';
import '../../../services/local_storage_service.dart';

final themeModeProvider = StateProvider<ThemeMode>((ref) => ThemeMode.system);

// ── Auth ───────────────────────────────────────────────────────────────────
class AuthNotifier extends ChangeNotifier {
  final LocalStorageService _storage;

  AuthNotifier(this._storage);

  UserModel? _currentUser;
  bool _isLoading = false;
  String? _error;

  UserModel? get currentUser => _currentUser;
  bool get isLoggedIn => _currentUser != null;
  bool get isLoading => _isLoading;
  String? get error => _error;

  /// Called by SplashScreen: restore session if auto-login was saved.
  Future<bool> tryAutoLogin() async {
    if (!_storage.loadAutoLogin()) return false;
    final user = _storage.loadUser();
    if (user == null) return false;
    _currentUser = user;
    notifyListeners();
    return true;
  }

  Future<void> login(String username, String password,
      {bool rememberMe = false}) async {
    _isLoading = true;
    _error = null;
    notifyListeners();

    final stored = _storage.loadUser();
    if (stored != null &&
        stored.username == username &&
        stored.password == password) {
      _currentUser = stored;
      if (rememberMe) {
        await _storage.saveAutoLogin(true);
      } else {
        await _storage.clearSession();
      }
      _error = null;
    } else {
      _error = 'username_or_password_incorrect';
    }

    _isLoading = false;
    notifyListeners();
  }

  Future<void> signUp({
    required String username,
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

    final existing = _storage.loadUser();
    if (existing != null && existing.username == username) {
      _error = 'username_already_exists';
      _isLoading = false;
      notifyListeners();
      return;
    }

    final initials = name.isNotEmpty ? name[0].toUpperCase() : 'U';
    final newUser = UserModel(
      id: DateTime.now().millisecondsSinceEpoch.toString(),
      username: username,
      name: name,
      email: '',
      password: password,
      avatarInitials: initials,
      gender: gender,
      heightCm: heightCm ?? 0,
      weightKg: weightKg ?? 0,
      workoutGoal: workoutGoal,
      joinedAt: DateTime.now(),
    );

    await _storage.saveUser(newUser);
    _currentUser = newUser;
    _isLoading = false;
    notifyListeners();
  }

  Future<void> updateProfile(UserModel updated) async {
    await _storage.saveUser(updated);
    _currentUser = updated;
    notifyListeners();
  }

  Future<void> logout() async {
    await _storage.clearSession();
    _currentUser = null;
    _error = null;
    notifyListeners();
  }

  void clearError() {
    _error = null;
    notifyListeners();
  }
}

final authNotifierProvider = ChangeNotifierProvider<AuthNotifier>(
  (ref) => AuthNotifier(ref.watch(localStorageServiceProvider)),
);

final autoLoginProvider = StateProvider<bool>((ref) => false);
