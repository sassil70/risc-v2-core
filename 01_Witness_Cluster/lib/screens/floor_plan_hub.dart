import 'package:flutter/material.dart';
import 'dart:async';
import 'dart:io';
import 'package:glassmorphism/glassmorphism.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:flutter_animate/flutter_animate.dart';
import '../services/api_service.dart';
import '../core/services/remote_logger.dart';
import '../services/report_queue_service.dart';
import 'context_aware_camera.dart';
import 'floor_plan_recorder.dart';
import 'report_webview_screen.dart';
import 'partial_report_viewer.dart';
import 'evidence_gallery.dart';
import 'final_report_tab.dart';
import 'package:record/record.dart';
import 'package:path_provider/path_provider.dart';
import 'package:permission_handler/permission_handler.dart';

class FloorPlanHubScreen extends StatefulWidget {
  final String sessionId;
  const FloorPlanHubScreen({super.key, required this.sessionId});

  @override
  State<FloorPlanHubScreen> createState() => _FloorPlanHubScreenState();
}

class _FloorPlanHubScreenState extends State<FloorPlanHubScreen>
    with TickerProviderStateMixin {
  final ApiService _api = ApiService();
  final ReportQueueService _reportQueue = ReportQueueService();
  bool _isLoading = true;
  List<dynamic> _rooms = [];
  Map<String, dynamic>? _sessionData;
  Timer? _refreshTimer;
  late TabController _tabController;
  int _bottomNavIndex = 0; // 0 = Inspection, 1 = Reports, 2 = Final Report
  
  // Reports tab state
  String? _expandedRoomId;
  bool _isRecordingAmendment = false;
  StreamSubscription? _queueSub;

  static const int maxInspections = 3;

  /// Clean code name like 'G_Ground_Floor_Circulation' → 'Ground Floor Circulation'
  String _cleanName(String? raw) {
    if (raw == null || raw.isEmpty) return 'Room';
    String cleaned = raw.replaceFirst(RegExp(r'^[A-Z]\d?_'), '');
    cleaned = cleaned.replaceAll('_', ' ');
    cleaned = cleaned.split(' ').map((w) => w.isEmpty ? '' : '${w[0].toUpperCase()}${w.substring(1).toLowerCase()}').join(' ');
    return cleaned.trim();
  }

  @override
  void initState() {
    super.initState();
    // 4 Fixed RICS Categories: D, E, F, G
    _tabController = TabController(length: 4, vsync: this);
    _fetchStatus();
    _refreshTimer = Timer.periodic(
      const Duration(seconds: 30),
      (_) => _fetchStatus(),
    );
    // Listen to report queue updates
    _queueSub = _reportQueue.statusStream.listen((_) {
      if (mounted) setState(() {});
    });
  }

  @override
  void dispose() {
    _refreshTimer?.cancel();
    _tabController.dispose();
    _queueSub?.cancel();
    super.dispose();
  }

  Future<void> _fetchStatus() async {
    try {
      final statusRes = await _api.getStatus(sessionId: widget.sessionId);

      if (statusRes.containsKey('session') &&
          statusRes['session']?['floor_plan'] != null) {
        final roomsData = statusRes['session']['floor_plan']['rooms'] as List;

        if (mounted) {
          setState(() {
            _rooms = roomsData;
            _sessionData = statusRes['session'];
            _isLoading = false;
          });
        }
      } else {
        if (mounted)
          setState(() {
            _rooms = [];
            _isLoading = false;
          });
      }
    } catch (e) {
      if (mounted && _isLoading) setState(() => _isLoading = false);
    }
  }

  Color _getStatusColor(String status) {
    switch (status.toLowerCase()) {
      case 'green':
      case 'completed':
        return const Color(0xFF00E676);
      case 'yellow':
      case 'in_progress':
        return const Color(0xFF00E5FF);
      case 'red':
        return const Color(0xFFFF5252);
      case 'pending':
        return const Color(0xFFFFD700);
      default:
        return Colors.grey;
    }
  }

  IconData _getStatusIcon(String status) {
    switch (status.toLowerCase()) {
      case 'green':
      case 'completed':
        return Icons.verified;
      case 'yellow':
      case 'in_progress':
        return Icons.autorenew;
      case 'red':
        return Icons.error_outline;
      case 'pending':
        return Icons.radio_button_unchecked;
      default:
        return Icons.radio_button_unchecked;
    }
  }

  Future<void> _openInspection(Map<String, dynamic> room) async {
    await Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => ContextAwareCameraScreen(
          sessionId: widget.sessionId,
          roomId: room['id'],
          roomName: room['name'],
          roomType: room['type'] ?? 'general',
          projectId: _sessionData?['project_id'],
          contexts: room['contexts']?.cast<String>(),
        ),
      ),
    );
    _fetchStatus();
  }

  Future<void> _openExecutiveAddendum() async {
    await Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => ContextAwareCameraScreen(
          sessionId: widget.sessionId,
          roomId: "executive_summary",
          roomName: "Executive Global Summary",
          roomType: "executive",
          projectId: _sessionData?['project_id'],
          contexts: const [
            "Overall Opinion",
            "Urgent Structural Defects",
            "Safety Hazards",
          ],
        ),
      ),
    );
    _fetchStatus();
  }

  Future<void> _archiveSession() async {
    RemoteLogger()
        .log('INFO', 'User triggered _archiveSession() in FloorPlanHubScreen');
    final confirm = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: const Color(0xFF0F172A),
        title: Text(
          "GENERATE RICS REPORT?",
          style: GoogleFonts.outfit(color: Colors.white),
        ),
        content: Text(
          "This will finalize the RICS compliance matrix and generate the Master Synthesis. This may take up to 2 minutes as the AI synthesizes all rooms.",
          style: GoogleFonts.spaceMono(color: Colors.white70),
        ),
        actions: [
          TextButton(
            onPressed: () {
              RemoteLogger().log('WARN',
                  'User CANCELLED RICS Generation in FloorPlanHubScreen');
              Navigator.pop(ctx, false);
            },
            child: const Text(
              "CANCEL",
              style: TextStyle(color: Colors.white54),
            ),
          ),
          ElevatedButton(
            onPressed: () {
              RemoteLogger().log('INFO',
                  'User CONFIRMED RICS Generation in FloorPlanHubScreen');
              Navigator.pop(ctx, true);
            },
            style: ElevatedButton.styleFrom(
              backgroundColor: const Color(0xFFFFD700),
              foregroundColor: Colors.black,
            ),
            child: const Text(
              "GENERATE REPORT",
              style: TextStyle(fontWeight: FontWeight.bold),
            ),
          ),
        ],
      ),
    );

    if (confirm == true) {
      // Show loading overlay
      showDialog(
        context: context,
        barrierDismissible: false,
        builder: (BuildContext context) {
          return const Center(
            child: CircularProgressIndicator(color: Color(0xFFFFD700)),
          );
        },
      );

      try {
        RemoteLogger().log('INFO',
            'Initiating API call: generateFinalRicsPdf for project: ${widget.sessionId}');
        // Trigger AI Synthesis on the backend
        await _api.generateFinalRicsPdf(
          projectId: widget.sessionId,
        ); // We use sessionId as projectId in current architecture

        if (mounted) {
          RemoteLogger().log('SUCCESS',
              'API generateFinalRicsPdf completed successfully. Navigating to ReportWebViewScreen.');
          Navigator.pop(context); // Remove loading

          // Navigate to the ReportWebViewScreen showing the PDF
          Navigator.push(
            context,
            MaterialPageRoute(
              builder: (_) => ReportWebViewScreen(
                projectId: widget.sessionId,
                backendBaseUrl: ApiService.baseUrl,
              ),
            ),
          );
        }
      } catch (e) {
        RemoteLogger().log('ERROR', 'API generateFinalRicsPdf FAILED: $e');
        if (mounted) {
          Navigator.pop(context); // Remove loading
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text(
                "Failed to generate report: $e",
                style: const TextStyle(color: Colors.red),
              ),
            ),
          );
        }
      }
    }
  }

  Future<void> _startVoiceArchitect() async {
    String propertyType = 'House';
    int floors = 2;

    final result = await showDialog<Map<String, dynamic>>(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (context, setDialogState) {
          return AlertDialog(
            backgroundColor: const Color(0xFF1E1E1E),
            title: Text(
              "Initialize Architecture",
              style: GoogleFonts.outfit(color: Colors.white),
            ),
            content: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text("Type", style: const TextStyle(color: Colors.white70)),
                DropdownButton<String>(
                  value: propertyType,
                  dropdownColor: const Color(0xFF2C2C2C),
                  isExpanded: true,
                  style: const TextStyle(color: Colors.white),
                  items: ['House', 'Flat', 'Bungalow', 'Commercial']
                      .map((t) => DropdownMenuItem(value: t, child: Text(t)))
                      .toList(),
                  onChanged: (v) => setDialogState(() => propertyType = v!),
                ),
                const SizedBox(height: 20),
                Text(
                  "Floors: $floors",
                  style: const TextStyle(color: Colors.white70),
                ),
                Slider(
                  value: floors.toDouble(),
                  min: 1,
                  max: 5,
                  divisions: 4,
                  activeColor: const Color(0xFFFFD700),
                  onChanged: (v) => setDialogState(() => floors = v.toInt()),
                ),
              ],
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(ctx),
                child: const Text(
                  "CANCEL",
                  style: TextStyle(color: Colors.white54),
                ),
              ),
              ElevatedButton(
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFFFFD700),
                ),
                onPressed: () => Navigator.pop(ctx, {
                  'type': propertyType,
                  'floors': floors,
                }),
                child: const Text(
                  "VOICE ARCHITECT",
                  style: TextStyle(
                    color: Colors.black,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
            ],
          );
        },
      ),
    );

    if (result != null) {
      final String? projectId = _sessionData?['project_id'];

      if (projectId == null || projectId.isEmpty) {
        showDialog(
          context: context,
          builder: (ctx) => AlertDialog(
            backgroundColor: const Color(0xFF1E1E1E),
            title: const Text(
              "System Warning",
              style: TextStyle(color: Colors.redAccent),
            ),
            content: const Text(
              "This is a legacy 'Zombie' session lacking a Property ID connection. Please start a new active mission from the dashboard.",
              style: TextStyle(color: Colors.white70),
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(ctx),
                child: const Text(
                  "CLOSE",
                  style: TextStyle(color: Colors.white54),
                ),
              ),
            ],
          ),
        );
        return;
      }

      Navigator.push(
        context,
        MaterialPageRoute(
          builder: (_) => FloorPlanRecorder(
            sessionId: widget.sessionId,
            initialData: {
              'property_id': projectId,
              'property_type': result['type'],
              'number_of_floors': result['floors'],
            },
          ),
        ),
      ).then((_) => _fetchStatus());
    }
  }

  @override
  Widget build(BuildContext context) {
    const gold = Color(0xFFFFD700);

    return Scaffold(
      backgroundColor: const Color(0xFF0A0A14),
      body: Stack(
        children: [
          // Background gradient
          Positioned.fill(
            child: Container(
              decoration: const BoxDecoration(
                gradient: RadialGradient(
                  center: Alignment.bottomRight,
                  radius: 1.8,
                  colors: [Color(0xFF1E293B), Color(0xFF020408)],
                ),
              ),
            ),
          ),
          // Background texture
          Positioned.fill(
            child: Opacity(
              opacity: 0.03,
              child: Image.network(
                "https://www.transparenttextures.com/patterns/graphy.png",
                repeat: ImageRepeat.repeat,
              ),
            ),
          ),
          SafeArea(
            child: Column(
              children: [
                // AppBar
                Padding(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 16,
                    vertical: 8,
                  ),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      IconButton(
                        icon: const Icon(
                          Icons.arrow_back_ios,
                          color: Colors.white54,
                          size: 20,
                        ),
                        onPressed: () =>
                            Navigator.of(context).pop(),
                      ),
                      Text(
                        _bottomNavIndex == 0 ? "RICS MATRIX HUB" : _bottomNavIndex == 1 ? "REPORT CENTER" : "FINAL REPORT",
                        style: GoogleFonts.outfit(
                          color: Colors.white,
                          fontSize: 18,
                          fontWeight: FontWeight.bold,
                          letterSpacing: 2,
                        ),
                      ),
                      IconButton(
                        icon: Icon(
                          _bottomNavIndex == 0 ? Icons.picture_as_pdf : _bottomNavIndex == 1 ? Icons.refresh : Icons.auto_awesome,
                          color: gold,
                        ),
                        onPressed: _bottomNavIndex == 0 ? _archiveSession : _bottomNavIndex == 1 ? () => setState(() {}) : () {},
                      ),
                    ],
                  ),
                ),

                // Property Header
                if (_sessionData != null)
                  Padding(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 16.0,
                      vertical: 8,
                    ),
                    child: GlassmorphicContainer(
                      width: double.infinity,
                      height: 80,
                      borderRadius: 12,
                      blur: 15,
                      alignment: Alignment.center,
                      border: 1,
                      linearGradient: LinearGradient(
                        colors: [
                          Colors.white.withOpacity(0.05),
                          Colors.white.withOpacity(0.01),
                        ],
                      ),
                      borderGradient: LinearGradient(
                        colors: [
                          gold.withOpacity(0.5),
                          Colors.white.withOpacity(0.05),
                        ],
                      ),
                      child: Padding(
                        padding: const EdgeInsets.symmetric(horizontal: 20),
                        child: Row(
                          children: [
                            Container(
                              padding: const EdgeInsets.all(10),
                              decoration: BoxDecoration(
                                color: gold.withOpacity(0.1),
                                shape: BoxShape.circle,
                              ),
                              child: Icon(Icons.location_city, color: gold),
                            ),
                            const SizedBox(width: 16),
                            Expanded(
                              child: Column(
                                mainAxisAlignment: MainAxisAlignment.center,
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    _sessionData?['property']?['address']
                                            ?['full_address'] ??
                                        'UNKNOWN TARGET',
                                    style: GoogleFonts.outfit(
                                      color: Colors.white,
                                      fontWeight: FontWeight.bold,
                                    ),
                                    overflow: TextOverflow.ellipsis,
                                  ),
                                  Text(
                                    '${_rooms.length} ZONES DETECTED',
                                    style: GoogleFonts.spaceMono(
                                      color: Colors.white54,
                                      fontSize: 10,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ).animate().fadeIn().slideY(),

                if (_isLoading)
                  const Expanded(
                    child: Center(
                      child: CircularProgressIndicator(
                        color: Color(0xFFFFD700),
                      ),
                    ),
                  )
                else if (_rooms.isEmpty && _bottomNavIndex == 0)
                  Expanded(
                    child: Center(
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          const Icon(
                            Icons.mic_external_on,
                            size: 80,
                            color: Colors.white24,
                          ),
                          const SizedBox(height: 20),
                          Text(
                            "NO BLUEPRINT DATA",
                            style: GoogleFonts.spaceMono(color: Colors.white30),
                          ),
                          const SizedBox(height: 30),
                          ElevatedButton.icon(
                            onPressed: _startVoiceArchitect,
                            icon: const Icon(
                              Icons.record_voice_over,
                              color: Colors.black,
                            ),
                            label: Text(
                              "START VOICE ARCHITECT",
                              style: GoogleFonts.outfit(
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                            style: ElevatedButton.styleFrom(
                              backgroundColor: gold,
                              foregroundColor: Colors.black,
                              padding: const EdgeInsets.symmetric(
                                horizontal: 32,
                                vertical: 16,
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                  )
                else if (_bottomNavIndex == 2)
                  Expanded(
                    child: FinalReportTab(
                      sessionId: widget.sessionId,
                      projectId: _sessionData?['project_id'],
                    ),
                  )
                else if (_bottomNavIndex == 0)
                  Expanded(
                    child: Column(
                      children: [
                        // RICS Category Tab Bar
                        TabBar(
                          controller: _tabController,
                          isScrollable: true,
                          indicatorColor: gold,
                          indicatorWeight: 3,
                          labelColor: gold,
                          unselectedLabelColor: Colors.white38,
                          labelStyle: GoogleFonts.outfit(
                            fontWeight: FontWeight.bold,
                            fontSize: 12,
                          ),
                          tabs: const [
                            Tab(text: "D: EXTERIOR"),
                            Tab(text: "E: INTERIOR"),
                            Tab(text: "F: SERVICES"),
                            Tab(text: "G: GROUNDS"),
                          ],
                        ),

                        // Tab Views
                        Expanded(
                          child: TabBarView(
                            controller: _tabController,
                            children: [
                              _buildCategoryView('D'),
                              _buildCategoryView('E'),
                              _buildCategoryView('F'),
                              _buildCategoryView('G'),
                            ],
                          ),
                        ),
                      ],
                    ),
                  )
                else
                  Expanded(child: _buildReportsTab()),
              ],
            ),
          ),
        ],
      ),

      // FAB: mic for Reports (voice amendment), nothing for Inspection
      floatingActionButton: _bottomNavIndex == 1
          ? FloatingActionButton(
              backgroundColor: gold,
              foregroundColor: Colors.black,
              onPressed: _openExecutiveAddendum,
              tooltip: "Global Executive Summary",
              child: const Icon(Icons.summarize, size: 26),
            )
          : _bottomNavIndex == 2
              ? FloatingActionButton(
                  backgroundColor: const Color(0xFF4D2D69),
                  foregroundColor: Colors.white,
                  onPressed: () {},
                  tooltip: "RICS Final Report",
                  child: const Icon(Icons.picture_as_pdf, size: 26),
                )
              : null,
      bottomNavigationBar: Container(
        decoration: BoxDecoration(
          border: Border(top: BorderSide(color: gold.withOpacity(0.2))),
        ),
        child: BottomNavigationBar(
          currentIndex: _bottomNavIndex,
          onTap: (i) => setState(() => _bottomNavIndex = i),
          backgroundColor: const Color(0xFF0A0A14),
          selectedItemColor: gold,
          unselectedItemColor: Colors.white38,
          selectedLabelStyle: GoogleFonts.spaceMono(fontSize: 10, fontWeight: FontWeight.bold),
          unselectedLabelStyle: GoogleFonts.spaceMono(fontSize: 10),
          items: [
            const BottomNavigationBarItem(
              icon: Icon(Icons.search),
              activeIcon: Icon(Icons.search, size: 28),
              label: 'INSPECTION',
            ),
            BottomNavigationBarItem(
              icon: Stack(
                clipBehavior: Clip.none,
                children: [
                  const Icon(Icons.description_outlined),
                  if (_reportQueue.pendingCount + _reportQueue.processingCount > 0)
                    Positioned(
                      right: -6,
                      top: -4,
                      child: Container(
                        padding: const EdgeInsets.all(3),
                        decoration: const BoxDecoration(
                          color: Colors.redAccent,
                          shape: BoxShape.circle,
                        ),
                        child: Text(
                          '${_reportQueue.pendingCount + _reportQueue.processingCount}',
                          style: const TextStyle(color: Colors.white, fontSize: 8),
                        ),
                      ),
                    ),
                ],
              ),
              activeIcon: const Icon(Icons.description, size: 28),
              label: 'REPORTS',
            ),
            const BottomNavigationBarItem(
              icon: Icon(Icons.description_outlined, color: Color(0xFF4D2D69)),
              activeIcon: Icon(Icons.description, size: 28, color: Color(0xFF4D2D69)),
              label: 'FINAL REPORT',
            ),
          ],
        ),
      ),
    );
  }

  // ============== REPORTS TAB ==============

  Widget _buildReportsTab() {
    const gold = Color(0xFFFFD700);
    final projectId = _sessionData?['project_id'] as String?;
    final jobs = _reportQueue.jobs;
    final roomsWithData = _rooms.where((r) {
      final int imgCount = r['images_count'] ?? 0;
      final int audioCount = r['audio_count'] ?? 0;
      return imgCount > 0 || audioCount > 0;
    }).toList();

    return ListView(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      children: [
        // Queue Status Header
        if (jobs.isNotEmpty)
          Container(
            margin: const EdgeInsets.only(bottom: 16),
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: gold.withOpacity(0.08),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: gold.withOpacity(0.2)),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'REPORT QUEUE',
                  style: GoogleFonts.spaceMono(
                    color: gold, fontSize: 10, fontWeight: FontWeight.bold,
                  ),
                ),
                const SizedBox(height: 8),
                ...jobs.map((job) {
                  IconData icon;
                  Color color;
                  String statusText;
                  switch (job.status) {
                    case 'QUEUED':
                      icon = Icons.hourglass_empty;
                      color = Colors.white54;
                      statusText = 'Queued';
                      break;
                    case 'PROCESSING':
                      icon = Icons.autorenew;
                      color = gold;
                      statusText = 'Generating...';
                      break;
                    case 'COMPLETE':
                      icon = Icons.check_circle;
                      color = const Color(0xFF00E676);
                      statusText = 'Ready to view';
                      break;
                    case 'ERROR':
                      icon = Icons.error;
                      color = Colors.redAccent;
                      statusText = job.errorMessage ?? 'Failed';
                      break;
                    default:
                      icon = Icons.help;
                      color = Colors.grey;
                      statusText = job.status;
                  }
                  return Padding(
                    padding: const EdgeInsets.symmetric(vertical: 4),
                    child: Row(
                      children: [
                        Icon(icon, color: color, size: 16),
                        const SizedBox(width: 8),
                        Expanded(
                          child: Text(
                            _cleanName(job.roomName),
                            style: GoogleFonts.outfit(
                              color: Colors.white, fontSize: 12,
                            ),
                          ),
                        ),
                        Text(
                          statusText,
                          style: GoogleFonts.spaceMono(
                            color: color, fontSize: 9,
                          ),
                        ),
                        if (job.status == 'COMPLETE')
                          IconButton(
                            icon: const Icon(Icons.visibility, size: 16),
                            color: color,
                            padding: EdgeInsets.zero,
                            constraints: const BoxConstraints(),
                            onPressed: () {
                              Navigator.push(
                                context,
                                MaterialPageRoute(
                                  builder: (_) => PartialReportViewerScreen(
                                    projectId: job.projectId,
                                    roomId: job.roomId,
                                    roomName: job.roomName,
                                  ),
                                ),
                              );
                            },
                          ),
                        if (job.status == 'ERROR')
                          IconButton(
                            icon: const Icon(Icons.refresh, size: 16),
                            color: Colors.orangeAccent,
                            padding: EdgeInsets.zero,
                            constraints: const BoxConstraints(),
                            onPressed: () => _reportQueue.retry(job.roomId),
                          ),
                      ],
                    ),
                  );
                }),
              ],
            ),
          ),

        // Section: Rooms with evidence
        if (roomsWithData.isEmpty)
          Center(
            child: Padding(
              padding: const EdgeInsets.only(top: 80),
              child: Column(
                children: [
                  Icon(Icons.description_outlined, size: 64, color: Colors.white12),
                  const SizedBox(height: 16),
                  Text(
                    'No rooms with evidence yet.\nInspect some rooms first!',
                    style: GoogleFonts.spaceMono(color: Colors.white30, fontSize: 11),
                    textAlign: TextAlign.center,
                  ),
                ],
              ),
            ),
          )
        else
          ...roomsWithData.map((room) {
            final roomId = room['id'] as String;
            final roomName = _cleanName(room['name']?.toString());
            final int imgCount = room['images_count'] ?? 0;
            final int audioCount = room['audio_count'] ?? 0;
            final hasQueuedJob = _reportQueue.hasJobForRoom(roomId);
            final latestJob = _reportQueue.getLatestJobForRoom(roomId);
            final isComplete = latestJob?.status == 'COMPLETE';
            final isProcessing = latestJob?.status == 'PROCESSING';
            final isQueued = latestJob?.status == 'QUEUED';
            final isExpanded = _expandedRoomId == roomId;

            return GestureDetector(
              onTap: () {
                setState(() {
                  _expandedRoomId = isExpanded ? null : roomId;
                });
              },
              child: AnimatedContainer(
                duration: const Duration(milliseconds: 250),
                margin: const EdgeInsets.only(bottom: 12),
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                  color: isExpanded
                      ? Colors.white.withOpacity(0.06)
                      : Colors.white.withOpacity(0.03),
                  borderRadius: BorderRadius.circular(14),
                  border: Border.all(
                    color: isComplete
                        ? const Color(0xFF00E676).withOpacity(0.3)
                        : isProcessing
                            ? gold.withOpacity(0.4)
                            : isExpanded
                                ? gold.withOpacity(0.2)
                                : Colors.white12,
                    width: isExpanded ? 1.5 : 1.0,
                  ),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // Room header
                    Row(
                      children: [
                        Icon(
                          isComplete
                              ? Icons.check_circle
                              : isProcessing
                                  ? Icons.autorenew
                                  : Icons.meeting_room,
                          color: isComplete
                              ? const Color(0xFF00E676)
                              : isProcessing
                                  ? gold
                                  : Colors.white54,
                          size: 20,
                        ),
                        const SizedBox(width: 10),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                roomName,
                                style: GoogleFonts.outfit(
                                  color: Colors.white,
                                  fontWeight: FontWeight.w600,
                                  fontSize: 14,
                                ),
                              ),
                              const SizedBox(height: 2),
                              Row(
                                children: [
                                  Icon(Icons.camera_alt,
                                      color: imgCount > 0
                                          ? const Color(0xFF00E5FF)
                                          : Colors.white24,
                                      size: 10),
                                  const SizedBox(width: 3),
                                  Text(
                                    '$imgCount',
                                    style: GoogleFonts.spaceMono(
                                      color: imgCount > 0
                                          ? const Color(0xFF00E5FF)
                                          : Colors.white38,
                                      fontSize: 9,
                                    ),
                                  ),
                                  const SizedBox(width: 10),
                                  Icon(Icons.mic,
                                      color: audioCount > 0
                                          ? const Color(0xFFE040FB)
                                          : Colors.white24,
                                      size: 10),
                                  const SizedBox(width: 3),
                                  Text(
                                    '$audioCount',
                                    style: GoogleFonts.spaceMono(
                                      color: audioCount > 0
                                          ? const Color(0xFFE040FB)
                                          : Colors.white38,
                                      fontSize: 9,
                                    ),
                                  ),
                                ],
                              ),
                            ],
                          ),
                        ),
                        // Status / Generate button
                        if (isQueued || isProcessing)
                          Container(
                            padding: const EdgeInsets.symmetric(
                                horizontal: 8, vertical: 4),
                            decoration: BoxDecoration(
                              color: isProcessing
                                  ? gold.withOpacity(0.15)
                                  : Colors.white.withOpacity(0.05),
                              borderRadius: BorderRadius.circular(8),
                            ),
                            child: Row(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                SizedBox(
                                  width: 10, height: 10,
                                  child: CircularProgressIndicator(
                                    strokeWidth: 1.5,
                                    color: isProcessing ? gold : Colors.white54,
                                  ),
                                ),
                                const SizedBox(width: 5),
                                Text(
                                  isProcessing ? 'GENERATING' : 'QUEUED',
                                  style: GoogleFonts.spaceMono(
                                    fontSize: 7,
                                    fontWeight: FontWeight.bold,
                                    color: isProcessing ? gold : Colors.white54,
                                  ),
                                ),
                              ],
                            ),
                          )
                        else if (projectId != null && !hasQueuedJob)
                          ElevatedButton.icon(
                            onPressed: () {
                              _reportQueue.enqueue(
                                  projectId, roomId, room['name'] ?? roomName);
                              ScaffoldMessenger.of(context).showSnackBar(
                                SnackBar(
                                  content: Text(
                                    '📋 Queued: $roomName',
                                    style: GoogleFonts.spaceMono(fontSize: 11),
                                  ),
                                  backgroundColor: gold.withOpacity(0.9),
                                  duration: const Duration(seconds: 2),
                                ),
                              );
                            },
                            icon: Icon(
                              isComplete ? Icons.refresh : Icons.auto_awesome,
                              size: 12,
                            ),
                            label: Text(
                              isComplete ? 'REGEN' : 'GENERATE',
                              style: GoogleFonts.spaceMono(
                                fontSize: 7, fontWeight: FontWeight.bold,
                              ),
                            ),
                            style: ElevatedButton.styleFrom(
                              backgroundColor: gold,
                              foregroundColor: Colors.black,
                              padding: const EdgeInsets.symmetric(
                                horizontal: 8, vertical: 4,
                              ),
                              minimumSize: Size.zero,
                              shape: RoundedRectangleBorder(
                                borderRadius: BorderRadius.circular(8),
                              ),
                            ),
                          ),
                        const SizedBox(width: 4),
                        Icon(
                          isExpanded
                              ? Icons.keyboard_arrow_up
                              : Icons.keyboard_arrow_down,
                          color: Colors.white38,
                          size: 20,
                        ),
                      ],
                    ),

                    // Expandable 4-action panel
                    if (isExpanded) ...[
                      const SizedBox(height: 12),
                      Container(
                        decoration: BoxDecoration(
                          color: Colors.white.withOpacity(0.03),
                          borderRadius: BorderRadius.circular(10),
                          border: Border.all(color: Colors.white10),
                        ),
                        child: Column(
                          children: [
                            // 1. Voice Edit
                            _actionTile(
                              icon: Icons.mic,
                              iconColor: const Color(0xFFE040FB),
                              label: 'VOICE EDIT',
                              subtitle: 'Record corrections for this room',
                              onTap: () {
                                if (projectId != null) {
                                  _showVoiceAmendmentDialog(
                                      projectId, roomId, roomName);
                                }
                              },
                            ),
                            Divider(
                                color: Colors.white10,
                                height: 1,
                                indent: 44),
                            // 2. Edit Evidence (exclude/include photos)
                            _actionTile(
                              icon: Icons.photo_library,
                              iconColor: const Color(0xFF00E5FF),
                              label: 'EDIT EVIDENCE',
                              subtitle:
                                  'View, exclude or include photos in report',
                              onTap: () {
                                if (projectId != null) {
                                  Navigator.push(
                                    context,
                                    MaterialPageRoute(
                                      builder: (_) => EvidenceGalleryScreen(
                                        projectId: projectId,
                                        roomId: roomId,
                                        roomName: roomName,
                                      ),
                                    ),
                                  );
                                }
                              },
                            ),
                            Divider(
                                color: Colors.white10,
                                height: 1,
                                indent: 44),
                            // 3. View Report
                            _actionTile(
                              icon: Icons.visibility,
                              iconColor: isComplete
                                  ? const Color(0xFF00E676)
                                  : Colors.white24,
                              label: 'VIEW REPORT',
                              subtitle: isComplete
                                  ? 'Read the generated report'
                                  : 'Generate a report first',
                              enabled: isComplete,
                              onTap: isComplete && projectId != null
                                  ? () {
                                      Navigator.push(
                                        context,
                                        MaterialPageRoute(
                                          builder: (_) =>
                                              PartialReportViewerScreen(
                                            projectId: projectId,
                                            roomId: roomId,
                                            roomName: roomName,
                                          ),
                                        ),
                                      );
                                    }
                                  : null,
                            ),
                            Divider(
                                color: Colors.white10,
                                height: 1,
                                indent: 44),
                            // 4. Regenerate
                            _actionTile(
                              icon: Icons.autorenew,
                              iconColor: gold,
                              label: 'REGENERATE',
                              subtitle:
                                  'Apply voice edits & re-generate report',
                              enabled:
                                  projectId != null && !hasQueuedJob,
                              onTap: projectId != null && !hasQueuedJob
                                  ? () {
                                      _reportQueue.enqueue(projectId, roomId,
                                          room['name'] ?? roomName);
                                      ScaffoldMessenger.of(context)
                                          .showSnackBar(
                                        SnackBar(
                                          content: Text(
                                            '🔄 Regenerating: $roomName',
                                            style:
                                                GoogleFonts.spaceMono(
                                                    fontSize: 11),
                                          ),
                                          backgroundColor:
                                              gold.withOpacity(0.9),
                                          duration:
                                              const Duration(seconds: 2),
                                        ),
                                      );
                                    }
                                  : null,
                            ),
                          ],
                        ),
                      ),
                    ],
                  ],
                ),
              ),
            );
          }),

        // Full RICS Report button
        if (roomsWithData.isNotEmpty && projectId != null) ...[
          const SizedBox(height: 20),
          SizedBox(
            width: double.infinity,
            child: ElevatedButton.icon(
              onPressed: _archiveSession,
              icon: const Icon(Icons.picture_as_pdf, size: 20),
              label: Text(
                'GENERATE FULL RICS PDF',
                style: GoogleFonts.spaceMono(
                  fontSize: 11, fontWeight: FontWeight.bold,
                ),
              ),
              style: ElevatedButton.styleFrom(
                backgroundColor: gold,
                foregroundColor: Colors.black,
                padding: const EdgeInsets.symmetric(vertical: 16),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(12),
                ),
              ),
            ),
          ),
          const SizedBox(height: 40),
        ],
      ],
    );
  }

  Widget _actionTile({
    required IconData icon,
    required Color iconColor,
    required String label,
    required String subtitle,
    bool enabled = true,
    VoidCallback? onTap,
  }) {
    return InkWell(
      onTap: enabled ? onTap : null,
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
        child: Row(
          children: [
            Container(
              width: 28, height: 28,
              decoration: BoxDecoration(
                color: (enabled ? iconColor : Colors.white24).withOpacity(0.15),
                borderRadius: BorderRadius.circular(7),
              ),
              child: Icon(icon,
                  color: enabled ? iconColor : Colors.white24, size: 14),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    label,
                    style: GoogleFonts.spaceMono(
                      color: enabled ? Colors.white : Colors.white30,
                      fontSize: 10,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  Text(
                    subtitle,
                    style: GoogleFonts.spaceMono(
                      color: enabled ? Colors.white38 : Colors.white12,
                      fontSize: 8,
                    ),
                  ),
                ],
              ),
            ),
            Icon(Icons.chevron_right,
                color: enabled ? Colors.white30 : Colors.white10, size: 16),
          ],
        ),
      ),
    );
  }

  // ============== VOICE AMENDMENT DIALOG ==============

  Future<void> _showVoiceAmendmentDialog(
      String projectId, String roomId, String roomName) async {
    final recorder = AudioRecorder();
    bool isRecording = false;
    String? recordedPath;
    bool isUploading = false;
    bool uploadSuccess = false;

    await showModalBottomSheet(
      context: context,
      backgroundColor: Colors.transparent,
      isScrollControlled: true,
      builder: (ctx) {
        return StatefulBuilder(
          builder: (context, setDialogState) {
            return Container(
              padding: EdgeInsets.only(
                top: 20,
                left: 20,
                right: 20,
                bottom: MediaQuery.of(context).viewInsets.bottom + 30,
              ),
              decoration: const BoxDecoration(
                color: Color(0xFF0F172A),
                borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
              ),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  // Handle bar
                  Container(
                    width: 40, height: 4,
                    decoration: BoxDecoration(
                      color: Colors.white24,
                      borderRadius: BorderRadius.circular(2),
                    ),
                  ),
                  const SizedBox(height: 16),
                  // Title
                  Text(
                    '🎤 VOICE EDIT',
                    style: GoogleFonts.spaceMono(
                      color: const Color(0xFFFFD700),
                      fontSize: 14,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    roomName,
                    style: GoogleFonts.outfit(
                      color: Colors.white70,
                      fontSize: 12,
                    ),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'Record your corrections and additions.\nGemini will apply them on next report generation.',
                    style: GoogleFonts.spaceMono(
                      color: Colors.white38,
                      fontSize: 9,
                    ),
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: 24),

                  // Record button
                  if (isUploading)
                    Column(
                      children: [
                        const CircularProgressIndicator(
                          color: Color(0xFFFFD700),
                          strokeWidth: 2,
                        ),
                        const SizedBox(height: 12),
                        Text(
                          'Uploading amendment...',
                          style: GoogleFonts.spaceMono(
                            color: Colors.white54, fontSize: 10,
                          ),
                        ),
                      ],
                    )
                  else if (uploadSuccess)
                    Column(
                      children: [
                        const Icon(Icons.check_circle,
                            color: Color(0xFF00E676), size: 60),
                        const SizedBox(height: 12),
                        Text(
                          'Amendment saved!',
                          style: GoogleFonts.spaceMono(
                            color: const Color(0xFF00E676), fontSize: 11,
                          ),
                        ),
                        Text(
                          'Tap REGENERATE to apply changes.',
                          style: GoogleFonts.spaceMono(
                            color: Colors.white38, fontSize: 9,
                          ),
                        ),
                      ],
                    )
                  else
                    GestureDetector(
                      onTap: () async {
                        if (isRecording) {
                          // STOP recording
                          final path = await recorder.stop();
                          setDialogState(() {
                            isRecording = false;
                            recordedPath = path;
                          });

                          // Upload immediately
                          if (path != null) {
                            setDialogState(() => isUploading = true);
                            try {
                              final result =
                                  await _api.uploadVoiceAddendum(
                                projectId,
                                roomId,
                                File(path),
                              );
                              setDialogState(() {
                                isUploading = false;
                                uploadSuccess = result != null;
                              });
                              if (result != null) {
                                _fetchStatus(); // Refresh counts
                              }
                            } catch (e) {
                              setDialogState(() => isUploading = false);
                              if (mounted) {
                                ScaffoldMessenger.of(this.context)
                                    .showSnackBar(
                                  SnackBar(
                                    content: Text('Upload failed: $e'),
                                    backgroundColor: Colors.redAccent,
                                  ),
                                );
                              }
                            }
                          }
                        } else {
                          // START recording
                          if (await Permission.microphone
                              .request()
                              .isGranted) {
                            final dir =
                                await getApplicationDocumentsDirectory();
                            final path =
                                '${dir.path}/amendment_${roomId}_${DateTime.now().millisecondsSinceEpoch}.m4a';
                            await recorder.start(
                                const RecordConfig(), path: path);
                            setDialogState(() => isRecording = true);
                          }
                        }
                      },
                      child: Container(
                        width: 90, height: 90,
                        decoration: BoxDecoration(
                          color: isRecording
                              ? Colors.redAccent
                              : const Color(0xFFE040FB),
                          shape: BoxShape.circle,
                          boxShadow: [
                            BoxShadow(
                              color: (isRecording
                                      ? Colors.redAccent
                                      : const Color(0xFFE040FB))
                                  .withOpacity(0.4),
                              blurRadius: 20,
                              spreadRadius: 4,
                            ),
                          ],
                        ),
                        child: Icon(
                          isRecording ? Icons.stop : Icons.mic,
                          size: 40,
                          color: Colors.white,
                        ),
                      ),
                    ),

                  const SizedBox(height: 12),
                  if (!isUploading && !uploadSuccess)
                    Text(
                      isRecording
                          ? '🔴 Recording... tap to stop'
                          : 'Tap to start recording',
                      style: GoogleFonts.spaceMono(
                        color: isRecording
                            ? Colors.redAccent
                            : Colors.white54,
                        fontSize: 10,
                      ),
                    ),
                  const SizedBox(height: 16),
                ],
              ),
            );
          },
        );
      },
    );

    // Cleanup
    await recorder.dispose();
  }
  Widget _buildCategoryView(String cat) {
    List<dynamic> catRooms = [];
    IconData fallbackIcon = Icons.error;
    Color fallbackColor = Colors.white;
    String fallbackId = "";
    String fallbackType = "";
    String fallbackName = "";

    // RICS Categorization using actual room data fields:
    // - type: 'general', 'wet', 'external', 'services', 'grounds', 'executive'
    // - floor_name: 'Ground Floor', 'First Floor', 'Second Floor', etc.
    if (cat == 'D') {
      // D: EXTERIOR — external structure elements
      catRooms = _rooms
          .where((r) => r['type'] == 'external' || r['type'] == 'grounds')
          .toList();
      fallbackIcon = Icons.roofing;
      fallbackColor = Colors.greenAccent;
      fallbackId = "cat_d_main";
      fallbackType = "external";
      fallbackName = "External Main Structure";
    } else if (cat == 'E') {
      // E: INTERIOR — ONLY general rooms (bedrooms, living rooms), grouped by floor
      catRooms = _rooms.where((r) => r['type'] == 'general').toList();
    } else if (cat == 'F') {
      // F: SERVICES — wet rooms (bathrooms, kitchens) and service areas
      catRooms = _rooms
          .where((r) => r['type'] == 'wet' || r['type'] == 'services')
          .toList();
      fallbackIcon = Icons.electrical_services;
      fallbackColor = Colors.amber;
      fallbackId = "cat_f_main";
      fallbackType = "services";
      fallbackName = "Main Services";
    } else if (cat == 'G') {
      // G: GROUNDS — gardens, boundaries, external areas
      catRooms = _rooms.where((r) => r['type'] == 'grounds').toList();
      fallbackIcon = Icons.park;
      fallbackColor = Colors.brown;
      fallbackId = "cat_g_main";
      fallbackType = "grounds";
      fallbackName = "Grounds & Boundaries";
    }

    if (catRooms.isEmpty && cat != 'E') {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(fallbackIcon, size: 80, color: fallbackColor.withOpacity(0.2)),
            const SizedBox(height: 24),
            Text(
              "NO ${fallbackName.toUpperCase()} RECORDED",
              style: GoogleFonts.spaceMono(color: Colors.white54, fontSize: 10),
            ),
            const SizedBox(height: 24),
            OutlinedButton.icon(
              onPressed: () => _openInspection({
                'id': fallbackId,
                'name': fallbackName,
                'type': fallbackType,
              }),
              icon: Icon(fallbackIcon, color: fallbackColor),
              label: Text(
                "INITIATE CATEGORY SCAN",
                style: TextStyle(color: fallbackColor),
              ),
              style: OutlinedButton.styleFrom(
                side: BorderSide(color: fallbackColor.withOpacity(0.5)),
              ),
            ),
          ],
        ),
      );
    }

    if (catRooms.isEmpty && cat == 'E') {
      return Center(
        child: Text(
          "NO INTERIOR ROOMS DETECTED",
          style: GoogleFonts.spaceMono(color: Colors.white30),
        ),
      );
    }

    // For E: INTERIOR, group rooms by floor_name for clear visual separation
    if (cat == 'E') {
      // Build floor groups
      final Map<String, List<dynamic>> floorGroups = {};
      for (var room in catRooms) {
        final floorName = _cleanName(room['floor_name']?.toString());
        floorGroups.putIfAbsent(floorName, () => []);
        floorGroups[floorName]!.add(room);
      }

      // Sort floor names: Ground Floor first, then First Floor, Second Floor, etc.
      final sortedFloors = floorGroups.keys.toList()
        ..sort((a, b) {
          int floorIndex(String name) {
            final lower = name.toLowerCase();
            if (lower.contains('ground') || lower.contains('rez')) return 0;
            if (lower.contains('first') || lower.contains('1st')) return 1;
            if (lower.contains('second') || lower.contains('2nd')) return 2;
            if (lower.contains('third') || lower.contains('3rd')) return 3;
            return 99;
          }

          return floorIndex(a).compareTo(floorIndex(b));
        });

      return ListView.builder(
        padding: const EdgeInsets.only(top: 8, bottom: 80),
        itemCount: sortedFloors.length,
        itemBuilder: (ctx, floorIdx) {
          final floorName = sortedFloors[floorIdx];
          final floorRooms = floorGroups[floorName]!;

          return Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Floor Header
              Padding(
                padding:
                    const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                child: Row(
                  children: [
                    const Icon(Icons.layers,
                        color: Color(0xFFFFD700), size: 16),
                    const SizedBox(width: 8),
                    Text(
                      floorName.toUpperCase(),
                      style: GoogleFonts.outfit(
                        color: const Color(0xFFFFD700),
                        fontWeight: FontWeight.bold,
                        fontSize: 13,
                        letterSpacing: 1.5,
                      ),
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Container(
                        height: 1,
                        color: const Color(0xFFFFD700).withOpacity(0.3),
                      ),
                    ),
                    const SizedBox(width: 8),
                    Text(
                      '${floorRooms.length} ROOMS',
                      style: GoogleFonts.spaceMono(
                        color: Colors.white38,
                        fontSize: 10,
                      ),
                    ),
                  ],
                ),
              ),
              // Room Grid for this floor
              GridView.builder(
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                padding: const EdgeInsets.symmetric(horizontal: 16),
                gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                  crossAxisCount: 2,
                  childAspectRatio: 0.85,
                  crossAxisSpacing: 16,
                  mainAxisSpacing: 16,
                ),
                itemCount: floorRooms.length,
                itemBuilder: (ctx, i) => _buildRoomCard(floorRooms[i]),
              ),
              const SizedBox(height: 8),
            ],
          );
        },
      );
    }

    // Standard grid for D, F, G categories
    return GridView.builder(
      padding: const EdgeInsets.only(
        top: 16,
        left: 16,
        right: 16,
        bottom: 80,
      ), // bottom padding for FAB
      gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
        crossAxisCount: 2,
        childAspectRatio: 0.85,
        crossAxisSpacing: 16,
        mainAxisSpacing: 16,
      ),
      itemCount: catRooms.length,
      itemBuilder: (ctx, i) => _buildRoomCard(catRooms[i]),
    );
  }

  Widget _buildRoomCard(Map<String, dynamic> room) {
    final status = room['status']?.toString() ?? 'pending';
    final color = _getStatusColor(status);
    final int imgCount = room['images_count'] ?? 0;
    final int audioCount = room['audio_count'] ?? 0;
    final bool hasData = imgCount > 0 || audioCount > 0;
    final String statusLabel = status == 'completed'
        ? 'COMPLETE'
        : (status == 'in_progress' ? 'IN PROGRESS' : 'PENDING');

    return GlassmorphicContainer(
      width: double.infinity,
      height: double.infinity,
      borderRadius: 16,
      blur: 5,
      border: 1,
      alignment: Alignment.center,
      linearGradient: LinearGradient(
        begin: Alignment.topLeft,
        end: Alignment.bottomRight,
        colors: [
          Colors.white.withOpacity(0.05),
          Colors.white.withOpacity(0.01),
        ],
      ),
      borderGradient: LinearGradient(
        begin: Alignment.topLeft,
        end: Alignment.bottomRight,
        colors: [color.withOpacity(0.5), Colors.white.withOpacity(0.05)],
      ),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            // Status Row
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Icon(_getStatusIcon(status), color: color, size: 16),
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 6,
                    vertical: 2,
                  ),
                  decoration: BoxDecoration(
                    color: color.withOpacity(0.2),
                    borderRadius: BorderRadius.circular(4),
                  ),
                  child: Text(
                    statusLabel,
                    style: GoogleFonts.spaceMono(color: color, fontSize: 8),
                  ),
                ),
              ],
            ),
            // Room Name
            Flexible(
              child: Center(
                child: Text(
                  _cleanName(room['name']?.toString()),
                  style: GoogleFonts.outfit(
                    color: Colors.white,
                    fontWeight: FontWeight.bold,
                    fontSize: 13,
                  ),
                  textAlign: TextAlign.center,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                ),
              ),
            ),
            // Evidence Counters
            Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(Icons.camera_alt,
                    color:
                        imgCount > 0 ? const Color(0xFF00E5FF) : Colors.white24,
                    size: 12),
                const SizedBox(width: 3),
                Text(
                  '$imgCount',
                  style: GoogleFonts.spaceMono(
                    color:
                        imgCount > 0 ? const Color(0xFF00E5FF) : Colors.white24,
                    fontSize: 10,
                  ),
                ),
                const SizedBox(width: 10),
                Icon(Icons.mic,
                    color: audioCount > 0
                        ? const Color(0xFFFFD700)
                        : Colors.white24,
                    size: 12),
                const SizedBox(width: 3),
                Text(
                  '$audioCount',
                  style: GoogleFonts.spaceMono(
                    color: audioCount > 0
                        ? const Color(0xFFFFD700)
                        : Colors.white24,
                    fontSize: 10,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 4),
            // Report Queue Status Badge
            Builder(builder: (context) {
              final roomId = room['id'] as String;
              final job = _reportQueue.getLatestJobForRoom(roomId);
              if (job == null) return const SizedBox.shrink();
              
              final isProcessing = job.status == 'PROCESSING';
              final isQueued = job.status == 'QUEUED';
              final isComplete = job.status == 'COMPLETE';
              final isError = job.status == 'ERROR';
              
              if (!isProcessing && !isQueued && !isComplete && !isError) {
                return const SizedBox.shrink();
              }

              final Color badgeColor = isProcessing
                  ? const Color(0xFFFFD700)
                  : isQueued
                      ? Colors.white54
                      : isComplete
                          ? const Color(0xFF00E676)
                          : Colors.redAccent;
              final String badgeText = isProcessing
                  ? '🔄 GENERATING'
                  : isQueued
                      ? '⏳ QUEUED'
                      : isComplete
                          ? '✅ READY'
                          : '❌ ERROR';

              return Container(
                width: double.infinity,
                padding: const EdgeInsets.symmetric(vertical: 3),
                margin: const EdgeInsets.only(bottom: 2),
                decoration: BoxDecoration(
                  color: badgeColor.withOpacity(0.12),
                  borderRadius: BorderRadius.circular(6),
                ),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    if (isProcessing || isQueued)
                      Padding(
                        padding: const EdgeInsets.only(right: 4),
                        child: SizedBox(
                          width: 8, height: 8,
                          child: CircularProgressIndicator(
                            strokeWidth: 1.2,
                            color: badgeColor,
                          ),
                        ),
                      ),
                    Text(
                      badgeText,
                      style: GoogleFonts.spaceMono(
                        color: badgeColor,
                        fontSize: 7,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ],
                ),
              );
            }),
            // Scan Button
            SizedBox(
              width: double.infinity,
              height: 30,
              child: OutlinedButton(
                style: OutlinedButton.styleFrom(
                  side: BorderSide(color: color.withOpacity(0.5)),
                  padding: EdgeInsets.zero,
                ),
                onPressed: () => _openInspection(room),
                child: Text(
                  hasData ? "RE-SCAN" : "SCAN",
                  style: GoogleFonts.spaceMono(color: color, fontSize: 10),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
