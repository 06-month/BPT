import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../models/user_model.dart';

// Overridden in main.dart with the pre-initialized instance.
final sharedPreferencesProvider = Provider<SharedPreferences>(
  (_) => throw UnimplementedError('SharedPreferences not initialized'),
);

final localStorageServiceProvider = Provider<LocalStorageService>((ref) {
  return LocalStorageService(ref.watch(sharedPreferencesProvider));
});

class LocalStorageService {
  final SharedPreferences _prefs;

  static const _keyUser = 'bpt_user';
  static const _keyAutoLogin = 'bpt_auto_login';

  LocalStorageService(this._prefs);

  // ── User ──────────────────────────────────────────────────────────────────
  Future<void> saveUser(UserModel user) async {
    await _prefs.setString(_keyUser, user.toJsonString());
  }

  UserModel? loadUser() {
    final raw = _prefs.getString(_keyUser);
    if (raw == null) return null;
    try {
      return UserModel.fromJsonString(raw);
    } catch (_) {
      return null;
    }
  }

  Future<void> removeUser() async {
    await _prefs.remove(_keyUser);
  }

  // ── Auto-login ────────────────────────────────────────────────────────────
  Future<void> saveAutoLogin(bool value) async {
    await _prefs.setBool(_keyAutoLogin, value);
  }

  bool loadAutoLogin() => _prefs.getBool(_keyAutoLogin) ?? false;

  // ── Session ───────────────────────────────────────────────────────────────
  /// Clears auto-login flag only (keeps user record for next login).
  Future<void> clearSession() async {
    await _prefs.setBool(_keyAutoLogin, false);
  }

  /// Clears everything (full sign-out + delete account).
  Future<void> clearAll() async {
    await _prefs.remove(_keyUser);
    await _prefs.setBool(_keyAutoLogin, false);
  }
}
