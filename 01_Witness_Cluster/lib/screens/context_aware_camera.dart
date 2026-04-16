import 'dart:io';
import 'package:flutter/material.dart';
import 'package:camera/camera.dart';
import 'package:path_provider/path_provider.dart';
import 'dart:async';
import 'dart:convert';
import 'package:flutter/services.dart' show HapticFeedback, rootBundle;
import 'package:permission_handler/permission_handler.dart';
import 'package:google_fonts/google_fonts.dart';

import '../core/services/timeline_service.dart';
import '../core/services/hardware_service.dart';
import '../core/services/sync_service.dart';
import '../services/api_service.dart';

class ContextAwareCameraScreen extends StatefulWidget {
  final String sessionId;
  final String roomId;
  final String roomName;
  final String roomType;
  final String? projectId;
  final List<String>? contexts;

  const ContextAwareCameraScreen({
    super.key,
    required this.sessionId,
    required this.roomId,
    required this.roomName,
    required this.roomType,
    this.projectId,
    this.contexts,
  });

  @override
  State<ContextAwareCameraScreen> createState() =>
      _ContextAwareCameraScreenState();
}

class _ContextAwareCameraScreenState extends State<ContextAwareCameraScreen>
    with WidgetsBindingObserver {
  final ApiService _api = ApiService();
  CameraController? _cameraController;
  final HardwareService _hardware = HardwareService();
  bool _isUploading = false;

  // === PHASE CONTROL ===
  bool _showDashboard = true; // true = dashboard, false = camera
  bool _isLoadingContexts = true;
  List<Map<String, dynamic>> _serverContexts = [];
  int _totalPhotos = 0;
  int _totalAudio = 0;
  bool _hasPartialReport = false;

  // RICS Data
  final Map<String, List<String>> _ricsMatrix = {};
  List<String> _currentRoomContexts = [];

  // Logic State
  String? _activeContext;
  String? _currentContextPath;
  bool _isRecording = false;

  // Evidence Tracking
  int _photosTakenInContext = 0;
  int _serverPhotoCountForContext = 0;
  List<String> _currentContextPhotos = [];
  Set<String> _excludedPhotos = {};
  final Map<String, bool> _completedContexts = {};

  // Timer
  Timer? _contextTimer;
  int _elapsedContextSeconds = 0;
  static const int maxContextSeconds = 120;

  // Visuals
  bool _showRedFlash = false;
  double _zoomLevel = 1.0;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    TimelineService().enterRoom();
    _loadServerContexts();
    _loadRICSMatrix();
    SyncService().startAutoSync();
  }

  Future<void> _loadServerContexts() async {
    if (widget.projectId == null) {
      setState(() => _isLoadingContexts = false);
      return;
    }
    try {
      final data =
          await _api.getRoomContexts(widget.projectId!, widget.roomId);
      if (data != null && mounted) {
        setState(() {
          _serverContexts =
              List<Map<String, dynamic>>.from(data['contexts'] ?? []);
          _excludedPhotos = Set<String>.from(
              List<String>.from(data['excluded_photos'] ?? []));
          _totalPhotos = data['total_photos'] ?? 0;
          _totalAudio = data['total_audio'] ?? 0;
          _hasPartialReport = data['has_partial_report'] ?? false;
          _isLoadingContexts = false;

          // Pre-populate completedContexts from server data
          for (var ctx in _serverContexts) {
            if (ctx['is_green'] == true) {
              _completedContexts[ctx['name']] = true;
            }
          }
        });
      } else {
        if (mounted) setState(() => _isLoadingContexts = false);
      }
    } catch (e) {
      if (mounted) setState(() => _isLoadingContexts = false);
    }
  }

  Future<void> _loadRICSMatrix() async {
    if (widget.contexts != null && widget.contexts!.isNotEmpty) {
      setState(() => _currentRoomContexts = widget.contexts!);
      return;
    }
    try {
      final jsonStr = await rootBundle.loadString('assets/rics_contexts.json');
      final Map<String, dynamic> data = jsonDecode(jsonStr);
      setState(() {
        data.forEach((k, v) => _ricsMatrix[k] = List<String>.from(v));
        String type = widget.roomType.toLowerCase();
        if (type.contains('kitchen')) {
          type = 'kitchen';
        } else if (type.contains('bath') ||
            type.contains('ensuite') ||
            type.contains('wc'))
          type = 'wet_room';
        else if (type.contains('bed') ||
            type.contains('living') ||
            type.contains('lounge') ||
            type.contains('dining'))
          type = 'general';
        else if (type.contains('garage')) type = 'external';
        _currentRoomContexts =
            _ricsMatrix[type] ?? _ricsMatrix['general'] ?? [];
      });
    } catch (e) {
      print("Error loading RICS Matrix: $e");
    }
  }

  Future<void> _initCamera() async {
    try {
      _cameraController = await _hardware.initCamera();
      if (!mounted) return;
      setState(() {});
    } catch (e) {
      print("Camera Init Error: $e");
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text("Camera Error: $e")));
      }
    }
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _hardware.dispose();
    _contextTimer?.cancel();
    super.dispose();
  }

  // ============== DASHBOARD ACTIONS =================

  void _enterCameraForContext(String contextName) async {
    if (_cameraController == null) {
      await _initCamera();
    }
    // Get server photo count for this context
    final serverCtx = _serverContexts.firstWhere(
      (c) => c['name'] == contextName,
      orElse: () => {'photo_count': 0},
    );
    setState(() {
      _showDashboard = false;
      _serverPhotoCountForContext = serverCtx['photo_count'] as int? ?? 0;
    });
    await _startContext(contextName);
  }

  void _returnToDashboard() async {
    if (_activeContext != null) {
      await _stopContext();
    }
    setState(() => _showDashboard = true);
    _loadServerContexts(); // Refresh counts
  }

  // Report generation removed from inspection screen — moved to Reports tab in FloorPlanHub

  // ============== CAMERA LOGIC ENGINE =================

  Future<void> _archiveAndUpload() async {
    if (_isRecording) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text("Stop current recording first!")),
      );
      return;
    }
    setState(() => _isUploading = true);
    try {
      await SyncService().forceSync();
      if (mounted) {
        setState(() => _isUploading = false);
        _returnToDashboard();
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text("Sync Error: $e"), backgroundColor: Colors.red),
        );
        setState(() => _isUploading = false);
      }
    }
  }

  void _triggerVisualAlarm() {
    setState(() => _showRedFlash = true);
    Future.delayed(const Duration(milliseconds: 300), () {
      if (mounted) setState(() => _showRedFlash = false);
    });
  }

  Future<void> _toggleContext(String contextName) async {
    if (_activeContext == contextName) {
      await _stopContext();
      return;
    }
    if (_activeContext != null) {
      await _stopContext(moveNext: true);
    }
    await _startContext(contextName);
  }

  Future<void> _startContext(String contextName) async {
    if (await Permission.microphone.request().isDenied) return;

    final dir = await getApplicationDocumentsDirectory();
    final safeName = contextName.replaceAll(RegExp(r'[^a-zA-Z0-9]'), '_');
    final contextPath =
        '${dir.path}/Inspections/${widget.sessionId}/${widget.roomId}/Context_$safeName';
    await Directory(contextPath).create(recursive: true);

    final existingFiles = Directory(contextPath)
        .listSync()
        .whereType<File>()
        .where((f) => f.path.endsWith('.jpg'))
        .map((f) => f.path)
        .toList();

    final audioPath =
        '$contextPath/audio_${DateTime.now().millisecondsSinceEpoch}.m4a';
    await _hardware.startRecording(audioPath);
    TimelineService().startSession(contextName, audioPath);

    setState(() {
      _activeContext = contextName;
      _currentContextPath = contextPath;
      _isRecording = true;
      _photosTakenInContext = existingFiles.length;
      _currentContextPhotos = existingFiles;
      _elapsedContextSeconds = 0;
    });

    _contextTimer = Timer.periodic(const Duration(seconds: 1), (timer) {
      setState(() => _elapsedContextSeconds++);
      if (_elapsedContextSeconds >= maxContextSeconds) {
        _stopContext(forced: true);
      }
    });
  }

  Future<void> _stopContext({bool forced = false, bool moveNext = false}) async {
    if (_activeContext == null) return;

    if (!forced && _currentContextPhotos.length < 3) {
      ScaffoldMessenger.of(context).removeCurrentSnackBar();
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text("Note: '$_activeContext' needs 3 photos for Green status."),
          backgroundColor: Colors.orange,
          duration: const Duration(seconds: 1),
        ),
      );
    }

    await _hardware.stopRecording();
    _contextTimer?.cancel();

    if (_currentContextPath != null) {
      await TimelineService().endSessionAndSave(
        _currentContextPath!,
        _elapsedContextSeconds,
      );
    }

    final completedContext = _activeContext!;
    setState(() {
      _isRecording = false;
      _activeContext = null;
      if (_currentContextPhotos.length >= 3) {
        _completedContexts[completedContext] = true;
      }
    });

    if (forced) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text("Time Limit Reached. Context Saved."),
          backgroundColor: Colors.orange,
        ),
      );
    }
  }

  Future<void> _takePhoto() async {
    if (_activeContext == null) {
      _triggerVisualAlarm();
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text("Select a Context first!"),
          duration: Duration(seconds: 1),
        ),
      );
      return;
    }

    try {
      final xFile = await _cameraController!.takePicture();
      final dir = await getApplicationDocumentsDirectory();
      final safeName = _activeContext!.replaceAll(RegExp(r'[^a-zA-Z0-9]'), '_');
      final contextPath =
          '${dir.path}/Inspections/${widget.sessionId}/${widget.roomId}/Context_$safeName';
      final timestamp = DateTime.now().millisecondsSinceEpoch;
      final newPath = '$contextPath/img_$timestamp.jpg';
      await File(xFile.path).copy(newPath);
      TimelineService().logPhoto(newPath);

      setState(() {
        _currentContextPhotos.add(newPath);
        _photosTakenInContext++;
      });
      SyncService().syncAll();
    } catch (e) {
      print("Photo Error: $e");
    }
  }

  // ============== UI: CONTEXT DASHBOARD =================

  Widget _buildDashboard() {
    const gold = Color(0xFFFFD700);
    const bg = Color(0xFF0A0E1A);

    if (_isLoadingContexts) {
      return Scaffold(
        backgroundColor: bg,
        body: Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const CircularProgressIndicator(color: gold),
              const SizedBox(height: 16),
              Text('Loading evidence...',
                  style: GoogleFonts.spaceMono(color: Colors.white54)),
            ],
          ),
        ),
      );
    }

    // Merge server contexts with RICS matrix contexts
    final allContextNames = <String>{};
    for (var c in _serverContexts) {
      allContextNames.add(c['name'] as String);
    }
    for (var c in _currentRoomContexts) {
      allContextNames.add(c);
    }
    final contextNames = allContextNames.toList();

    // Build context cards with server data
    final contextCards = contextNames.map((name) {
      final serverCtx = _serverContexts.firstWhere(
        (c) => c['name'] == name,
        orElse: () => {
          'name': name,
          'photo_count': 0,
          'audio_count': 0,
          'is_green': false,
          'status': 'pending',
          'photo_urls': [],
          'audio_urls': [],
          'audio_duration': 0,
        },
      );
      return serverCtx;
    }).toList();

    // Sort: pending first → in_progress → completed
    final statusOrder = {'pending': 0, 'in_progress': 1, 'completed': 2};
    contextCards.sort((a, b) =>
        (statusOrder[a['status']] ?? 99)
            .compareTo(statusOrder[b['status']] ?? 99));

    final greenCount = contextCards.where((c) => c['is_green'] == true).length;

    return Scaffold(
      backgroundColor: bg,
      body: SafeArea(
        child: Column(
          children: [
            // === TOP BAR ===
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
              child: Row(
                children: [
                  IconButton(
                    icon: const Icon(Icons.arrow_back_ios,
                        color: Colors.white54, size: 20),
                    onPressed: () => Navigator.pop(context),
                  ),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.center,
                      children: [
                        Text(
                          widget.roomName,
                          style: GoogleFonts.outfit(
                            color: Colors.white,
                            fontSize: 16,
                            fontWeight: FontWeight.bold,
                          ),
                          overflow: TextOverflow.ellipsis,
                        ),
                        const SizedBox(height: 2),
                        Text(
                          'INSPECTION DASHBOARD',
                          style: GoogleFonts.spaceMono(
                            color: gold,
                            fontSize: 9,
                            letterSpacing: 2,
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(width: 40),
                ],
              ),
            ),

            // === STATS HEADER ===
            Container(
              margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
              decoration: BoxDecoration(
                color: Colors.white.withOpacity(0.04),
                borderRadius: BorderRadius.circular(14),
                border: Border.all(color: gold.withOpacity(0.15)),
              ),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceAround,
                children: [
                  _statBadge(Icons.camera_alt, '$_totalPhotos', 'Photos',
                      const Color(0xFF00E5FF)),
                  _statBadge(Icons.mic, '$_totalAudio', 'Audio',
                      const Color(0xFFE040FB)),
                  _statBadge(Icons.check_circle, '$greenCount/${contextCards.length}',
                      'Complete', const Color(0xFF00E676)),
                ],
              ),
            ),

            const SizedBox(height: 8),

            // === CONTEXT CARDS ===
            Expanded(
              child: ListView.builder(
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
                itemCount: contextCards.length,
                itemBuilder: (ctx, i) {
                  final c = contextCards[i];
                  return _buildContextCard(c);
                },
              ),
            ),

            // === BOTTOM ACTION BAR ===
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: bg,
                border: Border(
                    top: BorderSide(color: Colors.white.withOpacity(0.05))),
              ),
              child: Padding(
                padding: const EdgeInsets.symmetric(
                    horizontal: 16, vertical: 12),
                child: Row(
                  children: [
                    // Sync Button (full width now — generate moved to Reports tab)
                    Expanded(
                      child: OutlinedButton.icon(
                        onPressed: _isUploading ? null : _archiveAndUpload,
                        icon: _isUploading
                            ? const SizedBox(
                                width: 16, height: 16,
                                child: CircularProgressIndicator(
                                  strokeWidth: 2, color: Colors.white))
                            : const Icon(Icons.cloud_upload, size: 18),
                        label: Text(
                          _isUploading ? 'SYNCING...' : 'SYNC ALL EVIDENCE',
                          style: GoogleFonts.spaceMono(fontSize: 10),
                        ),
                        style: OutlinedButton.styleFrom(
                          foregroundColor: Colors.white70,
                          side: const BorderSide(color: Colors.white24),
                          padding: const EdgeInsets.symmetric(vertical: 14),
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _statBadge(IconData icon, String value, String label, Color color) {
    return Column(
      children: [
        Icon(icon, color: color, size: 20),
        const SizedBox(height: 4),
        Text(value,
            style: GoogleFonts.spaceMono(
              color: Colors.white, fontSize: 16, fontWeight: FontWeight.bold)),
        Text(label,
            style: GoogleFonts.spaceMono(color: Colors.white38, fontSize: 8)),
      ],
    );
  }

  void _togglePhotoExclude(String filename) async {
    if (widget.projectId == null) return;
    
    // Immediate local toggle for instant feedback
    setState(() {
      if (_excludedPhotos.contains(filename)) {
        _excludedPhotos.remove(filename);
      } else {
        _excludedPhotos.add(filename);
      }
    });
    
    final isNowExcluded = _excludedPhotos.contains(filename);
    
    // Haptic feedback
    HapticFeedback.mediumImpact();
    
    // Show snackbar
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            isNowExcluded
                ? '⛔ Photo excluded from report'
                : '✅ Photo re-included in report',
            style: GoogleFonts.spaceMono(fontSize: 11),
          ),
          backgroundColor: isNowExcluded ? Colors.redAccent : Colors.green,
          duration: const Duration(seconds: 1),
        ),
      );
    }
    
    // API call in background
    await ApiService().togglePhotoExclude(
      widget.projectId!,
      widget.roomId,
      filename,
    );
  }

  Widget _buildContextCard(Map<String, dynamic> ctx) {
    final name = ctx['name'] as String;
    final photoCount = ctx['photo_count'] as int? ?? 0;
    final audioCount = ctx['audio_count'] as int? ?? 0;
    final status = ctx['status'] as String? ?? 'pending';
    final photoUrls = List<String>.from(ctx['photo_urls'] ?? []);
    final audioDuration = ctx['audio_duration'] as int? ?? 0;

    Color statusColor;
    IconData statusIcon;
    String statusLabel;

    switch (status) {
      case 'completed':
        statusColor = const Color(0xFF00E676);
        statusIcon = Icons.check_circle;
        statusLabel = 'COMPLETE';
        break;
      case 'in_progress':
        statusColor = const Color(0xFFFFD700);
        statusIcon = Icons.timelapse;
        statusLabel = 'IN PROGRESS';
        break;
      default:
        statusColor = const Color(0xFFFF5252);
        statusIcon = Icons.radio_button_unchecked;
        statusLabel = 'NOT STARTED';
    }

    final baseUrl = ApiService.baseUrl.replaceAll('/api', '');

    return GestureDetector(
      onTap: () => _enterCameraForContext(name),
      child: Container(
        margin: const EdgeInsets.only(bottom: 10),
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: statusColor.withOpacity(0.06),
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: statusColor.withOpacity(0.2)),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header Row
            Row(
              children: [
                Icon(statusIcon, color: statusColor, size: 20),
                const SizedBox(width: 10),
                Expanded(
                  child: Text(
                    name,
                    style: GoogleFonts.outfit(
                      color: Colors.white,
                      fontSize: 15,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                  decoration: BoxDecoration(
                    color: statusColor.withOpacity(0.15),
                    borderRadius: BorderRadius.circular(6),
                  ),
                  child: Text(
                    statusLabel,
                    style: GoogleFonts.spaceMono(
                      color: statusColor,
                      fontSize: 8,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
              ],
            ),

            const SizedBox(height: 10),

            // Stats Row
            Row(
              children: [
                Icon(Icons.camera_alt,
                    color: photoCount >= 3
                        ? const Color(0xFF00E676)
                        : Colors.white38,
                    size: 14),
                const SizedBox(width: 4),
                Text(
                  '$photoCount photos',
                  style: GoogleFonts.spaceMono(
                    color: photoCount >= 3
                        ? const Color(0xFF00E676)
                        : Colors.white54,
                    fontSize: 10,
                  ),
                ),
                const SizedBox(width: 16),
                Icon(Icons.mic,
                    color: audioCount >= 1
                        ? const Color(0xFFE040FB)
                        : Colors.white38,
                    size: 14),
                const SizedBox(width: 4),
                Text(
                  audioCount > 0 ? '${audioDuration}s audio' : 'No audio',
                  style: GoogleFonts.spaceMono(
                    color: audioCount >= 1
                        ? const Color(0xFFE040FB)
                        : Colors.white54,
                    fontSize: 10,
                  ),
                ),
                const Spacer(),
                Icon(Icons.camera, color: statusColor.withOpacity(0.6), size: 16),
                const SizedBox(width: 4),
                Text(
                  'TAP TO INSPECT',
                  style: GoogleFonts.spaceMono(
                    color: statusColor.withOpacity(0.6),
                    fontSize: 8,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ],
            ),

            // Photo Thumbnails
            if (photoUrls.isNotEmpty) ...[
              const SizedBox(height: 10),
              SizedBox(
                height: 56,
                child: ListView.builder(
                  scrollDirection: Axis.horizontal,
                  itemCount: photoUrls.length,
                  itemBuilder: (ctx, i) {
                    final url = '$baseUrl${photoUrls[i]}';
                    final filename = Uri.parse(photoUrls[i]).pathSegments.last;
                    final isExcluded = _excludedPhotos.contains(filename);
                    return GestureDetector(
                      onLongPress: () => _togglePhotoExclude(filename),
                      child: Stack(
                        children: [
                          Container(
                            width: 56,
                            height: 56,
                            margin: const EdgeInsets.only(right: 6),
                            decoration: BoxDecoration(
                              borderRadius: BorderRadius.circular(8),
                              border: Border.all(
                                  color: isExcluded
                                      ? Colors.red.withOpacity(0.6)
                                      : statusColor.withOpacity(0.3),
                                  width: isExcluded ? 2 : 1),
                            ),
                            child: Opacity(
                              opacity: isExcluded ? 0.3 : 1.0,
                              child: ClipRRect(
                                borderRadius: BorderRadius.circular(7),
                                child: Image.network(
                                  url,
                                  fit: BoxFit.cover,
                                  errorBuilder: (_, __, ___) => Container(
                                    color: Colors.white10,
                                    child: const Icon(Icons.broken_image,
                                        color: Colors.white24, size: 20),
                                  ),
                                ),
                              ),
                            ),
                          ),
                          if (isExcluded)
                            Positioned.fill(
                              child: Container(
                                margin: const EdgeInsets.only(right: 6),
                                decoration: BoxDecoration(
                                  borderRadius: BorderRadius.circular(8),
                                  color: Colors.red.withOpacity(0.15),
                                ),
                                child: const Center(
                                  child: Icon(Icons.close,
                                      color: Colors.redAccent, size: 28),
                                ),
                              ),
                            ),
                        ],
                      ),
                    );
                  },
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  // ============== UI: CAMERA VIEW =================

  Widget _buildCameraView() {
    if (_cameraController == null || !_cameraController!.value.isInitialized) {
      return const Scaffold(
        backgroundColor: Colors.black,
        body: Center(child: CircularProgressIndicator()),
      );
    }

    return Scaffold(
      backgroundColor: Colors.black,
      body: Stack(
        children: [
          // 1. Camera Feed
          Positioned.fill(child: CameraPreview(_cameraController!)),

          // 2. Visual Alarm Overlay
          if (_showRedFlash)
            Positioned.fill(
              child: Container(color: Colors.red.withOpacity(0.5)),
            ),

          // 3. Top Info Bar
          SafeArea(
            child: Align(
              alignment: Alignment.topCenter,
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                color: Colors.black54,
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    // Back to Dashboard
                    IconButton(
                      icon: const Icon(Icons.dashboard, color: Colors.white),
                      onPressed: _returnToDashboard,
                      tooltip: "Back to Dashboard",
                    ),
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.center,
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(
                          widget.roomName,
                          style: const TextStyle(
                            color: Colors.white, fontWeight: FontWeight.bold),
                        ),
                        Text(
                          _activeContext == null
                              ? "Select Context ▼"
                              : "Recording: $_activeContext",
                          style: TextStyle(
                            color: _activeContext == null
                                ? Colors.grey
                                : Colors.redAccent,
                          ),
                        ),
                      ],
                    ),
                    if (_activeContext != null)
                      Text(
                        "${_elapsedContextSeconds}s / ${maxContextSeconds}s",
                        style: const TextStyle(
                          color: Colors.white,
                          fontFeatures: [FontFeature.tabularFigures()],
                        ),
                      )
                    else
                      // Sync & Return
                      IconButton(
                        icon: const Icon(Icons.cloud_upload, color: Colors.white),
                        onPressed: _archiveAndUpload,
                        tooltip: "Sync & Return",
                      ),
                  ],
                ),
              ),
            ),
          ),

          // 4. Right Side Ribbon (Contexts)
          Positioned(
            right: 0,
            top: 100,
            bottom: 150,
            width: 80,
            child: Container(
              decoration: BoxDecoration(
                color: Colors.black.withOpacity(0.6),
                borderRadius: const BorderRadius.only(
                  topLeft: Radius.circular(20),
                  bottomLeft: Radius.circular(20),
                ),
              ),
              child: ListView.builder(
                itemCount: _currentRoomContexts.length,
                itemBuilder: (ctx, i) {
                  final contextName = _currentRoomContexts[i];
                  final isActive = _activeContext == contextName;
                  final isComplete = _completedContexts[contextName] == true;

                  return GestureDetector(
                    onTap: () => _toggleContext(contextName),
                    child: Container(
                      margin: const EdgeInsets.symmetric(
                          vertical: 8, horizontal: 8),
                      padding: const EdgeInsets.symmetric(vertical: 12),
                      decoration: BoxDecoration(
                        color: isActive
                            ? Colors.blueAccent
                            : (isComplete
                                ? Colors.green.withOpacity(0.8)
                                : Colors.red.withOpacity(0.4)),
                        border: Border.all(
                          color: isActive ? Colors.white : Colors.white10),
                        borderRadius: BorderRadius.circular(10),
                      ),
                      child: Column(
                        children: [
                          Icon(
                            isComplete
                                ? Icons.check
                                : (isActive ? Icons.mic : Icons.circle_outlined),
                            color: Colors.white, size: 20),
                          const SizedBox(height: 4),
                          Text(
                            contextName,
                            textAlign: TextAlign.center,
                            style: const TextStyle(
                              color: Colors.white, fontSize: 9),
                          ),
                        ],
                      ),
                    ),
                  );
                },
              ),
            ),
          ),

          // 5. Bottom Control Area
          SafeArea(
            top: false,
            child: Align(
              alignment: Alignment.bottomCenter,
              child: Container(
                padding: const EdgeInsets.only(bottom: 8),
                color: Colors.black54,
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    if (_activeContext != null)
                      Padding(
                        padding: const EdgeInsets.only(bottom: 10, top: 10),
                        child: Text(
                          _serverPhotoCountForContext > 0
                              ? "Photos: ${_serverPhotoCountForContext + _currentContextPhotos.length} ($_serverPhotoCountForContext synced + ${_currentContextPhotos.length} new)"
                              : "Photos: ${_currentContextPhotos.length} / 3 Required",
                          style: TextStyle(
                            color: (_serverPhotoCountForContext + _currentContextPhotos.length) >= 3
                                ? Colors.greenAccent
                                : Colors.orangeAccent),
                        ),
                      ),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                      children: [
                        IconButton(
                          onPressed: () {
                            setState(() =>
                                _zoomLevel = (_zoomLevel - 1.0).clamp(1.0, 8.0));
                            _cameraController?.setZoomLevel(_zoomLevel);
                          },
                          icon: const Icon(Icons.zoom_out, color: Colors.white),
                        ),
                        GestureDetector(
                          onTapDown: (_) {
                            HapticFeedback.lightImpact();
                            _takePhoto();
                          },
                          child: Container(
                            width: 70, height: 70,
                            decoration: BoxDecoration(
                              shape: BoxShape.circle,
                              border: Border.all(color: Colors.white, width: 4),
                              color: _activeContext == null
                                  ? Colors.grey
                                  : Colors.white,
                            ),
                          ),
                        ),
                        IconButton(
                          onPressed: () {
                            setState(() =>
                                _zoomLevel = (_zoomLevel + 1.0).clamp(1.0, 8.0));
                            _cameraController?.setZoomLevel(_zoomLevel);
                          },
                          icon: const Icon(Icons.zoom_in, color: Colors.white),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ),
          ),

          // 6. Loading Overlay
          if (_isUploading)
            Positioned.fill(
              child: Container(
                color: Colors.black.withOpacity(0.7),
                child: const Center(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      CircularProgressIndicator(),
                      SizedBox(height: 20),
                      Text("Uploading Room Evidence...",
                          style: TextStyle(color: Colors.white)),
                    ],
                  ),
                ),
              ),
            ),
        ],
      ),
    );
  }

  // ============== MAIN BUILD =================

  @override
  Widget build(BuildContext context) {
    if (_showDashboard) {
      return _buildDashboard();
    } else {
      return _buildCameraView();
    }
  }
}
