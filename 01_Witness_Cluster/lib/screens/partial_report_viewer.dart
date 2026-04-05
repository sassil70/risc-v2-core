import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:flutter_animate/flutter_animate.dart';
import '../services/api_service.dart';

/// Partial Report Viewer — displays a room's generated partial report
/// in formatted RICS style with condition cards and voice edit functionality.
class PartialReportViewerScreen extends StatefulWidget {
  final String projectId;
  final String roomId;
  final String roomName;
  final bool startVoiceEdit;

  const PartialReportViewerScreen({
    super.key,
    required this.projectId,
    required this.roomId,
    required this.roomName,
    this.startVoiceEdit = false,
  });

  @override
  State<PartialReportViewerScreen> createState() =>
      _PartialReportViewerScreenState();
}

class _PartialReportViewerScreenState extends State<PartialReportViewerScreen> {
  final ApiService _api = ApiService();
  bool _isLoading = true;
  Map<String, dynamic>? _reportData;
  bool _isEditing = false;
  final TextEditingController _editController = TextEditingController();

  @override
  void initState() {
    super.initState();
    _loadReport();
  }

  @override
  void dispose() {
    _editController.dispose();
    super.dispose();
  }

  Future<void> _loadReport() async {
    try {
      final report =
          await _api.getPartialReport(widget.projectId, widget.roomId);
      if (mounted) {
        setState(() {
          _reportData = report;
          _isLoading = false;
        });
        if (widget.startVoiceEdit) {
          _showVoiceEditDialog();
        }
      }
    } catch (e) {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Future<void> _submitVoiceEdit(String instruction) async {
    if (instruction.trim().isEmpty) return;

    setState(() => _isEditing = true);
    try {
      final result = await _api.voiceEditReport(
          widget.projectId, widget.roomId, instruction);
      if (mounted) {
        if (result != null) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text('Edit applied!', style: GoogleFonts.spaceMono()),
              backgroundColor: const Color(0xFF00E676),
            ),
          );
          _loadReport(); // Reload the updated report
        } else {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text('Edit failed', style: GoogleFonts.spaceMono()),
              backgroundColor: Colors.redAccent,
            ),
          );
        }
      }
    } finally {
      if (mounted) setState(() => _isEditing = false);
    }
  }

  void _showVoiceEditDialog() {
    _editController.clear();
    showModalBottomSheet(
      context: context,
      backgroundColor: Colors.transparent,
      isScrollControlled: true,
      builder: (ctx) {
        return Container(
          decoration: BoxDecoration(
            color: const Color(0xFF1A1A24).withOpacity(0.97),
            borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
            border: Border(
                top: BorderSide(
                    color: const Color(0xFFFF7043).withOpacity(0.5))),
          ),
          child: Padding(
            padding: EdgeInsets.only(
              left: 24,
              right: 24,
              top: 24,
              bottom: MediaQuery.of(ctx).viewInsets.bottom + 24,
            ),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Container(
                  width: 40,
                  height: 4,
                  decoration: BoxDecoration(
                    color: Colors.white24,
                    borderRadius: BorderRadius.circular(2),
                  ),
                ),
                const SizedBox(height: 16),
                Text(
                  '🎙️ VOICE EDIT INSTRUCTION',
                  style: GoogleFonts.spaceMono(
                    color: const Color(0xFFFF7043),
                    fontSize: 12,
                    letterSpacing: 2,
                  ),
                ),
                const SizedBox(height: 8),
                Text(
                  'Describe how you want to modify the report:',
                  style:
                      GoogleFonts.outfit(color: Colors.white70, fontSize: 14),
                ),
                const SizedBox(height: 16),
                TextField(
                  controller: _editController,
                  maxLines: 3,
                  style:
                      GoogleFonts.spaceMono(color: Colors.white, fontSize: 12),
                  decoration: InputDecoration(
                    hintText: 'e.g. "Add note about damp patch on north wall"',
                    hintStyle: GoogleFonts.spaceMono(
                        color: Colors.white30, fontSize: 11),
                    filled: true,
                    fillColor: Colors.white.withOpacity(0.05),
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(12),
                      borderSide:
                          BorderSide(color: Colors.white.withOpacity(0.1)),
                    ),
                    enabledBorder: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(12),
                      borderSide:
                          BorderSide(color: Colors.white.withOpacity(0.1)),
                    ),
                    focusedBorder: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(12),
                      borderSide: const BorderSide(color: Color(0xFFFF7043)),
                    ),
                  ),
                ),
                const SizedBox(height: 16),
                SizedBox(
                  width: double.infinity,
                  height: 44,
                  child: ElevatedButton.icon(
                    style: ElevatedButton.styleFrom(
                      backgroundColor: const Color(0xFFFF7043),
                      foregroundColor: Colors.white,
                      shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(12)),
                    ),
                    onPressed: _isEditing
                        ? null
                        : () {
                            Navigator.pop(ctx);
                            _submitVoiceEdit(_editController.text);
                          },
                    icon: _isEditing
                        ? const SizedBox(
                            width: 18,
                            height: 18,
                            child: CircularProgressIndicator(
                                strokeWidth: 2, color: Colors.white))
                        : const Icon(Icons.send, size: 18),
                    label: Text(
                      _isEditing ? 'APPLYING...' : 'APPLY EDIT',
                      style: GoogleFonts.spaceMono(
                          fontSize: 11, fontWeight: FontWeight.bold),
                    ),
                  ),
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  // ── RICS Condition Color ──
  Color _crColor(int rating) {
    switch (rating) {
      case 1:
        return const Color(0xFF27AE60);
      case 2:
        return const Color(0xFFF39C12);
      case 3:
        return const Color(0xFFE74C3C);
      default:
        return Colors.grey;
    }
  }

  String _crLabel(int rating) {
    switch (rating) {
      case 1:
        return 'CR1 — Good';
      case 2:
        return 'CR2 — Repair';
      case 3:
        return 'CR3 — Urgent';
      default:
        return 'CR$rating';
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
        title: Column(
          children: [
            Text(
              "RICS ROOM REPORT",
              style: GoogleFonts.spaceMono(
                  color: gold, fontSize: 10, letterSpacing: 2),
            ),
            Text(
              widget.roomName,
              style: GoogleFonts.outfit(
                  color: Colors.white,
                  fontWeight: FontWeight.bold,
                  fontSize: 16),
            ),
          ],
        ),
        centerTitle: true,
        iconTheme: const IconThemeData(color: Colors.white),
        actions: [
          IconButton(
            icon: const Icon(Icons.mic, color: Color(0xFFFF7043)),
            onPressed: _showVoiceEditDialog,
            tooltip: 'Voice Edit',
          ),
        ],
      ),
      body: _isLoading
          ? Center(child: CircularProgressIndicator(color: gold))
          : _reportData == null
              ? _buildEmptyState(gold)
              : _buildReportBody(),
      floatingActionButton: _reportData != null
          ? FloatingActionButton(
              backgroundColor: const Color(0xFFFF7043),
              foregroundColor: Colors.white,
              onPressed: _showVoiceEditDialog,
              child: const Icon(Icons.mic),
            )
              .animate()
              .scale(delay: 300.ms, duration: 400.ms, curve: Curves.elasticOut)
          : null,
    );
  }

  Widget _buildEmptyState(Color gold) {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Icon(Icons.description, size: 64, color: Colors.white12),
          const SizedBox(height: 16),
          Text('No report generated yet',
              style:
                  GoogleFonts.spaceMono(color: Colors.white30, fontSize: 12)),
          const SizedBox(height: 24),
          ElevatedButton.icon(
            style: ElevatedButton.styleFrom(
                backgroundColor: gold, foregroundColor: Colors.black),
            onPressed: () => Navigator.pop(context),
            icon: const Icon(Icons.arrow_back, size: 16),
            label: Text('Go Back', style: GoogleFonts.spaceMono(fontSize: 11)),
          ),
        ],
      ),
    );
  }

  Widget _buildReportBody() {
    final data = _reportData!;
    // Handle both flat structure and nested "rooms" array
    Map<String, dynamic>? roomData;
    if (data.containsKey('report_chunk')) {
      final chunk = data['report_chunk'];
      if (chunk is Map<String, dynamic>) {
        if (chunk.containsKey('rooms') &&
            chunk['rooms'] is List &&
            (chunk['rooms'] as List).isNotEmpty) {
          roomData = (chunk['rooms'] as List)[0] as Map<String, dynamic>;
        } else {
          roomData = chunk;
        }
      }
    } else if (data.containsKey('rooms') &&
        data['rooms'] is List &&
        (data['rooms'] as List).isNotEmpty) {
      roomData = (data['rooms'] as List)[0] as Map<String, dynamic>;
    } else {
      roomData = data;
    }

    if (roomData == null) return _buildEmptyState(const Color(0xFFFFD700));

    final summary = roomData['inspection_summary'] ?? '';
    final elements = (roomData['elements'] as List<dynamic>?) ?? [];
    final overallRating = roomData['overall_condition_rating'] ?? 0;
    final priorityActions =
        (roomData['priority_actions'] as List<dynamic>?) ?? [];
    final limitations = (roomData['limitations'] as List<dynamic>?) ?? [];
    final notes = roomData['notes'] ?? '';

    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // ── Overall Rating Banner ──
          _buildOverallBanner(overallRating, summary),
          const SizedBox(height: 20),

          // ── Elements ──
          _sectionHeader('ELEMENT ASSESSMENT', Icons.search),
          const SizedBox(height: 8),
          ...elements.asMap().entries.map((entry) {
            return _buildElementCard(
                entry.value as Map<String, dynamic>, entry.key);
          }),

          // ── Priority Actions ──
          if (priorityActions.isNotEmpty) ...[
            const SizedBox(height: 16),
            _sectionHeader('PRIORITY ACTIONS', Icons.priority_high),
            const SizedBox(height: 8),
            _buildListCard(priorityActions, const Color(0xFFFF7043)),
          ],

          // ── Limitations ──
          if (limitations.isNotEmpty) ...[
            const SizedBox(height: 16),
            _sectionHeader('LIMITATIONS', Icons.warning_amber),
            const SizedBox(height: 8),
            _buildListCard(limitations, Colors.white38),
          ],

          // ── Notes ──
          if (notes.toString().isNotEmpty) ...[
            const SizedBox(height: 16),
            _sectionHeader('ADDITIONAL NOTES', Icons.note),
            const SizedBox(height: 8),
            _buildTextCard(notes.toString()),
          ],

          const SizedBox(height: 80), // space for FAB
        ],
      ),
    );
  }

  Widget _buildOverallBanner(int rating, String summary) {
    final color = _crColor(rating);
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [color.withOpacity(0.15), color.withOpacity(0.05)],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: color.withOpacity(0.4)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Text('OVERALL CONDITION',
                  style: GoogleFonts.spaceMono(
                      color: Colors.white54, fontSize: 10, letterSpacing: 2)),
              const Spacer(),
              Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
                decoration: BoxDecoration(
                  color: color,
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Text(_crLabel(rating),
                    style: GoogleFonts.spaceMono(
                        color: Colors.white,
                        fontSize: 10,
                        fontWeight: FontWeight.bold)),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Text(summary,
              style: GoogleFonts.outfit(
                  color: Colors.white.withOpacity(0.85),
                  fontSize: 14,
                  height: 1.6)),
        ],
      ),
    ).animate().fadeIn(duration: 400.ms);
  }

  Widget _sectionHeader(String title, IconData icon) {
    return Row(
      children: [
        Icon(icon, size: 16, color: const Color(0xFFFFD700)),
        const SizedBox(width: 8),
        Text(title,
            style: GoogleFonts.spaceMono(
                color: const Color(0xFFFFD700),
                fontSize: 11,
                letterSpacing: 2,
                fontWeight: FontWeight.bold)),
      ],
    );
  }

  Widget _buildElementCard(Map<String, dynamic> elem, int index) {
    final rating = elem['condition_rating'] ?? 1;
    final color = _crColor(rating is int ? rating : 1);
    final defects = (elem['defects_identified'] as List<dynamic>?) ?? [];
    final specialist = elem['specialist_referral']?.toString() ?? 'None';
    final needsInvestigation = elem['further_investigation_required'] == true;

    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Container(
        decoration: BoxDecoration(
          color: Colors.white.withOpacity(0.04),
          borderRadius: BorderRadius.circular(14),
          border: Border(left: BorderSide(color: color, width: 4)),
        ),
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Header
              Row(
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          elem['rics_element']?.toString() ?? '',
                          style: GoogleFonts.spaceMono(
                              color: Colors.white38,
                              fontSize: 9,
                              letterSpacing: 1),
                        ),
                        const SizedBox(height: 2),
                        Text(
                          elem['name']?.toString() ?? '',
                          style: GoogleFonts.outfit(
                              color: Colors.white,
                              fontWeight: FontWeight.bold,
                              fontSize: 15),
                        ),
                      ],
                    ),
                  ),
                  Container(
                    padding:
                        const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                    decoration: BoxDecoration(
                        color: color, borderRadius: BorderRadius.circular(6)),
                    child: Text(_crLabel(rating is int ? rating : 1),
                        style: GoogleFonts.spaceMono(
                            color: Colors.white,
                            fontSize: 9,
                            fontWeight: FontWeight.bold)),
                  ),
                ],
              ),
              const SizedBox(height: 10),

              // Description
              Text(
                elem['condition_description']?.toString() ?? '',
                style: GoogleFonts.outfit(
                    color: Colors.white.withOpacity(0.75),
                    fontSize: 13,
                    height: 1.7),
              ),

              // Defects Table
              if (defects.isNotEmpty) ...[
                const SizedBox(height: 12),
                Container(
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    color: Colors.white.withOpacity(0.03),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('DEFECTS IDENTIFIED',
                          style: GoogleFonts.spaceMono(
                              color: Colors.white38,
                              fontSize: 8,
                              letterSpacing: 1)),
                      const SizedBox(height: 6),
                      ...defects.map((d) {
                        final def = d as Map<String, dynamic>;
                        final sevColor = {
                              'Minor': const Color(0xFF27AE60),
                              'Moderate': const Color(0xFFF39C12),
                              'Significant': const Color(0xFFE74C3C),
                            }[def['severity']] ??
                            Colors.grey;
                        return Padding(
                          padding: const EdgeInsets.only(bottom: 8),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Row(
                                children: [
                                  Container(
                                      width: 6,
                                      height: 6,
                                      decoration: BoxDecoration(
                                          color: sevColor,
                                          shape: BoxShape.circle)),
                                  const SizedBox(width: 6),
                                  Expanded(
                                    child: Text(def['defect_type'] ?? '',
                                        style: GoogleFonts.outfit(
                                            color: Colors.white,
                                            fontSize: 12,
                                            fontWeight: FontWeight.w600)),
                                  ),
                                  Container(
                                    padding: const EdgeInsets.symmetric(
                                        horizontal: 6, vertical: 2),
                                    decoration: BoxDecoration(
                                      color: sevColor.withOpacity(0.15),
                                      borderRadius: BorderRadius.circular(4),
                                    ),
                                    child: Text(def['severity'] ?? '',
                                        style: GoogleFonts.spaceMono(
                                            color: sevColor,
                                            fontSize: 8,
                                            fontWeight: FontWeight.bold)),
                                  ),
                                ],
                              ),
                              const SizedBox(height: 4),
                              _defectRow(
                                  '📍', 'Location', def['location'] ?? ''),
                              _defectRow(
                                  '🔍', 'Cause', def['probable_cause'] ?? ''),
                              _defectRow('🔧', 'Action',
                                  def['recommended_action'] ?? ''),
                              _defectRow('⏱️', 'Urgency', def['urgency'] ?? ''),
                            ],
                          ),
                        );
                      }),
                    ],
                  ),
                ),
              ],

              // Specialist Referral
              if (specialist != 'None' && specialist.isNotEmpty) ...[
                const SizedBox(height: 8),
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                  decoration: BoxDecoration(
                    color: const Color(0xFFF39C12).withOpacity(0.1),
                    borderRadius: BorderRadius.circular(6),
                    border: Border.all(
                        color: const Color(0xFFF39C12).withOpacity(0.3)),
                  ),
                  child: Row(
                    children: [
                      const Icon(Icons.engineering,
                          size: 14, color: Color(0xFFF39C12)),
                      const SizedBox(width: 6),
                      Text('Specialist: $specialist',
                          style: GoogleFonts.spaceMono(
                              color: const Color(0xFFF39C12), fontSize: 10)),
                    ],
                  ),
                ),
              ],

              // Further Investigation
              if (needsInvestigation) ...[
                const SizedBox(height: 8),
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                  decoration: BoxDecoration(
                    color: const Color(0xFFE74C3C).withOpacity(0.1),
                    borderRadius: BorderRadius.circular(6),
                    border: Border.all(
                        color: const Color(0xFFE74C3C).withOpacity(0.3)),
                  ),
                  child: Row(
                    children: [
                      const Icon(Icons.warning,
                          size: 14, color: Color(0xFFE74C3C)),
                      const SizedBox(width: 6),
                      Text('Further Investigation Required',
                          style: GoogleFonts.spaceMono(
                              color: const Color(0xFFE74C3C), fontSize: 10)),
                    ],
                  ),
                ),
              ],

              // Evidence Photos — render as actual images
              if ((elem['evidence_photos'] as List<dynamic>?)?.isNotEmpty ==
                  true) ...[
                const SizedBox(height: 12),
                Text('EVIDENCE PHOTOS',
                    style: GoogleFonts.spaceMono(
                        color: Colors.white38,
                        fontSize: 8,
                        letterSpacing: 1)),
                const SizedBox(height: 6),
                SizedBox(
                  height: 120,
                  child: ListView.builder(
                    scrollDirection: Axis.horizontal,
                    itemCount: (elem['evidence_photos'] as List).length,
                    itemBuilder: (ctx, imgIdx) {
                      final photoUrl = (elem['evidence_photos'] as List)[imgIdx].toString();
                      // Build full URL: if starts with /storage/, prepend base
                      final fullUrl = photoUrl.startsWith('/storage/')
                          ? '${ApiService.baseUrl.replaceAll('/api', '')}$photoUrl'
                          : photoUrl;
                      return Padding(
                        padding: const EdgeInsets.only(right: 8),
                        child: ClipRRect(
                          borderRadius: BorderRadius.circular(8),
                          child: Image.network(
                            fullUrl,
                            width: 160,
                            height: 120,
                            fit: BoxFit.cover,
                            errorBuilder: (ctx, err, stack) => Container(
                              width: 160,
                              height: 120,
                              color: Colors.white.withOpacity(0.05),
                              child: Column(
                                mainAxisAlignment: MainAxisAlignment.center,
                                children: [
                                  const Icon(Icons.broken_image,
                                      color: Colors.white24, size: 24),
                                  const SizedBox(height: 4),
                                  Text(
                                    photoUrl.split('/').last,
                                    style: GoogleFonts.spaceMono(
                                        color: Colors.white24, fontSize: 7),
                                    textAlign: TextAlign.center,
                                    maxLines: 2,
                                    overflow: TextOverflow.ellipsis,
                                  ),
                                ],
                              ),
                            ),
                          ),
                        ),
                      );
                    },
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    ).animate().fadeIn(delay: (80 * index).ms).slideX(begin: 0.05, end: 0);
  }

  Widget _defectRow(String emoji, String label, String value) {
    if (value.isEmpty) return const SizedBox.shrink();
    return Padding(
      padding: const EdgeInsets.only(left: 12, top: 2),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(emoji, style: const TextStyle(fontSize: 10)),
          const SizedBox(width: 4),
          SizedBox(
            width: 52,
            child: Text(label,
                style:
                    GoogleFonts.spaceMono(color: Colors.white38, fontSize: 9)),
          ),
          Expanded(
            child: Text(value,
                style: GoogleFonts.outfit(color: Colors.white60, fontSize: 11)),
          ),
        ],
      ),
    );
  }

  Widget _buildListCard(List<dynamic> items, Color color) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.04),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        children: items.asMap().entries.map((entry) {
          return Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Container(
                  width: 20,
                  height: 20,
                  decoration: BoxDecoration(
                    color: color.withOpacity(0.15),
                    borderRadius: BorderRadius.circular(4),
                  ),
                  child: Center(
                    child: Text('${entry.key + 1}',
                        style: GoogleFonts.spaceMono(
                            color: color,
                            fontSize: 10,
                            fontWeight: FontWeight.bold)),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(entry.value.toString(),
                      style: GoogleFonts.outfit(
                          color: Colors.white.withOpacity(0.75),
                          fontSize: 13,
                          height: 1.5)),
                ),
              ],
            ),
          );
        }).toList(),
      ),
    ).animate().fadeIn(delay: 200.ms);
  }

  Widget _buildTextCard(String text) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.04),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Text(text,
          style: GoogleFonts.outfit(
              color: Colors.white.withOpacity(0.75),
              fontSize: 13,
              height: 1.6)),
    ).animate().fadeIn(delay: 200.ms);
  }
}
