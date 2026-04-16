import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:glassmorphism/glassmorphism.dart';
import 'package:flutter_animate/flutter_animate.dart';
import '../services/api_service.dart';
import 'evidence_gallery.dart';
import 'partial_report_viewer.dart';

/// Reports Hub — mirrors FloorPlanHub layout but with report-focused actions.
/// Each room card shows 4 buttons: View Evidence, Generate Report,
/// View Report, Voice Edit.
class ReportsHubScreen extends ConsumerStatefulWidget {
  final String projectId;
  final Map<String, dynamic>? propertyData;

  const ReportsHubScreen({
    super.key,
    required this.projectId,
    this.propertyData,
  });

  @override
  ConsumerState<ReportsHubScreen> createState() => _ReportsHubScreenState();
}

class _ReportsHubScreenState extends ConsumerState<ReportsHubScreen>
    with SingleTickerProviderStateMixin {
  final ApiService _api = ApiService();
  bool _isLoading = true;
  List<Map<String, dynamic>> _rooms = [];
  bool _isGeneratingFinal = false;
  // Background pipeline: track which rooms are generating (allows multiple concurrent)
  final Set<String> _activeGenerations = {};
  final Map<String, String> _genStatus = {}; // roomId → status text

  /// Clean code name like 'G_Ground_Floor_Circulation' → 'Ground Floor Circulation'
  String _cleanName(String? raw) {
    if (raw == null || raw.isEmpty) return 'Room';
    String cleaned = raw.replaceFirst(RegExp(r'^[A-Z]\d?_'), '');
    cleaned = cleaned.replaceAll('_', ' ');
    cleaned = cleaned.split(' ').map((w) => w.isEmpty ? '' : '${w[0].toUpperCase()}${w.substring(1).toLowerCase()}').join(' ');
    return cleaned.trim();
  }

  // RICS category tabs
  final _categories = [
    {'key': 'D', 'label': 'EXTERNAL', 'icon': Icons.home_work},
    {'key': 'E', 'label': 'INTERNAL', 'icon': Icons.door_back_door},
    {'key': 'F', 'label': 'SERVICES', 'icon': Icons.electrical_services},
    {'key': 'G', 'label': 'GENERAL', 'icon': Icons.gavel},
  ];

  late TabController _tabController;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: _categories.length, vsync: this);
    _loadData();
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  Future<void> _loadData() async {
    try {
      final data =
          widget.propertyData ?? await _api.getProjectDetails(widget.projectId);
      if (mounted) {
        final allRooms =
            (data?['rooms'] as List<dynamic>?)?.cast<Map<String, dynamic>>() ??
                [];
        setState(() {
          _rooms = allRooms;
          _isLoading = false;
        });
      }
    } catch (e) {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  List<Map<String, dynamic>> _roomsForCategory(String catKey) {
    return _rooms.where((r) {
      final type = (r['type'] ?? '').toString().toLowerCase();
      final name = (r['name'] ?? '').toString().toLowerCase();
      if (catKey == 'D') {
        return type == 'external' || name.contains('exterior') || name.contains('roof') || name.contains('chimney');
      }
      if (catKey == 'E') {
        return type == 'general' || type == 'bedroom' || type == 'living'
            || name.contains('bedroom') || name.contains('living') || name.contains('dining')
            || name.contains('lounge') || name.contains('hallway') || name.contains('landing')
            || name.contains('corridor') || name.contains('circulation') || name.contains('stair');
      }
      if (catKey == 'F') {
        return type == 'wet' || type == 'services' || type == 'kitchen'
            || type == 'bathroom' || type == 'wet_room'
            || name.contains('kitchen') || name.contains('bath') || name.contains('wc')
            || name.contains('toilet') || name.contains('ensuite') || name.contains('utility')
            || name.contains('boiler') || name.contains('laundry');
      }
      if (catKey == 'G') {
        return type == 'grounds' || name.contains('garden') || name.contains('garage')
            || name.contains('driveway') || name.contains('boundary');
      }
      return false;
    }).toList();
  }

  bool get _allRoomsHavePartialReport {
    if (_rooms.isEmpty) return false;
    return _rooms.every((r) => r['has_partial_report'] == true);
  }

  /// Background report generation — no blocking dialog
  void _generateInBackground(String roomId, String roomName) {
    if (_activeGenerations.contains(roomId)) return;
    setState(() {
      _activeGenerations.add(roomId);
      _genStatus[roomId] = 'Queued...';
    });

    // Fire and forget — runs in background
    () async {
      try {
        if (mounted) setState(() => _genStatus[roomId] = 'Analyzing photos...');
        final result = await _api.generatePartialReport(widget.projectId, roomId);
        if (mounted) {
          setState(() {
            _activeGenerations.remove(roomId);
            _genStatus.remove(roomId);
          });
          _loadData(); // Refresh to show ✅ REPORT badge
          if (result != null) {
            ScaffoldMessenger.of(context).showSnackBar(
              SnackBar(
                content: Text('✅ $roomName report ready', style: GoogleFonts.spaceMono(fontSize: 11)),
                backgroundColor: const Color(0xFF00E676),
                duration: const Duration(seconds: 2),
              ),
            );
          } else {
            ScaffoldMessenger.of(context).showSnackBar(
              SnackBar(
                content: Text('❌ $roomName failed — retry', style: GoogleFonts.spaceMono(fontSize: 11)),
                backgroundColor: Colors.redAccent,
              ),
            );
          }
        }
      } catch (e) {
        if (mounted) {
          setState(() {
            _activeGenerations.remove(roomId);
            _genStatus[roomId] = 'Error';
          });
        }
      }
    }();
  }

  Future<void> _generateFinalReport() async {
    setState(() => _isGeneratingFinal = true);
    try {
      // Use the NEW Markdown-First pipeline (with photo bridge + Gemini timeout)
      final result = await _api.generateFinalReport(widget.projectId);
      if (mounted) {
        if (result != null) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text('Final report generated!', style: GoogleFonts.spaceMono()),
              backgroundColor: const Color(0xFF00E676),
            ),
          );
        } else {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text('Generation failed — check logs', style: GoogleFonts.spaceMono()),
              backgroundColor: Colors.redAccent,
            ),
          );
        }
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Error: $e', style: GoogleFonts.spaceMono()),
            backgroundColor: Colors.redAccent,
          ),
        );
      }
    } finally {
      if (mounted) setState(() => _isGeneratingFinal = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    const gold = Color(0xFFFFD700);

    if (_isLoading) {
      return const Center(child: CircularProgressIndicator(color: gold));
    }

    return Column(
      children: [
        // Category Tabs
        Container(
          margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
          height: 44,
          decoration: BoxDecoration(
            color: Colors.white.withOpacity(0.05),
            borderRadius: BorderRadius.circular(22),
          ),
          child: TabBar(
            controller: _tabController,
            indicator: BoxDecoration(
              color: gold.withOpacity(0.8),
              borderRadius: BorderRadius.circular(22),
            ),
            labelColor: Colors.black,
            unselectedLabelColor: Colors.white54,
            labelStyle: GoogleFonts.spaceMono(
              fontSize: 10,
              fontWeight: FontWeight.bold,
            ),
            tabs: _categories
                .map((c) => Tab(text: c['label'] as String))
                .toList(),
          ),
        ).animate().fadeIn(delay: 100.ms),

        // Room Cards
        Expanded(
          child: TabBarView(
            controller: _tabController,
            children: _categories.map((cat) {
              final rooms = _roomsForCategory(cat['key'] as String);
              if (rooms.isEmpty) {
                return Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(cat['icon'] as IconData,
                          size: 48, color: Colors.white12),
                      const SizedBox(height: 12),
                      Text(
                        'No ${cat['label']} rooms',
                        style: GoogleFonts.spaceMono(
                            color: Colors.white30, fontSize: 12),
                      ),
                    ],
                  ),
                );
              }
              return ListView.builder(
                padding:
                    const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                itemCount: rooms.length,
                itemBuilder: (ctx, i) => _buildReportRoomCard(rooms[i], i),
              );
            }).toList(),
          ),
        ),

        // Final Report Button - wrapped in SafeArea for Android navbar
        SafeArea(
          top: false,
          child: Container(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 12),
            decoration: BoxDecoration(
              gradient: LinearGradient(
                begin: Alignment.topCenter,
                end: Alignment.bottomCenter,
                colors: [
                  Colors.transparent,
                  const Color(0xFF05080D).withOpacity(0.95),
                ],
              ),
            ),
            child: SizedBox(
              width: double.infinity,
              height: 52,
              child: ElevatedButton.icon(
                style: ElevatedButton.styleFrom(
                  backgroundColor:
                      _allRoomsHavePartialReport ? gold : Colors.white12,
                  foregroundColor: _allRoomsHavePartialReport
                      ? Colors.black
                      : Colors.white30,
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(14),
                  ),
                  elevation: _allRoomsHavePartialReport ? 4 : 0,
                  shadowColor: _allRoomsHavePartialReport
                      ? gold.withOpacity(0.5)
                      : Colors.transparent,
                ),
                onPressed: _allRoomsHavePartialReport && !_isGeneratingFinal
                    ? _generateFinalReport
                    : null,
                icon: _isGeneratingFinal
                    ? const SizedBox(
                        width: 20,
                        height: 20,
                        child: CircularProgressIndicator(
                            strokeWidth: 2, color: Colors.black))
                    : const Icon(Icons.auto_awesome, size: 20),
                label: Text(
                  _isGeneratingFinal
                      ? 'GENERATING...'
                      : 'GENERATE FINAL RICS REPORT',
                  style: GoogleFonts.spaceMono(
                      fontSize: 11, fontWeight: FontWeight.bold),
                ),
              ),
            ),
          ),
        ).animate().fadeIn(delay: 300.ms).slideY(begin: 0.2),
      ],
    );
  }

  Widget _buildReportRoomCard(Map<String, dynamic> room, int index) {
    final roomName = _cleanName(room['name']);
    final photoCount = room['images_count'] ?? 0;
    final audioCount = room['audio_count'] ?? 0;
    final hasPartialReport = room['has_partial_report'] == true;
    final roomId = room['id'] ?? '';

    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: GlassmorphicContainer(
        width: double.infinity,
        height: 180,
        borderRadius: 16,
        blur: 12,
        alignment: Alignment.center,
        border: 1,
        linearGradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            Colors.white.withOpacity(0.06),
            Colors.white.withOpacity(0.02),
          ],
        ),
        borderGradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            hasPartialReport
                ? const Color(0xFF00E676).withOpacity(0.5)
                : const Color(0xFFFFD700).withOpacity(0.3),
            Colors.white10,
          ],
        ),
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Header row
              Row(
                children: [
                  Expanded(
                    child: Text(
                      roomName,
                      style: GoogleFonts.outfit(
                        color: Colors.white,
                        fontWeight: FontWeight.bold,
                        fontSize: 15,
                      ),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                  if (hasPartialReport)
                    Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 8, vertical: 3),
                      decoration: BoxDecoration(
                        color: const Color(0xFF00E676).withOpacity(0.15),
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: Text(
                        '✅ REPORT',
                        style: GoogleFonts.spaceMono(
                          color: const Color(0xFF00E676),
                          fontSize: 8,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ),
                ],
              ),

              const SizedBox(height: 4),
              Text(
                '📷 $photoCount photos  •  🎤 $audioCount audio',
                style:
                    GoogleFonts.spaceMono(color: Colors.white54, fontSize: 10),
              ),

              const Spacer(),

              // 4 Action Buttons (2x2 grid)
              Row(
                children: [
                  Expanded(
                    child: _actionButton(
                      icon: Icons.photo_library,
                      label: 'View Evidence',
                      color: const Color(0xFF42A5F5),
                      onTap: () => Navigator.push(
                        context,
                        MaterialPageRoute(
                          builder: (_) => EvidenceGalleryScreen(
                            projectId: widget.projectId,
                            roomId: roomId,
                            roomName: roomName,
                          ),
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: _actionButton(
                      icon: _activeGenerations.contains(roomId)
                          ? Icons.hourglass_top
                          : Icons.auto_awesome,
                      label: _activeGenerations.contains(roomId)
                          ? (_genStatus[roomId] ?? 'Working...')
                          : 'Generate',
                      color: const Color(0xFFFFD700),
                      enabled: !_activeGenerations.contains(roomId),
                      onTap: () => _generateInBackground(roomId, roomName),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 6),
              Row(
                children: [
                  Expanded(
                    child: _actionButton(
                      icon: Icons.description,
                      label: 'View Report',
                      color: const Color(0xFF00E676),
                      enabled: hasPartialReport,
                      onTap: hasPartialReport
                          ? () => Navigator.push(
                                context,
                                MaterialPageRoute(
                                  builder: (_) => PartialReportViewerScreen(
                                    projectId: widget.projectId,
                                    roomId: roomId,
                                    roomName: roomName,
                                  ),
                                ),
                              )
                          : null,
                    ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: _actionButton(
                      icon: Icons.mic,
                      label: 'Voice Edit',
                      color: const Color(0xFFFF7043),
                      enabled: hasPartialReport,
                      onTap: hasPartialReport
                          ? () => Navigator.push(
                                context,
                                MaterialPageRoute(
                                  builder: (_) => PartialReportViewerScreen(
                                    projectId: widget.projectId,
                                    roomId: roomId,
                                    roomName: roomName,
                                    startVoiceEdit: true,
                                  ),
                                ),
                              )
                          : null,
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    ).animate().fadeIn(delay: (50 * index).ms).slideX(begin: 0.1, end: 0);
  }

  Widget _actionButton({
    required IconData icon,
    required String label,
    required Color color,
    bool enabled = true,
    VoidCallback? onTap,
  }) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: enabled ? onTap : null,
        borderRadius: BorderRadius.circular(10),
        child: Container(
          height: 36,
          decoration: BoxDecoration(
            color: enabled
                ? color.withOpacity(0.1)
                : Colors.white.withOpacity(0.03),
            borderRadius: BorderRadius.circular(10),
            border: Border.all(
              color: enabled ? color.withOpacity(0.3) : Colors.white10,
            ),
          ),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(icon, size: 14, color: enabled ? color : Colors.white24),
              const SizedBox(width: 4),
              Text(
                label,
                style: GoogleFonts.spaceMono(
                  fontSize: 8,
                  fontWeight: FontWeight.bold,
                  color: enabled ? color : Colors.white24,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
