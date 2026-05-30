import 'dart:convert';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:cloud_firestore/cloud_firestore.dart';

import '../models/user_model.dart';
import '../models/workout_record_model.dart';

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
  static const _keyRecords = 'bpt_workout_records';

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

  // ── Workout Records ───────────────────────────────────────────────────────
  Future<void> saveRecords(List<WorkoutRecordModel> records) async {
    final encoded = jsonEncode(records.map((r) => r.toJson()).toList());
    await _prefs.setString(_keyRecords, encoded);
  }

  List<WorkoutRecordModel> loadRecords() {
    final raw = _prefs.getString(_keyRecords);
    if (raw == null) return [];
    try {
      final list = jsonDecode(raw) as List;
      return list
          .map((e) => WorkoutRecordModel.fromJson(e as Map<String, dynamic>))
          .toList();
    } catch (_) {
      return [];
    }
  }

  Future<void> addRecord(WorkoutRecordModel record) async {
    final existing = loadRecords();
    existing.insert(0, record); // newest first
    await saveRecords(existing);

    // Firestore 동기화 백업 추가
    try {
      final user = FirebaseAuth.instance.currentUser;
      if (user != null) {
        await FirebaseFirestore.instance.collection('workouts').add({
          ...record.toJson(),
          'uid': user.uid,
          'timestamp': FieldValue.serverTimestamp(),
        });
      }
    } catch (_) {
      // 로컬 저장은 완료되었으므로 네트워크 불안정 등으로 인한 백업 실패 시 오류가 UI에 영향을 주지 않게 함
    }
  }

  // ── Session ───────────────────────────────────────────────────────────────
  Future<void> clearSession() async {
    await _prefs.setBool(_keyAutoLogin, false);
  }

  Future<void> clearAll() async {
    await _prefs.remove(_keyUser);
    await _prefs.setBool(_keyAutoLogin, false);
  }
}
