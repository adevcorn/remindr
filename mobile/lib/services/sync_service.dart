"""Sync service for offline queue processing."""
import 'dart:async';
import 'package:connectivity_plus/connectivity_plus.dart';
import 'local_database.dart';
import 'api_service.dart';
import '../models/capture.dart';
import '../models/draft.dart';

class SyncService {
  final LocalDatabase _localDb;
  final ApiService _apiService;
  final Connectivity _connectivity = Connectivity();
  
  StreamSubscription<ConnectivityResult>? _connectivitySubscription;
  Timer? _syncTimer;
  bool _isSyncing = false;

  SyncService(this._localDb, this._apiService);

  void startAutoSync() {
    // Monitor connectivity changes
    _connectivitySubscription = _connectivity.onConnectivityChanged.listen((result) {
      if (result != ConnectivityResult.none) {
        syncPendingItems();
      }
    });

    // Periodic sync every 30 seconds
    _syncTimer = Timer.periodic(const Duration(seconds: 30), (_) {
      syncPendingItems();
    });
  }

  void stopAutoSync() {
    _connectivitySubscription?.cancel();
    _syncTimer?.cancel();
  }

  Future<void> syncPendingItems() async {
    if (_isSyncing) return;
    
    _isSyncing = true;
    
    try {
      // Check connectivity
      final isOnline = await _apiService.checkHealth();
      if (!isOnline) return;

      // Sync pending captures
      await _syncPendingCaptures();

      // Sync pending drafts
      await _syncPendingDrafts();
    } finally {
      _isSyncing = false;
    }
  }

  Future<void> _syncPendingCaptures() async {
    final pendingCaptures = await _localDb.getPendingCaptures();

    for (final capture in pendingCaptures) {
      try {
        final synced = await _apiService.createCapture(capture);
        
        // Update local record with synced data
        await _localDb.updateCapture(synced);
      } catch (e) {
        // Log error but continue with other captures
        print('Failed to sync capture ${capture.id}: $e');
        
        // Update retry count
        final updated = Capture(
          id: capture.id,
          userId: capture.userId,
          captureType: capture.captureType,
          state: CaptureState.error,
          rawText: capture.rawText,
          errorMessage: e.toString(),
          retryCount: capture.retryCount + 1,
          createdAt: capture.createdAt,
        );
        await _localDb.updateCapture(updated);
      }
    }
  }

  Future<void> _syncPendingDrafts() async {
    final pendingDrafts = await _localDb.getPendingDrafts();

    for (final draft in pendingDrafts) {
      try {
        // Confirm the draft via API (triggers sync to Google)
        final synced = await _apiService.confirmDraft(
          draftId: draft.id!,
          title: draft.title,
          description: draft.description,
          dueDate: draft.dueDate,
          priority: draft.priority,
        );
        
        // Update local record
        await _localDb.updateDraft(synced);
      } catch (e) {
        print('Failed to sync draft ${draft.id}: $e');
      }
    }
  }

  void dispose() {
    stopAutoSync();
  }
}
