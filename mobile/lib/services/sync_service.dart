// Sync service for offline queue processing with parallel sync optimization
import 'dart:async';
import 'package:connectivity_plus/connectivity_plus.dart';
import 'local_database.dart';
import 'api_service.dart';
import '../models/capture.dart';
import '../models/draft.dart';

/// Result of a sync operation for tracking progress
class SyncResult {
  final int total;
  final int successful;
  final int failed;
  final List<String> errors;
  final Duration duration;

  SyncResult({
    required this.total,
    required this.successful,
    required this.failed,
    required this.errors,
    required this.duration,
  });

  @override
  String toString() => 
      'SyncResult(total: $total, successful: $successful, failed: $failed, duration: ${duration.inMilliseconds}ms)';
}

/// Progress callback for UI updates
typedef SyncProgressCallback = void Function(int completed, int total);

class SyncService {
  final LocalDatabase _localDb;
  final ApiService _apiService;
  final Connectivity _connectivity = Connectivity();
  
  StreamSubscription<ConnectivityResult>? _connectivitySubscription;
  Timer? _syncTimer;
  bool _isSyncing = false;
  
  // Concurrency control: maximum parallel API requests
  static const int _maxConcurrentRequests = 5;
  
  // Progress tracking
  SyncProgressCallback? onSyncProgress;
  final _syncResultController = StreamController<SyncResult>.broadcast();
  Stream<SyncResult> get syncResults => _syncResultController.stream;

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

  /// Main sync entry point - now with parallel execution
  Future<SyncResult> syncPendingItems() async {
    if (_isSyncing) {
      return SyncResult(
        total: 0,
        successful: 0,
        failed: 0,
        errors: ['Sync already in progress'],
        duration: Duration.zero,
      );
    }
    
    _isSyncing = true;
    final startTime = DateTime.now();
    int totalItems = 0;
    int successfulItems = 0;
    int failedItems = 0;
    final errors = <String>[];
    
    try {
      // Check connectivity
      final isOnline = await _apiService.checkHealth();
      if (!isOnline) {
        return SyncResult(
          total: 0,
          successful: 0,
          failed: 0,
          errors: ['Service is offline'],
          duration: DateTime.now().difference(startTime),
        );
      }

      // Fetch all pending items in parallel (batch database reads)
      final results = await Future.wait([
        _localDb.getPendingCaptures(),
        _localDb.getPendingDrafts(),
      ]);
      
      final pendingCaptures = results[0] as List<Capture>;
      final pendingDrafts = results[1] as List<Draft>;
      totalItems = pendingCaptures.length + pendingDrafts.length;

      if (totalItems == 0) {
        return SyncResult(
          total: 0,
          successful: 0,
          failed: 0,
          errors: [],
          duration: DateTime.now().difference(startTime),
        );
      }

      print('Starting parallel sync: $totalItems items (${pendingCaptures.length} captures, ${pendingDrafts.length} drafts)');

      // Sync captures and drafts in parallel
      final syncResults = await Future.wait([
        _syncPendingCapturesParallel(pendingCaptures),
        _syncPendingDraftsParallel(pendingDrafts),
      ]);

      // Aggregate results
      for (final result in syncResults) {
        successfulItems += result.successful;
        failedItems += result.failed;
        errors.addAll(result.errors);
      }

      final duration = DateTime.now().difference(startTime);
      final finalResult = SyncResult(
        total: totalItems,
        successful: successfulItems,
        failed: failedItems,
        errors: errors,
        duration: duration,
      );

      print('Sync completed: $finalResult');
      _syncResultController.add(finalResult);
      
      return finalResult;
    } finally {
      _isSyncing = false;
    }
  }

  /// Sync captures in parallel with chunked processing
  Future<SyncResult> _syncPendingCapturesParallel(List<Capture> captures) async {
    if (captures.isEmpty) {
      return SyncResult(
        total: 0,
        successful: 0,
        failed: 0,
        errors: [],
        duration: Duration.zero,
      );
    }

    final startTime = DateTime.now();
    final errors = <String>[];
    final successfulCaptures = <Capture>[];
    final failedCaptures = <Capture>[];

    // Process in chunks to limit concurrent requests
    for (var i = 0; i < captures.length; i += _maxConcurrentRequests) {
      final chunk = captures.skip(i).take(_maxConcurrentRequests).toList();
      
      // Execute chunk in parallel
      final chunkResults = await Future.wait(
        chunk.map((capture) => _syncSingleCapture(capture)),
      );

      // Collect results
      for (var j = 0; j < chunkResults.length; j++) {
        final result = chunkResults[j];
        if (result['success'] == true) {
          successfulCaptures.add(result['capture'] as Capture);
        } else {
          failedCaptures.add(result['capture'] as Capture);
          errors.add('Capture ${result['capture'].id}: ${result['error']}');
        }
        
        // Progress callback
        onSyncProgress?.call(i + j + 1, captures.length);
      }
    }

    // Batch update successful captures
    if (successfulCaptures.isNotEmpty) {
      await _localDb.batchUpdateCaptures(successfulCaptures);
    }

    // Batch update failed captures with error state
    if (failedCaptures.isNotEmpty) {
      await _localDb.batchUpdateCaptures(failedCaptures);
    }

    return SyncResult(
      total: captures.length,
      successful: successfulCaptures.length,
      failed: failedCaptures.length,
      errors: errors,
      duration: DateTime.now().difference(startTime),
    );
  }

  /// Sync a single capture and return result map
  Future<Map<String, dynamic>> _syncSingleCapture(Capture capture) async {
    try {
      final synced = await _apiService.createCapture(capture);
      return {
        'success': true,
        'capture': synced,
      };
    } catch (e) {
      print('Failed to sync capture ${capture.id}: $e');
      
      // Return updated capture with error state
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
      
      return {
        'success': false,
        'capture': updated,
        'error': e.toString(),
      };
    }
  }

  /// Sync drafts in parallel with chunked processing
  Future<SyncResult> _syncPendingDraftsParallel(List<Draft> drafts) async {
    if (drafts.isEmpty) {
      return SyncResult(
        total: 0,
        successful: 0,
        failed: 0,
        errors: [],
        duration: Duration.zero,
      );
    }

    final startTime = DateTime.now();
    final errors = <String>[];
    final successfulDrafts = <Draft>[];
    final failedDrafts = <Draft>[];

    // Process in chunks to limit concurrent requests
    for (var i = 0; i < drafts.length; i += _maxConcurrentRequests) {
      final chunk = drafts.skip(i).take(_maxConcurrentRequests).toList();
      
      // Execute chunk in parallel
      final chunkResults = await Future.wait(
        chunk.map((draft) => _syncSingleDraft(draft)),
      );

      // Collect results
      for (var j = 0; j < chunkResults.length; j++) {
        final result = chunkResults[j];
        if (result['success'] == true) {
          successfulDrafts.add(result['draft'] as Draft);
        } else {
          failedDrafts.add(result['draft'] as Draft);
          errors.add('Draft ${result['draft'].id}: ${result['error']}');
        }
        
        // Progress callback
        onSyncProgress?.call(i + j + 1, drafts.length);
      }
    }

    // Batch update successful drafts
    if (successfulDrafts.isNotEmpty) {
      await _localDb.batchUpdateDrafts(successfulDrafts);
    }

    // Batch update failed drafts with error state
    if (failedDrafts.isNotEmpty) {
      await _localDb.batchUpdateDrafts(failedDrafts);
    }

    return SyncResult(
      total: drafts.length,
      successful: successfulDrafts.length,
      failed: failedDrafts.length,
      errors: errors,
      duration: DateTime.now().difference(startTime),
    );
  }

  /// Sync a single draft and return result map
  Future<Map<String, dynamic>> _syncSingleDraft(Draft draft) async {
    try {
      final synced = await _apiService.confirmDraft(
        draftId: draft.id!,
        title: draft.title,
        description: draft.description,
        dueDate: draft.dueDate,
        priority: draft.priority,
      );
      
      return {
        'success': true,
        'draft': synced,
      };
    } catch (e) {
      print('Failed to sync draft ${draft.id}: $e');
      
      // Return draft with error state
      final updated = Draft(
        id: draft.id,
        captureId: draft.captureId,
        userId: draft.userId,
        draftType: draft.draftType,
        aiConfidence: draft.aiConfidence,
        title: draft.title,
        description: draft.description,
        dueDate: draft.dueDate,
        priority: draft.priority,
        location: draft.location,
        startTime: draft.startTime,
        endTime: draft.endTime,
        isConfirmed: draft.isConfirmed,
        googleTaskId: draft.googleTaskId,
        googleEventId: draft.googleEventId,
        syncState: 'error',
        extractedEntities: draft.extractedEntities,
        createdAt: draft.createdAt,
        updatedAt: DateTime.now(),
      );
      
      return {
        'success': false,
        'draft': updated,
        'error': e.toString(),
      };
    }
  }

  void dispose() {
    stopAutoSync();
    _syncResultController.close();
  }
}
