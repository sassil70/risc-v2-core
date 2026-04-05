import 'dart:async';
import 'dart:io';
import 'package:flutter/foundation.dart';
import 'package:archive/archive.dart';
import 'package:path_provider/path_provider.dart';
import '../../services/api_service.dart';

/// Background Sync Service for Evidence Upload
/// - Scans local evidence folders every 30 seconds
/// - Zips and uploads each context folder individually
/// - Tracks what has been synced to avoid re-uploads
/// - Works offline: queues locally until network returns
class SyncService {
  static final SyncService _instance = SyncService._internal();
  factory SyncService() => _instance;
  SyncService._internal();

  Timer? _syncTimer;
  bool _isSyncing = false;
  final ApiService _api = ApiService();

  // Track synced contexts to avoid re-uploads: "sessionId/roomId/contextName:fingerprint"
  final Set<String> _syncedContexts = {};

  // Callback for UI updates (e.g., refresh FloorPlanHub)
  VoidCallback? onSyncComplete;

  /// Start the background sync timer (call once when entering inspection)
  void startAutoSync({VoidCallback? onComplete}) {
    onSyncComplete = onComplete;
    _syncTimer?.cancel();
    _syncTimer = Timer.periodic(const Duration(seconds: 30), (_) => syncAll());
    debugPrint("[SyncService] Auto-sync started (every 30s)");
  }

  /// Stop the background sync timer
  void stopAutoSync() {
    _syncTimer?.cancel();
    _syncTimer = null;
    debugPrint("[SyncService] Auto-sync stopped");
  }

  /// Force immediate sync (called by cloud button)
  Future<void> forceSync() async {
    debugPrint("[SyncService] Force sync triggered by user");
    await syncAll();
  }

  /// Scan all local evidence and upload any new/changed contexts
  Future<void> syncAll() async {
    if (_isSyncing) {
      debugPrint("[SyncService] Sync already in progress, skipping");
      return;
    }
    _isSyncing = true;

    try {
      final dir = await getApplicationDocumentsDirectory();
      final inspectionsDir = Directory('${dir.path}/Inspections');

      if (!await inspectionsDir.exists()) {
        _isSyncing = false;
        return;
      }

      // Walk: Inspections/{sessionId}/{roomId}/Context_{name}/
      final sessionDirs = inspectionsDir.listSync().whereType<Directory>();

      int uploadCount = 0;
      for (var sessionDir in sessionDirs) {
        final sessionId = sessionDir.path.split(Platform.pathSeparator).last;
        final roomDirs = sessionDir.listSync().whereType<Directory>();

        for (var roomDir in roomDirs) {
          final roomId = roomDir.path.split(Platform.pathSeparator).last;

          // Skip zip files or temp files
          if (roomId.contains('.zip')) continue;

          final contextDirs = roomDir.listSync().whereType<Directory>();

          for (var contextDir in contextDirs) {
            final contextName =
                contextDir.path.split(Platform.pathSeparator).last;
            if (!contextName.startsWith('Context_')) continue;

            // Check if this context has new files since last sync
            final syncKey = '$sessionId/$roomId/$contextName';
            final files = contextDir.listSync().whereType<File>().toList();

            if (files.isEmpty) continue;

            // Build a fingerprint based on file count + latest modification
            final latestMod = files
                .map((f) => f.lastModifiedSync().millisecondsSinceEpoch)
                .reduce((a, b) => a > b ? a : b);
            final fingerprint = '${files.length}_$latestMod';
            final fullKey = '$syncKey:$fingerprint';

            if (_syncedContexts.contains(fullKey)) continue;

            // New content! Upload this context
            try {
              final success = await _uploadContext(
                sessionId,
                roomId,
                contextDir,
                files,
              );
              if (success) {
                _syncedContexts.add(fullKey);
                uploadCount++;
                debugPrint(
                    "[SyncService] Synced: $syncKey (${files.length} files)");
              }
            } catch (e) {
              debugPrint("[SyncService] Failed: $syncKey - $e");
            }
          }
        }
      }

      if (uploadCount > 0) {
        debugPrint(
            "[SyncService] Sync complete: $uploadCount contexts uploaded");
        onSyncComplete?.call();
      }
    } catch (e) {
      debugPrint("[SyncService] Sync error: $e");
    } finally {
      _isSyncing = false;
    }
  }

  /// Upload a single context folder as a zip within the room structure
  Future<bool> _uploadContext(
    String sessionId,
    String roomId,
    Directory contextDir,
    List<File> files,
  ) async {
    try {
      final dir = await getApplicationDocumentsDirectory();
      final contextName = contextDir.path.split(Platform.pathSeparator).last;
      final zipPath =
          '${dir.path}/Inspections/$sessionId/${roomId}_${contextName}_sync.zip';

      // Build archive SYNCHRONOUSLY to avoid the async addFile bug
      final archive = Archive();
      for (var file in files) {
        final fileName = file.path.split(Platform.pathSeparator).last;
        final bytes = file.readAsBytesSync();
        final archiveFile = ArchiveFile(
          '$contextName/$fileName',
          bytes.length,
          bytes,
        );
        archive.addFile(archiveFile);
      }

      // Write the zip synchronously
      final zipData = ZipEncoder().encode(archive);
      File(zipPath).writeAsBytesSync(zipData);
      debugPrint(
          "[SyncService] ZIP created: ${zipData.length} bytes, ${files.length} files");

      // Upload using the existing room evidence endpoint
      final success = await _api.uploadRoomEvidence(
        sessionId,
        roomId,
        File(zipPath),
      );

      // Clean up temp zip
      try {
        File(zipPath).deleteSync();
      } catch (_) {}

      return success;
    } catch (e) {
      debugPrint("[SyncService] Upload error: $e");
      return false;
    }
  }
}
