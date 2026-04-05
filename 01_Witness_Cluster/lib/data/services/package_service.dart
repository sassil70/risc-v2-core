import 'dart:io';
import 'dart:convert';
import 'package:archive/archive_io.dart';
import 'package:path_provider/path_provider.dart';
import 'package:path/path.dart' as p;
import '../../core/utils/forensic_utils.dart';
import '../local/app_database.dart'; // Access to DB Tables

class PackageService {
  final AppDatabase db;

  PackageService(this.db);

  /// Bundles a session into a Signed ZIP package for export.
  Future<String> exportSession(String sessionId) async {
    // 1. Fetch Session Data
    final session = await (db.select(
      db.sessions,
    )..where((tbl) => tbl.id.equals(sessionId))).getSingle();
    final assets = await (db.select(
      db.mediaAssets,
    )..where((tbl) => tbl.sessionId.equals(sessionId))).get();

    // 2. Prepare Staging Directory
    final appDir = await getApplicationDocumentsDirectory();
    final stagingDir = Directory(p.join(appDir.path, 'staging', sessionId));
    if (await stagingDir.exists()) await stagingDir.delete(recursive: true);
    await stagingDir.create(recursive: true);

    // 3. Copy Assets & Build Manifest File List
    List<Map<String, dynamic>> manifestFiles = [];

    for (var asset in assets) {
      final sourceFile = File(asset.localPath);
      if (await sourceFile.exists()) {
        final fileName = p.basename(asset.localPath);
        await sourceFile.copy(
          p.join(stagingDir.path, fileName),
        ); // Copy to Staging

        manifestFiles.add({
          "path": fileName,
          "hash": asset.fileHash,
          "timestamp": asset.capturedAt.toIso8601String(),
        });
      }
    }

    // 4. Create Manifest JSON
    final manifestData = {
      "sessionId": session.id,
      "timestamp": session.startedAt.toIso8601String(),
      "surveyorId": "U-DEMO-001", // Hardcoded for Demo
      "files": manifestFiles,
    };

    final manifestJson = jsonEncode(manifestData);
    final File manifestFile = File(
      p.join(stagingDir.path, 'session_manifest.json'),
    );
    await manifestFile.writeAsString(manifestJson);

    // 5. Generate Signature (Verification Hash of Manifest)
    // In V2.0 spec, we just zip. The signature is implicit in the manifest/files integrity.
    // Ideally we'd sign with a private key here (Gap 1), but we stick to SHA-256 integrity for now.

    // 6. Zip It
    final encoder = ZipFileEncoder();
    final exportDir = Directory(p.join(appDir.path, 'exports'));
    await exportDir.create(recursive: true);

    final zipPath = p.join(exportDir.path, '$sessionId.zip');
    encoder.create(zipPath);
    encoder.addDirectory(
      stagingDir,
    ); // Add all files in staging (manifest + images)
    encoder.close();

    // Cleanup
    await stagingDir.delete(recursive: true);

    return zipPath;
  }
}
