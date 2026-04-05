import 'dart:io';
import 'package:camera/camera.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:path_provider/path_provider.dart';
import 'package:path/path.dart' as p;
import 'package:drift/drift.dart' as drift; // Alias for Value

// Internal Imports
// Internal Imports (Fixed Relative Paths)
import '../../../main.dart'; // Access global 'cameras'
import '../../../core/providers.dart';
import '../../../core/utils/forensic_utils.dart';
import '../../../data/local/app_database.dart';
import '../../../data/services/package_service.dart';
import '../../../core/services/sync_service.dart';

class CameraScreen extends ConsumerStatefulWidget {
  const CameraScreen({super.key});

  @override
  ConsumerState<CameraScreen> createState() => _CameraScreenState();
}

class _CameraScreenState extends ConsumerState<CameraScreen> {
  CameraController? _controller;
  bool _isCameraInitialized = false;
  bool _isRearCamera = true; // [NEW] Track camera state
  String _lastCapturedHash = "None"; // Debug UI
  String _activeSessionId = "SESSION_INIT"; // Placeholder for real session logic

  @override
  void initState() {
    super.initState();
    _initCamera();
    _createSession();
  }
  
  Future<void> _createSession() async {
     // For demo purposes, we usually create a session on startup or rely on existing
     // This creates a fresh session record in DB to link images to.
     final db = ref.read(databaseProvider);
     
     // Check if we have any session, if not create one
     final sessions = await db.select(db.sessions).get();
     if (sessions.isEmpty) {
        final id = await db.into(db.sessions).insertReturning(
           SessionsCompanion(
             startedAt: drift.Value(DateTime.now().toUtc()),
           )
        );
        setState(() {
           _activeSessionId = id.id;
        });
     } else {
        setState(() {
           _activeSessionId = sessions.last.id;
        });
     }
  }

  Future<void> _initCamera() async {
    if (cameras.isEmpty) return;
    
    // Dispose of the old controller if it exists
    await _controller?.dispose();

    // Select camera based on _isRearCamera
    final CameraDescription camera = _isRearCamera
        ? cameras.firstWhere((c) => c.lensDirection == CameraLensDirection.back, orElse: () => cameras.first)
        : cameras.firstWhere((c) => c.lensDirection == CameraLensDirection.front, orElse: () => cameras.first);

    _controller = CameraController(
      camera,
      ResolutionPreset.high,
      enableAudio: false,
    );

    try {
      await _controller!.initialize();
      if (mounted) {
        setState(() {
          _isCameraInitialized = true;
        });
      }
    } catch (e) {
      print("Camera init error: $e");
      if (mounted) {
        setState(() {
          _isCameraInitialized = false;
        });
      }
    }
  }

  void _switchCamera() {
    if (cameras.length < 2) {
      // No other camera available to switch to
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Only one camera available.')),
      );
      return;
    }
    setState(() {
      _isCameraInitialized = false; // Indicate camera is re-initializing
      _isRearCamera = !_isRearCamera;
    });
    _initCamera();
  }
  
  Future<void> _captureAndSecure() async {
    if (!_isCameraInitialized || _controller == null) return;
    if (_controller!.value.isTakingPicture) return;

    try {
      // 1. Capture
      final XFile imageFile = await _controller!.takePicture();
      final File rawFile = File(imageFile.path);

      // 2. Move to Persistent Storage
      final appDir = await getApplicationDocumentsDirectory();
      final fileName = p.basename(rawFile.path);
      final savedPath = p.join(appDir.path, fileName);
      final File secureFile = await rawFile.copy(savedPath);

      // 3. Forensic Hashing
      final hash = await ForensicUtils.calculateFileHash(secureFile);
      
      // 4. DB Insert
      final db = ref.read(databaseProvider);
      
      await db.into(db.mediaAssets).insert(
        MediaAssetsCompanion(
           sessionId: drift.Value(_activeSessionId),
           localPath: drift.Value(secureFile.path),
           assetType: const drift.Value('image'),
           fileHash: drift.Value(hash),
           capturedAt: drift.Value(DateTime.now().toUtc()), 
        )
      );

      setState(() {
        _lastCapturedHash = hash;
      });

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Secured: ${hash.substring(0, 8)}...')),
      );

    } catch (e) {
      print("Capture Error: $e");
    }
  }

  @override
  void dispose() {
    _controller?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (!_isCameraInitialized) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }

    return Scaffold(
      appBar: AppBar(
        title: const Text('Witness V2 - Forensic Cam'),
        actions: [
          IconButton(
            icon: const Icon(Icons.cloud_upload),
            tooltip: "Upload All Evidence",
            onPressed: _performFullSync,
          )
        ],
      ),
      body: Column(
        children: [
           Expanded(
             child: CameraPreview(_controller!),
           ),
           Container(
             color: Colors.black87,
             padding: const EdgeInsets.all(16),
             child: Column(
               children: [
                 Text('Session: ${_activeSessionId.substring(0,8)}', 
                      style: const TextStyle(color: Colors.white70)),
                 const SizedBox(height: 5),
                 Text('Last Hash: ${_lastCapturedHash.substring(0, min(20, _lastCapturedHash.length))}', 
                      style: const TextStyle(color: Colors.greenAccent, fontFamily: 'Courier')),
                 const SizedBox(height: 20),
                 ElevatedButton.icon(
                   onPressed: _captureAndSecure, 
                   icon: const Icon(Icons.shield, size: 30), 
                   label: const Text("CAPTURE & SIGN"),
                   style: ElevatedButton.styleFrom(
                     padding: const EdgeInsets.symmetric(horizontal: 40, vertical: 15),
                     backgroundColor: Colors.blueGrey,
                     foregroundColor: Colors.white,
                   ),
                 ),

                 const SizedBox(height: 15),
                 // SYNC DISABLED BY USER REQUEST - OFFLINE FORENSIC MODE ONLY
               ],
             ),
           )
        ],
      ),
    );
  }
  
  int min(int a, int b) => a < b ? a : b;

  Future<void> _performFullSync() async {
    // Blocking Loading Dialog to prevent multi-press
    showDialog(
      context: context, 
      barrierDismissible: false,
      builder: (ctx) => const Center(child: CircularProgressIndicator())
    );

    try {
      final db = ref.read(databaseProvider);
      
      // 1. Export Current Session
      // This creates a ZIP for the current work, adding it to the 'exports' queue.
      final packageService = PackageService(db); 
      final currentZipPath = await packageService.exportSession(_activeSessionId);
      final exportDir = p.dirname(currentZipPath);

      // 2. Upload EVERYTHING in the exports folder
      // This handles the current zip AND any old stuck zips.
      final syncService = SyncService();
      await syncService.uploadPendingPackages(exportDir, isManualOverride: true);

      // 3. Success
      if (mounted) {
        Navigator.pop(context); // Close Loader
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            backgroundColor: Colors.green, 
            content: Text('✅ All Evidence Synced Successfully!')
          ),
        );
      }

    } catch (e) {
      // 4. Error
      if (mounted) {
         Navigator.pop(context); // Close Loader
         ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            backgroundColor: Colors.red, 
            content: Text('❌ Sync Error: $e')
          ),
        );
      }
    }
  }
}
