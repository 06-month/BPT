import 'dart:async';
import 'dart:convert';

import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../core/network/api_client.dart';
import '../data/dto/workout_metadata_dto.dart';
import 'local_storage_service.dart';

/// Sync Status State for Riverpod UI feedback
class SyncState {
  final bool isSyncing;
  final int pendingCount;
  final String? lastSyncError;
  final DateTime? lastSyncedAt;

  const SyncState({
    this.isSyncing = false,
    this.pendingCount = 0,
    this.lastSyncError,
    this.lastSyncedAt,
  });

  SyncState copyWith({
    bool? isSyncing,
    int? pendingCount,
    String? lastSyncError,
    DateTime? lastSyncedAt,
  }) {
    return SyncState(
      isSyncing: isSyncing ?? this.isSyncing,
      pendingCount: pendingCount ?? this.pendingCount,
      lastSyncError: lastSyncError,
      lastSyncedAt: lastSyncedAt ?? this.lastSyncedAt,
    );
  }
}

/// Offline Pending Queue Storage using SharedPreferences
class SyncQueueStorage {
  final SharedPreferences _prefs;
  static const String _queueKey = 'bpt_pending_workout_sync_queue';

  SyncQueueStorage(this._prefs);

  List<WorkoutMetadataRequestDto> getQueue() {
    final raw = _prefs.getString(_queueKey);
    if (raw == null || raw.isEmpty) return [];
    try {
      final List list = jsonDecode(raw);
      return list
          .map((item) => WorkoutMetadataRequestDto.fromJson(item as Map<String, dynamic>))
          .toList();
    } catch (_) {
      return [];
    }
  }

  Future<void> enqueue(WorkoutMetadataRequestDto dto) async {
    final queue = getQueue();
    // Avoid duplicate client IDs in queue
    queue.removeWhere((item) => item.clientRecordId == dto.clientRecordId);
    queue.add(dto);
    await _saveQueue(queue);
  }

  Future<void> remove(String clientRecordId) async {
    final queue = getQueue();
    queue.removeWhere((item) => item.clientRecordId == clientRecordId);
    await _saveQueue(queue);
  }

  Future<void> clear() async {
    await _prefs.remove(_queueKey);
  }

  Future<void> _saveQueue(List<WorkoutMetadataRequestDto> queue) async {
    final jsonList = queue.map((e) => e.toJson()).toList();
    await _prefs.setString(_queueKey, jsonEncode(jsonList));
  }
}

final syncQueueStorageProvider = Provider<SyncQueueStorage>((ref) {
  return SyncQueueStorage(ref.watch(sharedPreferencesProvider));
});

/// Offline-First Synchronization Engine
class WorkoutSyncNotifier extends StateNotifier<AsyncValue<SyncState>> {
  final ApiClient _apiClient;
  final SyncQueueStorage _queueStorage;
  final LocalStorageService _localStorage;
  final Connectivity _connectivity;

  StreamSubscription<List<ConnectivityResult>>? _connectivitySubscription;

  WorkoutSyncNotifier(
    this._apiClient,
    this._queueStorage,
    this._localStorage,
    this._connectivity,
  ) : super(const AsyncValue.data(SyncState())) {
    _initConnectivityListener();
    _updatePendingCount();
  }

  void _initConnectivityListener() {
    _connectivitySubscription = _connectivity.onConnectivityChanged.listen((results) {
      final isOnline = results.any((r) => r != ConnectivityResult.none);
      if (isOnline) {
        // Trigger auto-sync when network connectivity is restored
        syncPendingRecords();
      }
    });
  }

  void _updatePendingCount() {
    final count = _queueStorage.getQueue().length;
    final current = state.value ?? const SyncState();
    state = AsyncValue.data(current.copyWith(pendingCount: count));
  }

  /// Adds an un-synced workout record to offline queue
  Future<void> queueOfflineRecord(WorkoutMetadataRequestDto dto) async {
    await _queueStorage.enqueue(dto);
    _updatePendingCount();
  }

  /// Batch or Sequential Sync logic: Drains queue to Spring Boot backend
  Future<bool> syncPendingRecords() async {
    final currentQueue = _queueStorage.getQueue();
    if (currentQueue.isEmpty) {
      _updatePendingCount();
      return true;
    }

    final currentState = state.value ?? const SyncState();
    state = AsyncValue.data(currentState.copyWith(isSyncing: true, lastSyncError: null));

    String? lastError;

    for (final dto in List<WorkoutMetadataRequestDto>.from(currentQueue)) {
      try {
        final response = await _apiClient.post(
          '/workouts/records/sync',
          data: dto.toJson(),
        );

        if (response.statusCode == 200 || response.statusCode == 201) {
          final resDto = WorkoutMetadataResponseDto.fromJson(response.data as Map<String, dynamic>);
          
          // Remove successfully uploaded item from queue
          await _queueStorage.remove(dto.clientRecordId);
          
          // Mark local record as synced
          _markLocalRecordSynced(dto.clientRecordId, resDto.serverRecordId);
        }
      } catch (e) {
        lastError = e.toString();
        // Break on network error to try later when connection improves
        break;
      }
    }

    _updatePendingCount();
    final updatedQueueCount = _queueStorage.getQueue().length;
    
    state = AsyncValue.data(
      SyncState(
        isSyncing: false,
        pendingCount: updatedQueueCount,
        lastSyncError: updatedQueueCount > 0 ? (lastError ?? 'Partial sync failed') : null,
        lastSyncedAt: DateTime.now(),
      ),
    );

    return updatedQueueCount == 0;
  }

  void _markLocalRecordSynced(String clientRecordId, String serverRecordId) {
    final records = _localStorage.loadRecords();
    final index = records.indexWhere((r) => r.id == clientRecordId);
    if (index != -1) {
      final updated = records[index].copyWith(
        isSynced: true,
        serverId: serverRecordId,
      );
      records[index] = updated;
      _localStorage.saveRecords(records);
    }
  }

  @override
  void dispose() {
    _connectivitySubscription?.cancel();
    super.dispose();
  }
}

final workoutSyncProvider =
    StateNotifierProvider<WorkoutSyncNotifier, AsyncValue<SyncState>>((ref) {
  return WorkoutSyncNotifier(
    ref.watch(apiClientProvider),
    ref.watch(syncQueueStorageProvider),
    ref.watch(localStorageServiceProvider),
    Connectivity(),
  );
});
