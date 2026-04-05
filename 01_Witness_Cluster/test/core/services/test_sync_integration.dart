import 'dart:io';
import 'package:flutter_test/flutter_test.dart';
import 'package:witness_v2/core/services/sync_service.dart';
import 'package:archive/archive_io.dart';

// INTEG TEST: Requires Real Backend at 127.0.0.1:8001
void main() {
  group('SyncService Real Integration', () {
    late SyncService syncService;
    late Directory tempDir;

    setUp(() async {
      syncService = SyncService();
      tempDir = await Directory.systemTemp.createTemp('sync_test');
    });

    tearDown(() async {
      if (await tempDir.exists()) {
        await tempDir.delete(recursive: true);
      }
    });

    test('uploadRoomEvidence should return true on 200 OK', () async {
      // 1. Create Valid Dummy Zip
      final zipFile = File('${tempDir.path}/test_evidence.zip');

      final archive = Archive();
      archive.addFile(ArchiveFile('test.txt', 12, 'Hello World'.codeUnits));
      final encoder = ZipEncoder();
      final bytes = encoder.encode(archive);
      if (bytes == null) fail("Failed to create zip");

      await zipFile.writeAsBytes(bytes);

      // 2. Upload
      final success = await syncService.uploadRoomEvidence(
        'TEST_SESSION_INTEG',
        'ROOM_INTEG',
        zipFile,
      );

      // 3. Assert
      expect(
        success,
        isTrue,
        reason: "Backend should be reachable and accept upload",
      );
    });
  });
}
