import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:connectivity_plus/connectivity_plus.dart';

import '../../core/network/api_client.dart';
import '../../services/local_storage_service.dart';
import '../../services/sync_service.dart';
import '../dto/workout_metadata_dto.dart';
import '../../models/workout_record_model.dart';

abstract class IWorkoutRepository {
  Future<WorkoutRecordModel> submitWorkoutRecord(WorkoutMetadataRequestDto metadataDto);
  Future<List<WorkoutRecordModel>> getWorkoutRecords();
}

class WorkoutRepository implements IWorkoutRepository {
  final ApiClient _apiClient;
  final LocalStorageService _localStorage;
  final SyncQueueStorage _queueStorage;
  final WorkoutSyncNotifier _syncNotifier;

  WorkoutRepository(
    this._apiClient,
    this._localStorage,
    this._queueStorage,
    this._syncNotifier,
  );

  /// Submits On-Device AI metadata (Lightweight JSON with postureScore) to Spring Boot
  /// If offline or server fails, caches in local storage and queues for background sync.
  @override
  Future<WorkoutRecordModel> submitWorkoutRecord(
    WorkoutMetadataRequestDto metadataDto,
  ) async {
    // Check network status
    final connectivity = await Connectivity().checkConnectivity();
    final isOnline = connectivity.any((c) => c != ConnectivityResult.none);

    WorkoutRecordModel recordModel = WorkoutRecordModel.fromDto(
      metadataDto,
      isSynced: false,
    );

    if (isOnline) {
      try {
        // Send metadata to Spring Boot REST API
        final response = await _apiClient.post(
          '/workouts/records',
          data: metadataDto.toJson(),
        );

        if (response.statusCode == 200 || response.statusCode == 201) {
          final resDto = WorkoutMetadataResponseDto.fromJson(
            response.data as Map<String, dynamic>,
          );

          recordModel = recordModel.copyWith(
            isSynced: true,
            serverId: resDto.serverRecordId,
            postureScore: resDto.postureScore > 0 ? resDto.postureScore : metadataDto.postureScore,
          );

          // Save to local storage cache
          await _localStorage.addRecord(recordModel);
          return recordModel;
        }
      } catch (e) {
        // Network or server failure -> Fallback to Offline Queue
      }
    }

    // Offline mode or API network error: Save locally & enqueue for sync
    await _queueStorage.enqueue(metadataDto);
    await _localStorage.addRecord(recordModel);

    // Trigger background sync attempt in case network recovers
    _syncNotifier.syncPendingRecords();

    return recordModel;
  }

  /// Fetches workout records merging online Spring Boot records with offline local records
  @override
  Future<List<WorkoutRecordModel>> getWorkoutRecords() async {
    final localRecords = _localStorage.loadRecords();

    final connectivity = await Connectivity().checkConnectivity();
    final isOnline = connectivity.any((c) => c != ConnectivityResult.none);

    if (!isOnline) {
      return localRecords;
    }

    try {
      final response = await _apiClient.get('/workouts/records');
      if (response.statusCode == 200 && response.data is List) {
        final serverRecords = (response.data as List).map((json) {
          final dto = WorkoutMetadataRequestDto.fromJson(json as Map<String, dynamic>);
          final serverId = json['id']?.toString() ?? json['serverId']?.toString();
          return WorkoutRecordModel.fromDto(dto, isSynced: true, serverId: serverId);
        }).toList();

        // Merge un-synced local records with server records
        final unSyncedLocal = localRecords.where((r) => !r.isSynced).toList();
        final merged = [...unSyncedLocal, ...serverRecords];
        
        // Update local cache
        await _localStorage.saveRecords(merged);
        return merged;
      }
    } catch (_) {
      // Fallback to local storage if API call fails
    }

    return localRecords;
  }
}

final workoutRepositoryProvider = Provider<IWorkoutRepository>((ref) {
  return WorkoutRepository(
    ref.watch(apiClientProvider),
    ref.watch(localStorageServiceProvider),
    ref.watch(syncQueueStorageProvider),
    ref.watch(workoutSyncProvider.notifier),
  );
});
