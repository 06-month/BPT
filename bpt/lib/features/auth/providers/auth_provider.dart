import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

final themeModeProvider = StateProvider<ThemeMode>((ref) => ThemeMode.system);

// ── Auth ───────────────────────────────────────────────────────────────────
class AuthNotifier extends ChangeNotifier {
  bool _isLoggedIn = false;
  bool _isLoading = false;
  String? _error;

  bool get isLoggedIn => _isLoggedIn;
  bool get isLoading => _isLoading;
  String? get error => _error;

  Future<void> login(String email, String password) async {
    _isLoading = true;
    _error = null;
    notifyListeners();

    // Simulate network delay
    await Future.delayed(const Duration(milliseconds: 1200));

    if (email.isNotEmpty && password.length >= 6) {
      _isLoggedIn = true;
      _error = null;
    } else {
      _error = 'Invalid credentials. Password must be at least 6 characters.';
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

    await Future.delayed(const Duration(milliseconds: 1500));

    if (username.isNotEmpty && password.length >= 6 && name.isNotEmpty) {
      _isLoggedIn = true;
      _error = null;
    } else {
      _error = 'Please fill in all required fields correctly.';
    }

    _isLoading = false;
    notifyListeners();
  }

  void logout() {
    _isLoggedIn = false;
    _error = null;
    notifyListeners();
  }

  void clearError() {
    _error = null;
    notifyListeners();
  }
}

final authNotifierProvider = ChangeNotifierProvider<AuthNotifier>(
  (ref) => AuthNotifier(),
);
