import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:glassmorphism/glassmorphism.dart';
import 'package:flutter_animate/flutter_animate.dart';

import '../services/api_service.dart';
import '../core/services/auth_service.dart';

import 'floor_plan_hub.dart';
import 'floor_plan_recorder.dart';

import 'property_init_screen.dart';
import 'reports_hub.dart';
import 'final_report_tab.dart';

class PropertyDetailsScreen extends ConsumerStatefulWidget {
  final String propertyId;
  const PropertyDetailsScreen({super.key, required this.propertyId});

  @override
  ConsumerState<PropertyDetailsScreen> createState() =>
      _PropertyDetailsScreenState();
}

class _PropertyDetailsScreenState extends ConsumerState<PropertyDetailsScreen>
    with SingleTickerProviderStateMixin {
  final ApiService _api = ApiService();
  bool _isLoading = true;
  Map<String, dynamic>? _propertyData;
  late TabController _mainTabController;

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
    _mainTabController = TabController(length: 3, vsync: this);
    _fetchProperty();
  }

  @override
  void dispose() {
    _mainTabController.dispose();
    super.dispose();
  }

  Future<void> _fetchProperty() async {
    try {
      final data = await _api.getProjectDetails(widget.propertyId);
      if (mounted) {
        setState(() {
          _propertyData = data;
          _isLoading = false;
        });
      }
    } catch (e) {
      if (mounted) setState(() => _isLoading = false);
      print("Error fetching property details: $e");
    }
  }

  void _editProperty() async {
    if (_propertyData == null) return;
    final result = await Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => PropertyInitScreen(propertyData: _propertyData),
      ),
    );
    if (result == true) {
      setState(() => _isLoading = true);
      _fetchProperty(); // Refresh data
    }
  }

  Future<void> _startFullInspection() async {
    final user = ref.read(userProvider);
    if (user == null || _propertyData == null) return;

    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (_) => const Center(
        child: CircularProgressIndicator(color: Color(0xFFFFD700)),
      ),
    );

    try {
      final session = await _api.createSession(
        projectId: _propertyData!['id'],
        surveyorId: user['id'],
        title: "${_propertyData!['reference_number']} Inspection",
      );

      if (mounted) {
        Navigator.pop(context); // Close loading
        Navigator.push(
          context,
          MaterialPageRoute(
            builder: (_) => FloorPlanHubScreen(sessionId: session['id']),
          ),
        ).then((_) => _fetchProperty()); // Refresh on return
      }
    } catch (e) {
      if (mounted) {
        Navigator.pop(context);
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text("Mission Link Failed: $e")));
      }
    }
  }


  void _openVoiceArchitect() async {
    if (_propertyData == null) return;

    final metadata = _propertyData!['metadata'] ?? {};

    final initialData = {
      'property_id': _propertyData!['id'],
      'property_type': metadata['property_type'] ?? 'Detached',
      'number_of_floors': metadata['number_of_floors'] ?? 1,
    };

    final result = await Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => FloorPlanRecorder(initialData: initialData),
      ),
    );

    if (result == true) {
      _fetchProperty(); // Refresh to see the new rooms!
    }
  }

  @override
  Widget build(BuildContext context) {
    final gold = const Color(0xFFFFD700);

    return Scaffold(
      backgroundColor: const Color(0xFF05080D),
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        title: Text(
          "PROPERTY HUB",
          style: GoogleFonts.outfit(
            color: Colors.white,
            fontWeight: FontWeight.bold,
            letterSpacing: 2,
          ),
        ),
        centerTitle: true,
        iconTheme: const IconThemeData(color: Colors.white),
        actions: [
          if (_propertyData != null && !_isLoading)
            IconButton(
              icon: const Icon(Icons.edit_note),
              color: const Color(0xFFFFD700),
              onPressed: _editProperty,
              tooltip: "Edit Property Profile",
            ),
        ],
        bottom: _propertyData != null && !_isLoading
            ? PreferredSize(
                preferredSize: const Size.fromHeight(48),
                child: Container(
                  margin:
                      const EdgeInsets.symmetric(horizontal: 24, vertical: 4),
                  height: 44,
                  decoration: BoxDecoration(
                    color: Colors.white.withOpacity(0.05),
                    borderRadius: BorderRadius.circular(22),
                    border: Border.all(color: Colors.white.withOpacity(0.1)),
                  ),
                  child: TabBar(
                    controller: _mainTabController,
                    indicator: BoxDecoration(
                      color: gold.withOpacity(0.8),
                      borderRadius: BorderRadius.circular(22),
                    ),
                    labelColor: Colors.black,
                    unselectedLabelColor: Colors.white54,
                    labelStyle: GoogleFonts.spaceMono(
                      fontSize: 10,
                      fontWeight: FontWeight.bold,
                      letterSpacing: 1,
                    ),
                    tabs: const [
                      Tab(text: '🔍 INSPECTION'),
                      Tab(text: '📄 REPORTS'),
                      Tab(text: '📋 FINAL'),
                    ],
                  ),
                ),
              )
            : null,
      ),
      body: Stack(
        children: [
          Positioned.fill(
            child: Opacity(
              opacity: 0.05,
              child: Image.network(
                "https://www.transparenttextures.com/patterns/graphy.png",
                repeat: ImageRepeat.repeat,
              ),
            ),
          ),
          if (_isLoading)
            Center(child: CircularProgressIndicator(color: gold))
          else if (_propertyData == null)
            Center(
              child: Text(
                "FAILED TO LOAD PROPERTY",
                style: GoogleFonts.spaceMono(color: Colors.red),
              ),
            )
          else
            TabBarView(
              controller: _mainTabController,
              children: [
                // Tab 1: Inspection (existing content)
                _buildInspectionTab(gold),
                // Tab 2: Reports Hub
                ReportsHubScreen(
                  projectId: widget.propertyId,
                  propertyData: _propertyData,
                ),
                // Tab 3: Final Report (Edit, Voice, Web, Photos)
                FinalReportTab(
                  projectId: widget.propertyId,
                ),
              ],
            ),
        ],
      ),
    );
  }

  Widget _buildInspectionTab(Color gold) {
    return Column(
      children: [
        // Header Card
        Padding(
          padding: const EdgeInsets.all(16.0),
          child: GlassmorphicContainer(
            width: double.infinity,
            height: 100,
            borderRadius: 16,
            blur: 15,
            alignment: Alignment.center,
            border: 1,
            linearGradient: LinearGradient(
              colors: [
                Colors.white.withOpacity(0.08),
                Colors.white.withOpacity(0.02),
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
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: gold.withOpacity(0.1),
                      shape: BoxShape.circle,
                    ),
                    child: Icon(
                      Icons.location_city,
                      color: gold,
                      size: 28,
                    ),
                  ),
                  const SizedBox(width: 16),
                  Expanded(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          _propertyData!['client_name'] ?? 'UNKNOWN CLIENT',
                          style: GoogleFonts.spaceMono(
                            color: gold,
                            fontSize: 12,
                          ),
                        ),
                        Text(
                          _propertyData!['reference_number'] ??
                              'UNKNOWN TARGET',
                          style: GoogleFonts.outfit(
                            color: Colors.white,
                            fontWeight: FontWeight.bold,
                            fontSize: 20,
                          ),
                          overflow: TextOverflow.ellipsis,
                        ),
                        Text(
                          '${(_propertyData!['rooms'] as List).length} DEFINED ZONES',
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

        // Action Bar
        Padding(
          padding: const EdgeInsets.symmetric(
            horizontal: 16.0,
            vertical: 8.0,
          ),
          child: SizedBox(
            width: double.infinity,
            height: 50,
            child: ElevatedButton.icon(
              style: ElevatedButton.styleFrom(
                backgroundColor: gold,
                foregroundColor: Colors.black,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(12),
                ),
              ),
              onPressed: _startFullInspection,
              icon: const Icon(Icons.add_a_photo, size: 20),
              label: Text(
                "START FULL INSPECTION (TODAY)",
                style: GoogleFonts.outfit(
                  fontWeight: FontWeight.bold,
                  fontSize: 16,
                ),
              ),
            ),
          ),
        ).animate().fadeIn(delay: 100.ms).slideY(),

        const SizedBox(height: 16),

        // --- INSPECTION PROGRESS SUMMARY ---
        Expanded(
          child: (_propertyData!['rooms'] as List).isEmpty
              ? Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      const Icon(Icons.mic_none, size: 64, color: Colors.white24),
                      const SizedBox(height: 16),
                      Text(
                        "NO ROOMS DEFINED",
                        style: GoogleFonts.outfit(
                          color: Colors.white54,
                          fontSize: 18,
                          letterSpacing: 2,
                        ),
                      ),
                      const SizedBox(height: 24),
                      ElevatedButton.icon(
                        style: ElevatedButton.styleFrom(
                          backgroundColor: const Color(0xFF1E88E5),
                          foregroundColor: Colors.white,
                          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(30)),
                        ),
                        onPressed: _openVoiceArchitect,
                        icon: const Icon(Icons.voice_chat),
                        label: Text(
                          "VOICE ARCHITECT: DEFINE ROOMS",
                          style: GoogleFonts.outfit(fontWeight: FontWeight.bold),
                        ),
                      ),
                    ],
                  ),
                )
              : _buildProgressSummary(),
        ),
      ],
    );
  }

  /// Inspection Progress Summary — replaces the room card grid
  Widget _buildProgressSummary() {
    const gold = Color(0xFFFFD700);
    const cyan = Color(0xFF00E5FF);
    const green = Color(0xFF00E676);
    final List rooms = _propertyData!['rooms'] as List;
    int totalPhotos = 0;
    int totalAudio = 0;
    int scannedRooms = 0;
    int pendingRooms = 0;
    final List<Map<String, dynamic>> scannedList = [];
    final List<Map<String, dynamic>> pendingList = [];

    for (var r in rooms) {
      final room = r as Map<String, dynamic>;
      final imgCount = room['images_count'] ?? 0;
      final audioCount = room['audio_count'] ?? 0;
      totalPhotos += (imgCount as int);
      totalAudio += (audioCount as int);
      if (imgCount > 0 || audioCount > 0) {
        scannedRooms++;
        scannedList.add(room);
      } else {
        pendingRooms++;
        pendingList.add(room);
      }
    }

    final double progress = rooms.isNotEmpty ? scannedRooms / rooms.length : 0;

    return ListView(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      children: [
        // Progress Header
        Padding(
          padding: const EdgeInsets.only(bottom: 12),
          child: Text(
            "INSPECTION PROGRESS",
            style: GoogleFonts.spaceMono(
              color: Colors.white54,
              fontSize: 12,
              letterSpacing: 2,
            ),
          ),
        ).animate().fadeIn(),

        // Progress Bar
        ClipRRect(
          borderRadius: BorderRadius.circular(6),
          child: LinearProgressIndicator(
            value: progress,
            minHeight: 8,
            backgroundColor: Colors.white10,
            valueColor: AlwaysStoppedAnimation(
              progress >= 1.0 ? green : gold,
            ),
          ),
        ),
        const SizedBox(height: 4),
        Align(
          alignment: Alignment.centerRight,
          child: Text(
            '${(progress * 100).toInt()}% — $scannedRooms/${rooms.length} ROOMS',
            style: GoogleFonts.spaceMono(
              color: progress >= 1.0 ? green : gold,
              fontSize: 10,
              fontWeight: FontWeight.bold,
            ),
          ),
        ),
        const SizedBox(height: 16),

        // Stats Row
        Row(
          children: [
            _statCard(Icons.camera_alt, '$totalPhotos', 'PHOTOS', cyan),
            const SizedBox(width: 12),
            _statCard(Icons.mic, '$totalAudio', 'AUDIO', gold),
            const SizedBox(width: 12),
            _statCard(Icons.meeting_room, '${rooms.length}', 'ROOMS', Colors.white54),
          ],
        ).animate().fadeIn(delay: 100.ms),
        const SizedBox(height: 20),

        // Scanned Rooms Section
        if (scannedList.isNotEmpty) ...[
          Row(
            children: [
              Icon(Icons.check_circle, color: green, size: 16),
              const SizedBox(width: 6),
              Text(
                'SCANNED ($scannedRooms)',
                style: GoogleFonts.spaceMono(
                  color: green,
                  fontSize: 11,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          ...scannedList.map((room) => _roomStatusRow(room, true)),
          const SizedBox(height: 16),
        ],

        // Pending Rooms Section
        if (pendingList.isNotEmpty) ...[
          Row(
            children: [
              const Icon(Icons.radio_button_unchecked, color: Colors.white38, size: 16),
              const SizedBox(width: 6),
              Text(
                'PENDING ($pendingRooms)',
                style: GoogleFonts.spaceMono(
                  color: Colors.white38,
                  fontSize: 11,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          ...pendingList.map((room) => _roomStatusRow(room, false)),
        ],
      ],
    );
  }

  Widget _statCard(IconData icon, String value, String label, Color color) {
    return Expanded(
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 12),
        decoration: BoxDecoration(
          color: color.withOpacity(0.08),
          borderRadius: BorderRadius.circular(10),
          border: Border.all(color: color.withOpacity(0.2)),
        ),
        child: Column(
          children: [
            Icon(icon, color: color, size: 20),
            const SizedBox(height: 4),
            Text(
              value,
              style: GoogleFonts.outfit(
                color: Colors.white,
                fontWeight: FontWeight.bold,
                fontSize: 18,
              ),
            ),
            Text(
              label,
              style: GoogleFonts.spaceMono(
                color: Colors.white38,
                fontSize: 8,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _roomStatusRow(Map<String, dynamic> room, bool scanned) {
    final int imgCount = room['images_count'] ?? 0;
    final int audioCount = room['audio_count'] ?? 0;
    const green = Color(0xFF00E676);
    const cyan = Color(0xFF00E5FF);
    const gold = Color(0xFFFFD700);

    return Container(
      margin: const EdgeInsets.only(bottom: 6),
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.04),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(
          color: scanned ? green.withOpacity(0.2) : Colors.white10,
        ),
      ),
      child: Row(
        children: [
          Icon(
            scanned ? Icons.check_circle : Icons.radio_button_unchecked,
            color: scanned ? green : Colors.white24,
            size: 16,
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              _cleanName(room['name']),
              style: GoogleFonts.outfit(
                color: scanned ? Colors.white : Colors.white38,
                fontWeight: scanned ? FontWeight.bold : FontWeight.normal,
                fontSize: 13,
              ),
              overflow: TextOverflow.ellipsis,
            ),
          ),
          if (scanned) ...[
            Icon(Icons.camera_alt, color: cyan, size: 12),
            const SizedBox(width: 3),
            Text('$imgCount', style: GoogleFonts.spaceMono(color: cyan, fontSize: 10)),
            const SizedBox(width: 8),
            Icon(Icons.mic, color: gold, size: 12),
            const SizedBox(width: 3),
            Text('$audioCount', style: GoogleFonts.spaceMono(color: gold, fontSize: 10)),
          ] else
            Text(
              'AWAITING',
              style: GoogleFonts.spaceMono(color: Colors.white24, fontSize: 9),
            ),
        ],
      ),
    );
  }
}
