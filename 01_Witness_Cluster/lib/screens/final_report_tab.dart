import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'dart:async';
import 'dart:io';
import 'package:google_fonts/google_fonts.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:dio/dio.dart';
import 'package:open_filex/open_filex.dart';
import 'package:path_provider/path_provider.dart';
import '../services/api_service.dart';

/// ─────────────────────────────────────────────────────
/// FINAL REPORT TAB — Stunning RICS Level 3 Report UI
/// ─────────────────────────────────────────────────────
class FinalReportTab extends StatefulWidget {
  final String? sessionId;
  final String? projectId;

  const FinalReportTab({
    super.key,
    this.sessionId,
    this.projectId,
  });

  @override
  State<FinalReportTab> createState() => _FinalReportTabState();
}

class _FinalReportTabState extends State<FinalReportTab>
    with TickerProviderStateMixin {
  final ApiService _api = ApiService();

  /// Resolved project/session ID — never null
  String get _pid => widget.projectId ?? widget.sessionId ?? '';
  // State
  bool _isGenerating = false;
  bool _hasReport = false;
  double _progress = 0.0;
  String _statusMessage = '';
  List<Map<String, dynamic>> _versions = [];
  String? _currentVersionId;
  bool _isModified = false;
  Timer? _progressTimer;

  // Approval state
  String _approvalStatus = 'pending'; // pending, approved, rejected
  List<String> _rejectionReasons = [];
  String? _approvalTimestamp;

  // Stats
  int _totalElements = 0;
  int _urgentCount = 0;
  int _attentionCount = 0;
  int _okCount = 0;
  int _totalPhotos = 0;

  // Animation
  late AnimationController _pulseController;
  late AnimationController _shimmerController;

  // Design tokens
  static const purple = Color(0xFF4D2D69);
  static const purpleLight = Color(0xFF6B4D8A);
  static const gold = Color(0xFFFFD700);
  static const bgDark = Color(0xFF0A0A14);
  static const bgCard = Color(0xFF0F172A);
  static const ratingGreen = Color(0xFF4CAF50);
  static const ratingAmber = Color(0xFFFF9800);
  static const ratingRed = Color(0xFFF44336);
  static const textPrimary = Color(0xFFEAEAEA);
  static const textSecondary = Color(0xFFA0A0B0);

  @override
  void initState() {
    super.initState();
    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1500),
    )..repeat(reverse: true);
    _shimmerController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 2000),
    )..repeat();
    _checkExistingReport();
    _loadApprovalStatus();
  }

  @override
  void dispose() {
    _pulseController.dispose();
    _shimmerController.dispose();
    _progressTimer?.cancel();
    super.dispose();
  }

  // ═══════════════════════════════════════════
  // API LAYER
  // ═══════════════════════════════════════════

  Future<void> _checkExistingReport() async {
    final pid = _pid;
    try {
      final res = await _api.getFinalReportMd(pid);
      if (res != null && res['content'] != null) {
        setState(() {
          _hasReport = true;
          _statusMessage = 'Report loaded';
        });
        _loadVersions();
      }
    } catch (_) {}
  }

  Future<void> _loadVersions() async {
    final pid = _pid;
    try {
      final res = await _api.getReportVersions(pid);
      if (res != null) {
        setState(() {
          _versions = List<Map<String, dynamic>>.from(res['versions'] ?? []);
          // Use active_version_id from backend, fallback to latest
          _currentVersionId = res['active_version_id'] as String? ??
              (_versions.isNotEmpty ? _versions.last['version_id'] : null);
        });
      }
    } catch (_) {}
  }

  Future<void> _viewVersionPdf(String versionId) async {
    final pid = _pid;
    final baseUrl = ApiService.baseUrl;
    final url = '$baseUrl/projects/$pid/report-version/$versionId/pdf';
    try {
      final dir = await getTemporaryDirectory();
      final path = '${dir.path}/RICS_Report_$versionId.pdf';
      await Dio().download(url, path);
      await OpenFilex.open(path);
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to open $versionId PDF: $e')),
        );
      }
    }
  }

  Future<void> _setActiveVersion(String versionId) async {
    final pid = _pid;
    try {
      await Dio().put(
        '${ApiService.baseUrl}/projects/$pid/report-active-version',
        data: {'version_id': versionId},
      );
      setState(() => _currentVersionId = versionId);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('✅ $versionId set as active for editing'),
            backgroundColor: const Color(0xFF4CAF50),
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to set active: $e')),
        );
      }
    }
  }

  Future<void> _generateReport() async {
    final pid = _pid;
    setState(() {
      _isGenerating = true;
      _progress = 0.0;
      _statusMessage = 'Initializing AI engine...';
    });

    // Animated progress simulation (real progress comes from API)
    _progressTimer = Timer.periodic(const Duration(milliseconds: 200), (t) {
      if (!mounted || !_isGenerating) {
        t.cancel();
        return;
      }
      setState(() {
        if (_progress < 0.15) {
          _progress += 0.008;
          _statusMessage = 'Gathering room data...';
        } else if (_progress < 0.35) {
          _progress += 0.006;
          _statusMessage = 'Mapping rooms → RICS elements...';
        } else if (_progress < 0.65) {
          _progress += 0.004;
          _statusMessage = 'Gemini 3.1 generating narratives...';
        } else if (_progress < 0.80) {
          _progress += 0.003;
          _statusMessage = 'Computing condition ratings...';
        } else if (_progress < 0.92) {
          _progress += 0.002;
          _statusMessage = 'Assembling Markdown report...';
        } else if (_progress < 0.98) {
          _progress += 0.001;
          _statusMessage = 'Rendering PDF via PyMuPDF...';
        }
      });
    });

    try {
      final res = await _api.generateFinalReport(pid);
      _progressTimer?.cancel();

      if (res != null && res['status'] == 'success') {
        setState(() {
          _isGenerating = false;
          _hasReport = true;
          _progress = 1.0;
          _statusMessage = 'Report generated successfully!';
          _totalElements = res['stats']?['total_elements'] ?? 0;
          _urgentCount = res['stats']?['urgent_items'] ?? 0;
          _attentionCount = res['stats']?['attention_items'] ?? 0;
          _okCount = (_totalElements - _urgentCount - _attentionCount).clamp(0, _totalElements);
          _totalPhotos = res['stats']?['total_photos'] ?? 0;
          _isModified = false;
        });
        _loadVersions();
      } else {
        setState(() {
          _isGenerating = false;
          _statusMessage = 'Generation failed. Tap to retry.';
        });
      }
    } catch (e) {
      _progressTimer?.cancel();
      setState(() {
        _isGenerating = false;
        _statusMessage = 'Error: ${e.toString().length > 80 ? e.toString().substring(0, 80) : e.toString()}';
      });
    }
  }

  Future<void> _saveReport({bool saveAs = false}) async {
    final pid = _pid;
    final changeLabel = saveAs ? 'Saved as copy — ${DateTime.now().toIso8601String().substring(0, 16)}' : 'Quick save';

    try {
      final mdRes = await _api.getFinalReportMd(pid);
      if (mdRes == null) return;

      final content = mdRes['content'] as String;
      await _api.updateFinalReportMd(
        pid,
        content,
        changeLabel,
      );

      setState(() => _isModified = false);
      _loadVersions();

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              saveAs ? '📄 Saved as new version' : '💾 Report saved',
              style: GoogleFonts.spaceMono(color: Colors.white),
            ),
            backgroundColor: ratingGreen,
            behavior: SnackBarBehavior.floating,
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Save failed: $e'),
            backgroundColor: ratingRed,
          ),
        );
      }
    }
  }

  Future<void> _markFinal(String versionId) async {
    final pid = _pid;
    try {
      await _api.markReportFinal(pid, versionId);
      _loadVersions();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              '✅ $versionId marked as FINAL',
              style: GoogleFonts.spaceMono(color: Colors.white),
            ),
            backgroundColor: ratingGreen,
          ),
        );
      }
    } catch (_) {}
  }

  Future<void> _loadApprovalStatus() async {
    final pid = _pid;
    try {
      final res = await _api.getApprovalStatus(pid);
      if (res != null && mounted) {
        setState(() {
          _approvalStatus = res['status'] ?? 'pending';
          _rejectionReasons = List<String>.from(res['rejection_reasons'] ?? []);
          _approvalTimestamp = res['timestamp'];
        });
      }
    } catch (_) {}
  }

  Future<void> _handleApproval() async {
    final pid = _pid;
    final result = await _api.approveReport(pid, versionId: _currentVersionId);
    if (result != null && mounted) {
      setState(() => _approvalStatus = 'approved');
      _loadApprovalStatus();
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('✅ Report APPROVED by Surveyor', style: GoogleFonts.spaceMono(color: Colors.white)),
          backgroundColor: ratingGreen,
        ),
      );
    }
  }

  Future<void> _handleRejection() async {
    final controller = TextEditingController();
    final reasons = await showDialog<List<String>>(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: const Color(0xFF1A1A2E),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        title: Text('Rejection Reasons', style: GoogleFonts.outfit(color: Colors.white, fontWeight: FontWeight.bold)),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text('Describe why this report needs revision:', style: GoogleFonts.spaceMono(color: Colors.white54, fontSize: 11)),
            const SizedBox(height: 12),
            TextField(
              controller: controller,
              maxLines: 4,
              style: GoogleFonts.spaceMono(color: Colors.white, fontSize: 12),
              decoration: InputDecoration(
                hintText: 'e.g. Missing photo evidence for D2...\nIncorrect CR rating for E3...',
                hintStyle: GoogleFonts.spaceMono(color: Colors.white24, fontSize: 10),
                filled: true,
                fillColor: Colors.white.withOpacity(0.05),
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide(color: Colors.white.withOpacity(0.1))),
                focusedBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: const BorderSide(color: Color(0xFFF44336))),
              ),
            ),
          ],
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: Text('Cancel', style: GoogleFonts.spaceMono(color: Colors.white54))),
          ElevatedButton(
            onPressed: () => Navigator.pop(ctx, controller.text.split('\n').where((l) => l.trim().isNotEmpty).toList()),
            style: ElevatedButton.styleFrom(backgroundColor: ratingRed),
            child: Text('REJECT', style: GoogleFonts.spaceMono(fontWeight: FontWeight.bold)),
          ),
        ],
      ),
    );
    if (reasons == null || reasons.isEmpty) return;
    final pid = _pid;
    final result = await _api.rejectReport(pid, reasons: reasons, versionId: _currentVersionId);
    if (result != null && mounted) {
      setState(() {
        _approvalStatus = 'rejected';
        _rejectionReasons = reasons;
      });
      _loadApprovalStatus();
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('❌ Report REJECTED — needs revision', style: GoogleFonts.spaceMono(color: Colors.white)),
          backgroundColor: ratingRed,
        ),
      );
    }
  }

  // ═══════════════════════════════════════════
  // BUILD UI
  // ═══════════════════════════════════════════

  @override
  Widget build(BuildContext context) {
    return Container(
      color: bgDark,
      child: _isGenerating
          ? _buildGeneratingView()
          : _hasReport
              ? _buildReportDashboard()
              : _buildEmptyState(),
    );
  }

  // ─── EMPTY STATE ───
  Widget _buildEmptyState() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          // Animated icon
          AnimatedBuilder(
            animation: _pulseController,
            builder: (_, __) => Transform.scale(
              scale: 1.0 + (_pulseController.value * 0.1),
              child: Container(
                width: 120,
                height: 120,
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    colors: [purple, purpleLight],
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                  ),
                  shape: BoxShape.circle,
                  boxShadow: [
                    BoxShadow(
                      color: purple.withOpacity(0.4 + _pulseController.value * 0.3),
                      blurRadius: 30 + (_pulseController.value * 20),
                      spreadRadius: 5,
                    ),
                  ],
                ),
                child: const Icon(
                  Icons.description_outlined,
                  color: Colors.white,
                  size: 50,
                ),
              ),
            ),
          ),
          const SizedBox(height: 32),
          Text(
            'RICS Level 3 Report',
            style: GoogleFonts.outfit(
              fontSize: 28,
              fontWeight: FontWeight.w700,
              color: Colors.white,
            ),
          ).animate().fadeIn(duration: 600.ms).slideY(begin: 0.2),
          const SizedBox(height: 12),
          Text(
            'Generate a professional survey report\nfrom your inspection data',
            textAlign: TextAlign.center,
            style: GoogleFonts.spaceMono(
              fontSize: 13,
              color: textSecondary,
              height: 1.6,
            ),
          ).animate().fadeIn(delay: 200.ms, duration: 600.ms),
          const SizedBox(height: 40),

          // Generate button
          GestureDetector(
            onTap: _generateReport,
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 40, vertical: 16),
              decoration: BoxDecoration(
                gradient: const LinearGradient(
                  colors: [purple, purpleLight],
                ),
                borderRadius: BorderRadius.circular(16),
                boxShadow: [
                  BoxShadow(
                    color: purple.withOpacity(0.5),
                    blurRadius: 20,
                    offset: const Offset(0, 8),
                  ),
                ],
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Icon(Icons.auto_awesome, color: gold, size: 22),
                  const SizedBox(width: 12),
                  Text(
                    'GENERATE REPORT',
                    style: GoogleFonts.outfit(
                      fontSize: 16,
                      fontWeight: FontWeight.w700,
                      color: Colors.white,
                      letterSpacing: 1.5,
                    ),
                  ),
                ],
              ),
            ),
          ).animate().fadeIn(delay: 400.ms, duration: 600.ms).scale(begin: const Offset(0.9, 0.9)),

          const SizedBox(height: 24),
          Text(
            'Estimated time: ~45 seconds',
            style: GoogleFonts.spaceMono(fontSize: 11, color: textSecondary),
          ).animate().fadeIn(delay: 600.ms),
        ],
      ),
    );
  }

  // ─── GENERATING VIEW ───
  Widget _buildGeneratingView() {
    final percentage = (_progress * 100).toInt();
    final estimatedRemaining = _progress > 0.1
        ? '${((1.0 - _progress) * 45).toInt()}s remaining'
        : 'Calculating...';

    return Center(
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 32),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            // Animated brain icon
            AnimatedBuilder(
              animation: _shimmerController,
              builder: (_, __) => Container(
                width: 100,
                height: 100,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  gradient: SweepGradient(
                    startAngle: _shimmerController.value * 6.28,
                    colors: const [purple, gold, purpleLight, purple],
                  ),
                  boxShadow: [
                    BoxShadow(
                      color: gold.withOpacity(0.3),
                      blurRadius: 30,
                      spreadRadius: 5,
                    ),
                  ],
                ),
                child: const Icon(Icons.psychology, color: Colors.white, size: 45),
              ),
            ),
            const SizedBox(height: 40),

            // Progress bar
            Container(
              height: 8,
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(4),
                color: Colors.white.withOpacity(0.1),
              ),
              child: ClipRRect(
                borderRadius: BorderRadius.circular(4),
                child: LinearProgressIndicator(
                  value: _progress,
                  backgroundColor: Colors.transparent,
                  valueColor: AlwaysStoppedAnimation<Color>(
                    _progress < 0.5 ? gold : ratingGreen,
                  ),
                ),
              ),
            ),
            const SizedBox(height: 16),

            // Percentage + time
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  '$percentage%',
                  style: GoogleFonts.outfit(
                    fontSize: 32,
                    fontWeight: FontWeight.w800,
                    color: gold,
                  ),
                ),
                Text(
                  estimatedRemaining,
                  style: GoogleFonts.spaceMono(
                    fontSize: 12,
                    color: textSecondary,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 24),

            // Status message
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
              decoration: BoxDecoration(
                color: bgCard,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: gold.withOpacity(0.2)),
              ),
              child: Row(
                children: [
                  SizedBox(
                    width: 18,
                    height: 18,
                    child: CircularProgressIndicator(
                      strokeWidth: 2,
                      valueColor: AlwaysStoppedAnimation<Color>(gold),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Text(
                      _statusMessage,
                      style: GoogleFonts.spaceMono(
                        fontSize: 12,
                        color: textPrimary,
                      ),
                    ),
                  ),
                ],
              ),
            ).animate(onPlay: (c) => c.repeat()).shimmer(
              duration: 2000.ms,
              color: gold.withOpacity(0.1),
            ),

            const SizedBox(height: 32),

            // Phase indicators
            _buildPhaseIndicators(),
          ],
        ),
      ),
    );
  }

  Widget _buildPhaseIndicators() {
    final phases = [
      {'label': 'Gather', 'threshold': 0.15, 'icon': Icons.storage},
      {'label': 'Map', 'threshold': 0.35, 'icon': Icons.account_tree},
      {'label': 'AI Narratives', 'threshold': 0.65, 'icon': Icons.psychology},
      {'label': 'Ratings', 'threshold': 0.80, 'icon': Icons.analytics},
      {'label': 'Markdown', 'threshold': 0.92, 'icon': Icons.code},
      {'label': 'PDF', 'threshold': 1.0, 'icon': Icons.picture_as_pdf},
    ];

    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceEvenly,
      children: phases.map((p) {
        final done = _progress >= (p['threshold'] as double);
        final active = !done && _progress >= ((p['threshold'] as double) - 0.15);
        return Column(
          children: [
            Container(
              width: 36,
              height: 36,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: done
                    ? ratingGreen
                    : active
                        ? gold.withOpacity(0.3)
                        : Colors.white.withOpacity(0.05),
                border: active
                    ? Border.all(color: gold, width: 2)
                    : null,
              ),
              child: Icon(
                p['icon'] as IconData,
                size: 16,
                color: done ? Colors.white : active ? gold : textSecondary,
              ),
            ),
            const SizedBox(height: 4),
            Text(
              p['label'] as String,
              style: GoogleFonts.spaceMono(
                fontSize: 8,
                color: done ? ratingGreen : textSecondary,
                fontWeight: done ? FontWeight.bold : FontWeight.normal,
              ),
            ),
          ],
        );
      }).toList(),
    );
  }

  // ─── REPORT DASHBOARD ───
  Widget _buildReportDashboard() {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Approval Banner
          _buildApprovalBanner(),
          const SizedBox(height: 12),

          // Header
          _buildHeader(),
          const SizedBox(height: 16),

          // Condition summary cards
          _buildConditionCards(),
          const SizedBox(height: 16),

          // Action buttons row
          _buildActionButtons(),
          const SizedBox(height: 20),

          // Versions list
          _buildVersionsList(),
        ],
      ),
    );
  }

  // ─── APPROVAL BANNER ───
  Widget _buildApprovalBanner() {
    if (_approvalStatus == 'approved') {
      return Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          gradient: LinearGradient(
            colors: [ratingGreen.withOpacity(0.15), ratingGreen.withOpacity(0.05)],
          ),
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: ratingGreen.withOpacity(0.4)),
        ),
        child: Row(
          children: [
            const Icon(Icons.verified, color: ratingGreen, size: 32),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('SURVEYOR APPROVED', style: GoogleFonts.spaceMono(color: ratingGreen, fontSize: 12, fontWeight: FontWeight.bold, letterSpacing: 2)),
                  if (_approvalTimestamp != null)
                    Text(_approvalTimestamp!.substring(0, 16).replaceAll('T', ' '), style: GoogleFonts.spaceMono(color: Colors.white38, fontSize: 9)),
                ],
              ),
            ),
            IconButton(
              icon: const Icon(Icons.undo, color: Colors.white30, size: 20),
              onPressed: () {
                setState(() => _approvalStatus = 'pending');
              },
              tooltip: 'Reset approval',
            ),
          ],
        ),
      ).animate().fadeIn(duration: 400.ms).slideY(begin: -0.1);
    }

    if (_approvalStatus == 'rejected') {
      return Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          gradient: LinearGradient(
            colors: [ratingRed.withOpacity(0.15), ratingRed.withOpacity(0.05)],
          ),
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: ratingRed.withOpacity(0.4)),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.cancel, color: ratingRed, size: 28),
                const SizedBox(width: 12),
                Expanded(
                  child: Text('REVISION REQUIRED', style: GoogleFonts.spaceMono(color: ratingRed, fontSize: 12, fontWeight: FontWeight.bold, letterSpacing: 2)),
                ),
                TextButton(
                  onPressed: _handleApproval,
                  child: Text('APPROVE NOW', style: GoogleFonts.spaceMono(color: ratingGreen, fontSize: 9, fontWeight: FontWeight.bold)),
                ),
              ],
            ),
            if (_rejectionReasons.isNotEmpty) ...[
              const SizedBox(height: 8),
              ...(_rejectionReasons.map((r) => Padding(
                padding: const EdgeInsets.only(left: 40, bottom: 4),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('• ', style: GoogleFonts.spaceMono(color: ratingRed, fontSize: 11)),
                    Expanded(child: Text(r, style: GoogleFonts.outfit(color: Colors.white70, fontSize: 12))),
                  ],
                ),
              ))),
            ],
          ],
        ),
      ).animate().fadeIn(duration: 400.ms).slideY(begin: -0.1);
    }

    // Pending state — show action buttons
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [gold.withOpacity(0.1), gold.withOpacity(0.03)],
        ),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: gold.withOpacity(0.3)),
      ),
      child: Row(
        children: [
          Icon(Icons.rate_review, color: gold, size: 24),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('SURVEYOR REVIEW', style: GoogleFonts.spaceMono(color: gold, fontSize: 10, fontWeight: FontWeight.bold, letterSpacing: 2)),
                const SizedBox(height: 2),
                Text('Review and approve or reject this report', style: GoogleFonts.outfit(color: Colors.white54, fontSize: 11)),
              ],
            ),
          ),
          const SizedBox(width: 8),
          ElevatedButton(
            onPressed: _handleApproval,
            style: ElevatedButton.styleFrom(
              backgroundColor: ratingGreen,
              foregroundColor: Colors.white,
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
            ),
            child: Text('✅', style: GoogleFonts.spaceMono(fontSize: 16)),
          ),
          const SizedBox(width: 6),
          ElevatedButton(
            onPressed: _handleRejection,
            style: ElevatedButton.styleFrom(
              backgroundColor: ratingRed.withOpacity(0.8),
              foregroundColor: Colors.white,
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
            ),
            child: Text('❌', style: GoogleFonts.spaceMono(fontSize: 16)),
          ),
        ],
      ),
    ).animate().fadeIn(delay: 200.ms, duration: 400.ms);
  }

  Widget _buildHeader() {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          colors: [purple, purpleLight],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(20),
        boxShadow: [
          BoxShadow(
            color: purple.withOpacity(0.4),
            blurRadius: 20,
            offset: const Offset(0, 8),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.verified, color: gold, size: 28),
              const SizedBox(width: 10),
              Text(
                'RICS Level 3 Report',
                style: GoogleFonts.outfit(
                  fontSize: 22,
                  fontWeight: FontWeight.w700,
                  color: Colors.white,
                ),
              ),
              const Spacer(),
              if (_isModified)
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                  decoration: BoxDecoration(
                    color: ratingAmber.withOpacity(0.2),
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: ratingAmber),
                  ),
                  child: Text(
                    'MODIFIED',
                    style: GoogleFonts.spaceMono(
                      fontSize: 9,
                      fontWeight: FontWeight.bold,
                      color: ratingAmber,
                    ),
                  ),
                ),
            ],
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              _buildStatChip(Icons.grid_view, '$_totalElements', 'Elements'),
              const SizedBox(width: 12),
              _buildStatChip(Icons.camera_alt, '$_totalPhotos', 'Photos'),
              const SizedBox(width: 12),
              _buildStatChip(Icons.history, '${_versions.length}', 'Versions'),
            ],
          ),
          const SizedBox(height: 8),
          if (_currentVersionId != null)
            Text(
              'Current: $_currentVersionId',
              style: GoogleFonts.spaceMono(
                fontSize: 10,
                color: Colors.white60,
              ),
            ),
        ],
      ),
    ).animate().fadeIn(duration: 400.ms).slideY(begin: 0.1);
  }

  Widget _buildStatChip(IconData icon, String value, String label) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.1),
        borderRadius: BorderRadius.circular(10),
      ),
      child: Row(
        children: [
          Icon(icon, color: gold, size: 16),
          const SizedBox(width: 6),
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                value,
                style: GoogleFonts.outfit(
                  fontSize: 16,
                  fontWeight: FontWeight.w700,
                  color: Colors.white,
                ),
              ),
              Text(
                label,
                style: GoogleFonts.spaceMono(
                  fontSize: 8,
                  color: Colors.white60,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildConditionCards() {
    return Row(
      children: [
        Expanded(
          child: _buildConditionCard(
            'URGENT',
            _urgentCount,
            ratingRed,
            Icons.warning_amber_rounded,
          ),
        ),
        const SizedBox(width: 8),
        Expanded(
          child: _buildConditionCard(
            'ATTENTION',
            _attentionCount,
            ratingAmber,
            Icons.info_outline,
          ),
        ),
        const SizedBox(width: 8),
        Expanded(
          child: _buildConditionCard(
            'OK',
            _okCount,
            ratingGreen,
            Icons.check_circle_outline,
          ),
        ),
      ],
    ).animate().fadeIn(delay: 200.ms, duration: 400.ms);
  }

  Widget _buildConditionCard(String label, int count, Color color, IconData icon) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: bgCard,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: color.withOpacity(0.3)),
      ),
      child: Column(
        children: [
          Icon(icon, color: color, size: 28),
          const SizedBox(height: 8),
          Text(
            '$count',
            style: GoogleFonts.outfit(
              fontSize: 28,
              fontWeight: FontWeight.w800,
              color: color,
            ),
          ),
          Text(
            label,
            style: GoogleFonts.spaceMono(
              fontSize: 9,
              fontWeight: FontWeight.bold,
              color: textSecondary,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildActionButtons() {
    return Column(
      children: [
        // PDF Access row: View PDF + Download + Share
        Row(
          children: [
            Expanded(
              child: _buildActionBtn(
                icon: Icons.picture_as_pdf,
                label: 'VIEW PDF',
                color: const Color(0xFFE53935),
                onTap: _viewPdf,
              ),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: _buildActionBtn(
                icon: Icons.download,
                label: 'DOWNLOAD',
                color: const Color(0xFF43A047),
                onTap: _downloadPdf,
              ),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: _buildActionBtn(
                icon: Icons.share,
                label: 'SHARE',
                color: const Color(0xFF1E88E5),
                onTap: _sharePdf,
              ),
            ),
          ],
        ),
        const SizedBox(height: 8),
        // Primary row: Save + Save As
        Row(
          children: [
            Expanded(
              child: _buildActionBtn(
                icon: Icons.save,
                label: 'SAVE',
                color: ratingGreen,
                onTap: () => _saveReport(),
              ),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: _buildActionBtn(
                icon: Icons.save_as,
                label: 'SAVE AS',
                color: purpleLight,
                onTap: () => _saveReport(saveAs: true),
              ),
            ),
          ],
        ),
        const SizedBox(height: 8),
        // Secondary row: Regenerate + Voice Edit + Open Web
        Row(
          children: [
            Expanded(
              child: _buildActionBtn(
                icon: Icons.refresh,
                label: 'REGENERATE',
                color: ratingAmber,
                onTap: _generateReport,
              ),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: _buildActionBtn(
                icon: Icons.mic,
                label: 'VOICE EDIT',
                color: gold,
                textColor: bgDark,
                onTap: () => _showVoiceEditDialog(),
              ),
            ),
          ],
        ),
        const SizedBox(height: 8),
        // Third row: Section Editor + Web Editor
        Row(
          children: [
            Expanded(
              child: _buildActionBtn(
                icon: Icons.edit_document,
                label: 'EDIT SECTIONS',
                color: Color(0xFF2D8CFF),
                onTap: () => _openSectionEditor(),
              ),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: _buildActionBtn(
                icon: Icons.open_in_browser,
                label: 'WEB EDITOR',
                color: purple,
                onTap: () => _openWebEditor(),
              ),
            ),
          ],
        ),
        const SizedBox(height: 8),
        // Fourth row: Photo Reorder
        Row(
          children: [
            Expanded(
              child: _buildActionBtn(
                icon: Icons.photo_library,
                label: 'REORDER PHOTOS',
                color: Color(0xFF00BCD4),
                onTap: () => _openPhotoReorder(),
              ),
            ),
          ],
        ),
      ],
    ).animate().fadeIn(delay: 400.ms, duration: 400.ms);
  }

  Widget _buildActionBtn({
    required IconData icon,
    required String label,
    required Color color,
    Color textColor = Colors.white,
    required VoidCallback onTap,
  }) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 14),
        decoration: BoxDecoration(
          color: color.withOpacity(0.15),
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: color.withOpacity(0.4)),
        ),
        child: Column(
          children: [
            Icon(icon, color: color, size: 22),
            const SizedBox(height: 4),
            Text(
              label,
              style: GoogleFonts.spaceMono(
                fontSize: 9,
                fontWeight: FontWeight.bold,
                color: color,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildVersionsList() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          '📦 VERSIONS',
          style: GoogleFonts.spaceMono(
            fontSize: 12,
            fontWeight: FontWeight.bold,
            color: gold,
            letterSpacing: 2,
          ),
        ),
        const SizedBox(height: 10),
        if (_versions.isEmpty)
          Container(
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
              color: bgCard,
              borderRadius: BorderRadius.circular(12),
            ),
            child: Center(
              child: Text(
                'No versions yet. Generate a report first.',
                style: GoogleFonts.spaceMono(
                  fontSize: 11,
                  color: textSecondary,
                ),
              ),
            ),
          )
        else
          ..._versions.reversed.map((v) => _buildVersionItem(v)),
      ],
    ).animate().fadeIn(delay: 600.ms, duration: 400.ms);
  }

  Widget _buildVersionItem(Map<String, dynamic> v) {
    final isFinal = v['is_final'] == true;
    final isActive = v['version_id'] == _currentVersionId;
    final hasPdf = v['pdf_path'] != null;
    final pageCount = v['page_count'] ?? 0;
    final pdfSize = v['pdf_size_kb'] ?? 0;
    final photoCount = v['photo_count'] ?? 0;

    return GestureDetector(
      onTap: () => _viewVersionPdf(v['version_id']),
      onLongPress: () {
        _setActiveVersion(v['version_id']);
      },
      child: Container(
        margin: const EdgeInsets.only(bottom: 8),
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: isActive ? purple.withOpacity(0.15) : bgCard,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(
            color: isFinal
                ? ratingGreen
                : isActive
                    ? gold.withOpacity(0.6)
                    : Colors.white.withOpacity(0.05),
            width: isFinal ? 2 : isActive ? 1.5 : 1,
          ),
        ),
        child: Row(
          children: [
            // Version icon
            Container(
              width: 36,
              height: 36,
              decoration: BoxDecoration(
                color: isFinal
                    ? ratingGreen.withOpacity(0.2)
                    : isActive
                        ? gold.withOpacity(0.2)
                        : purple.withOpacity(0.2),
                shape: BoxShape.circle,
              ),
              child: Icon(
                isFinal
                    ? Icons.verified
                    : isActive
                        ? Icons.edit_note
                        : Icons.description_outlined,
                color: isFinal ? ratingGreen : isActive ? gold : purpleLight,
                size: 18,
              ),
            ),
            const SizedBox(width: 12),

            // Info
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Text(
                        v['version_id'] ?? '',
                        style: GoogleFonts.outfit(
                          fontSize: 14,
                          fontWeight: FontWeight.w700,
                          color: Colors.white,
                        ),
                      ),
                      if (isActive && !isFinal) ...[
                        const SizedBox(width: 6),
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                          decoration: BoxDecoration(
                            color: gold.withOpacity(0.2),
                            borderRadius: BorderRadius.circular(6),
                            border: Border.all(color: gold.withOpacity(0.4)),
                          ),
                          child: Text(
                            'ACTIVE',
                            style: GoogleFonts.spaceMono(
                              fontSize: 7,
                              fontWeight: FontWeight.bold,
                              color: gold,
                            ),
                          ),
                        ),
                      ],
                      if (isFinal) ...[
                        const SizedBox(width: 6),
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                          decoration: BoxDecoration(
                            color: ratingGreen,
                            borderRadius: BorderRadius.circular(6),
                          ),
                          child: Text(
                            'FINAL',
                            style: GoogleFonts.spaceMono(
                              fontSize: 8,
                              fontWeight: FontWeight.bold,
                              color: Colors.white,
                            ),
                          ),
                        ),
                      ],
                    ],
                  ),
                  const SizedBox(height: 2),
                  Text(
                    v['label'] ?? '',
                    style: GoogleFonts.spaceMono(
                      fontSize: 10,
                      color: textSecondary,
                    ),
                  ),
                  // Metadata row: date + stats
                  Row(
                    children: [
                      if (v['timestamp'] != null)
                        Text(
                          (v['timestamp'] as String).substring(0, 16),
                          style: GoogleFonts.spaceMono(
                            fontSize: 9,
                            color: textSecondary.withOpacity(0.6),
                          ),
                        ),
                      if (pageCount > 0) ...[
                        const SizedBox(width: 8),
                        Text(
                          '${pageCount}pg',
                          style: GoogleFonts.spaceMono(
                            fontSize: 8,
                            color: purpleLight,
                          ),
                        ),
                      ],
                      if (photoCount > 0) ...[
                        const SizedBox(width: 6),
                        Text(
                          '📷$photoCount',
                          style: GoogleFonts.spaceMono(fontSize: 8),
                        ),
                      ],
                      if (pdfSize > 0) ...[
                        const SizedBox(width: 6),
                        Text(
                          '${pdfSize}KB',
                          style: GoogleFonts.spaceMono(
                            fontSize: 8,
                            color: textSecondary.withOpacity(0.5),
                          ),
                        ),
                      ],
                    ],
                  ),
                  Text(
                    hasPdf ? 'Tap to view • Long-press to set active' : 'No PDF available',
                    style: GoogleFonts.spaceMono(
                      fontSize: 8,
                      color: hasPdf ? gold.withOpacity(0.6) : ratingAmber.withOpacity(0.6),
                      fontStyle: FontStyle.italic,
                    ),
                  ),
                ],
              ),
            ),

            // Actions: View PDF + Mark as Final
            if (hasPdf)
              IconButton(
                icon: const Icon(Icons.picture_as_pdf, color: Color(0xFFE53935), size: 20),
                tooltip: 'View PDF',
                onPressed: () => _viewVersionPdf(v['version_id']),
              ),
            if (!isFinal)
              IconButton(
                icon: const Icon(Icons.check_circle_outline, color: ratingGreen, size: 20),
                tooltip: 'Mark as Final',
                onPressed: () => _markFinal(v['version_id']),
              ),
          ],
        ),
      ),
    );
  }

  // ─── DIALOGS ───

  void _showVoiceEditDialog() {
    final textController = TextEditingController();
    bool isProcessing = false;
    String? previewText;
    
    showDialog(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (context, setDialogState) => AlertDialog(
          backgroundColor: bgCard,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
          title: Row(
            children: [
              const Icon(Icons.mic, color: gold, size: 24),
              const SizedBox(width: 10),
              Text(
                'Voice Edit',
                style: GoogleFonts.outfit(
                  color: Colors.white,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ],
          ),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Type or dictate your edit command:',
                  style: GoogleFonts.spaceMono(
                    color: textSecondary,
                    fontSize: 11,
                  ),
                ),
                const SizedBox(height: 8),
                // Examples
                Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: purple.withOpacity(0.15),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Text(
                    '💡 Examples:\n'
                    '• "Add note to D2: visible moss on north elevation"\n'
                    '• "Change rating of E1 to 3"\n'
                    '• "Edit section F4 heating — boiler is 15 years old"',
                    style: GoogleFonts.spaceMono(
                      color: purpleLight,
                      fontSize: 9,
                      height: 1.5,
                    ),
                  ),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: textController,
                  maxLines: 3,
                  style: GoogleFonts.spaceMono(color: Colors.white, fontSize: 12),
                  decoration: InputDecoration(
                    hintText: 'Type your voice command...',
                    hintStyle: GoogleFonts.spaceMono(color: textSecondary, fontSize: 11),
                    filled: true,
                    fillColor: bgDark,
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(12),
                      borderSide: BorderSide(color: gold.withOpacity(0.3)),
                    ),
                    enabledBorder: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(12),
                      borderSide: BorderSide(color: gold.withOpacity(0.3)),
                    ),
                    focusedBorder: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(12),
                      borderSide: const BorderSide(color: gold),
                    ),
                    suffixIcon: IconButton(
                      icon: const Icon(Icons.mic, color: gold),
                      tooltip: 'Voice input (coming soon)',
                      onPressed: () {},
                    ),
                  ),
                ),
                if (isProcessing) ...[
                  const SizedBox(height: 16),
                  const Center(child: CircularProgressIndicator(color: gold)),
                  const SizedBox(height: 8),
                  Center(
                    child: Text(
                      'Gemini is processing your edit...',
                      style: GoogleFonts.spaceMono(color: textSecondary, fontSize: 10),
                    ),
                  ),
                ],
                if (previewText != null) ...[
                  const SizedBox(height: 12),
                  Text(
                    '✅ Edit Applied:',
                    style: GoogleFonts.spaceMono(
                      color: ratingGreen,
                      fontSize: 11,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Container(
                    padding: const EdgeInsets.all(8),
                    constraints: const BoxConstraints(maxHeight: 120),
                    decoration: BoxDecoration(
                      color: bgDark,
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: SingleChildScrollView(
                      child: Text(
                        previewText!,
                        style: GoogleFonts.spaceMono(color: Colors.white70, fontSize: 9),
                      ),
                    ),
                  ),
                ],
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(ctx),
              child: Text(
                'CANCEL',
                style: GoogleFonts.outfit(color: textSecondary, fontWeight: FontWeight.w600),
              ),
            ),
            if (previewText == null)
              ElevatedButton.icon(
                icon: const Icon(Icons.auto_fix_high, size: 16),
                label: Text(
                  'APPLY',
                  style: GoogleFonts.outfit(fontWeight: FontWeight.w700),
                ),
                style: ElevatedButton.styleFrom(
                  backgroundColor: gold,
                  foregroundColor: bgDark,
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                ),
                onPressed: isProcessing ? null : () async {
                  if (textController.text.trim().isEmpty) return;
                  setDialogState(() { isProcessing = true; });
                  try {
                    final pid = _pid;
                    // Send with confirm=true to save edit + regenerate PDF
                    final res = await _api.voiceEditFinalReport(pid, textController.text.trim(), confirm: true);
                    if (res != null && (res['status'] == 'success' || res['edit_info']?['applied'] == true)) {
                      final editInfo = res['edit_info'] as Map<String, dynamic>? ?? {};
                      final method = editInfo['method'] ?? 'unknown';
                      final version = editInfo['version'] as Map<String, dynamic>?;
                      final pdfRegen = editInfo['pdf_regenerated'] == true;
                      final versionId = version?['version_id'] ?? '?';
                      
                      setDialogState(() {
                        isProcessing = false;
                        previewText = '✅ Voice edit applied successfully!\n\n'
                            '📝 Command: "${textController.text.trim()}"\n'
                            '🤖 Method: ${method == "gemini" ? "Gemini AI" : "Simple Insert"}\n'
                            '📦 New version: $versionId\n'
                            '${pdfRegen ? "📄 PDF regenerated" : "⚠️ PDF not regenerated"}';
                        _isModified = true;
                      });
                    } else {
                      setDialogState(() {
                        isProcessing = false;
                        previewText = '⚠️ Edit could not be applied.\n\n'
                            'Diff preview:\n${res?['diff'] ?? 'No changes detected'}\n\n'
                            'Info: ${res?['edit_info']?['error'] ?? 'Unknown reason'}';
                      });
                    }
                  } catch (e) {
                    setDialogState(() {
                      isProcessing = false;
                      previewText = '❌ Error: $e';
                    });
                  }
                },
              ),
            if (previewText != null)
              ElevatedButton.icon(
                icon: const Icon(Icons.check, size: 16),
                label: Text('DONE', style: GoogleFonts.outfit(fontWeight: FontWeight.w700)),
                style: ElevatedButton.styleFrom(
                  backgroundColor: ratingGreen,
                  foregroundColor: Colors.white,
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                ),
                onPressed: () {
                  Navigator.pop(ctx);
                  _loadVersions();
                },
              ),
          ],
        ),
      ),
    );
  }

  // ─── PDF ACCESS METHODS ───

  /// Build the direct PDF URL
  String get _pdfUrl {
    final baseHost = ApiService.baseUrl.replaceAll('/api', '');
    return '$baseHost/api/projects/$_pid/report/pdf';
  }

  /// Download PDF to device temp dir and open with native viewer
  Future<void> _viewPdf() async {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Row(
          children: [
            const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white)),
            const SizedBox(width: 12),
            Text('Downloading report...', style: GoogleFonts.spaceMono(fontSize: 11)),
          ],
        ),
        backgroundColor: purple,
        duration: const Duration(seconds: 10),
      ),
    );

    try {
      final dir = await _getDownloadDir();
      final filePath = '$dir/RICS_Final_Report.pdf';
      
      final response = await Dio().download(
        _pdfUrl,
        filePath,
        options: Options(responseType: ResponseType.bytes),
      );

      if (!mounted) return;
      ScaffoldMessenger.of(context).hideCurrentSnackBar();

      if (response.statusCode == 200) {
        // Open PDF with native viewer
        final result = await OpenFilex.open(filePath, type: 'application/pdf');
        if (result.type != ResultType.done && mounted) {
          // Fallback: try browser
          await launchUrl(Uri.parse(_pdfUrl), mode: LaunchMode.externalApplication);
        }
      }
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).hideCurrentSnackBar();
      // Fallback: open in browser directly
      try {
        await launchUrl(Uri.parse(_pdfUrl), mode: LaunchMode.externalApplication);
      } catch (_) {
        if (mounted) {
          await Clipboard.setData(ClipboardData(text: _pdfUrl));
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text('📋 PDF URL copied — open in browser:\n$_pdfUrl',
                style: GoogleFonts.spaceMono(fontSize: 10)),
              duration: const Duration(seconds: 5),
              backgroundColor: ratingAmber,
            ),
          );
        }
      }
    }
  }

  /// Download PDF and save to device Downloads folder
  Future<void> _downloadPdf() async {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Row(
          children: [
            const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white)),
            const SizedBox(width: 12),
            Text('Saving PDF to Downloads...', style: GoogleFonts.spaceMono(fontSize: 11)),
          ],
        ),
        backgroundColor: const Color(0xFF43A047),
        duration: const Duration(seconds: 15),
      ),
    );

    try {
      final dir = await _getDownloadDir();
      final timestamp = DateTime.now().toIso8601String().substring(0, 16).replaceAll(':', '-');
      final filePath = '$dir/RICS_Report_$timestamp.pdf';

      final response = await Dio().download(
        _pdfUrl,
        filePath,
        options: Options(responseType: ResponseType.bytes),
      );

      if (!mounted) return;
      ScaffoldMessenger.of(context).hideCurrentSnackBar();

      if (response.statusCode == 200) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('✅ PDF saved: ${filePath.split('/').last}',
              style: GoogleFonts.spaceMono(fontSize: 11)),
            backgroundColor: ratingGreen,
            duration: const Duration(seconds: 4),
            action: SnackBarAction(
              label: 'OPEN',
              textColor: Colors.white,
              onPressed: () => OpenFilex.open(filePath, type: 'application/pdf'),
            ),
          ),
        );
      }
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).hideCurrentSnackBar();
      // Fallback: open URL in browser
      try {
        await launchUrl(Uri.parse(_pdfUrl), mode: LaunchMode.externalApplication);
      } catch (_) {
        await Clipboard.setData(ClipboardData(text: _pdfUrl));
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text('📋 PDF URL copied:\n$_pdfUrl',
                style: GoogleFonts.spaceMono(fontSize: 10)),
              backgroundColor: ratingAmber,
            ),
          );
        }
      }
    }
  }

  /// Share PDF via system share sheet
  Future<void> _sharePdf() async {
    if (!mounted) return;

    try {
      // Download PDF first
      final dir = await _getDownloadDir();
      final filePath = '$dir/RICS_Final_Report.pdf';
      
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Row(
            children: [
              const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white)),
              const SizedBox(width: 12),
              Text('Preparing share...', style: GoogleFonts.spaceMono(fontSize: 11)),
            ],
          ),
          backgroundColor: const Color(0xFF1E88E5),
          duration: const Duration(seconds: 10),
        ),
      );

      await Dio().download(_pdfUrl, filePath);
      if (!mounted) return;
      ScaffoldMessenger.of(context).hideCurrentSnackBar();

      // Open with share intent
      final result = await OpenFilex.open(filePath, type: 'application/pdf');
      if (result.type != ResultType.done) {
        // Fallback: copy URL
        await Clipboard.setData(ClipboardData(text: _pdfUrl));
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text('📋 Report link copied to clipboard',
                style: GoogleFonts.spaceMono(fontSize: 11)),
              backgroundColor: const Color(0xFF1E88E5),
              duration: const Duration(seconds: 3),
            ),
          );
        }
      }
    } catch (e) {
      // Fallback: just copy URL
      await Clipboard.setData(ClipboardData(text: _pdfUrl));
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('📋 Report link copied to clipboard',
              style: GoogleFonts.spaceMono(fontSize: 11)),
            backgroundColor: const Color(0xFF1E88E5),
          ),
        );
      }
    }
  }

  /// Get device download dir
  Future<String> _getDownloadDir() async {
    final dir = await getApplicationDocumentsDirectory();
    final downloadDir = Directory('${dir.path}/RICS_Reports');
    if (!await downloadDir.exists()) {
      await downloadDir.create(recursive: true);
    }
    return downloadDir.path;
  }

  // ─── MOBILE SECTION EDITOR ───

  void _openSectionEditor() {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: bgDark,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      builder: (ctx) => _SectionEditorSheet(
        projectId: _pid,
        api: _api,
        onSaved: () {
          setState(() { _isModified = true; });
          _loadVersions();
        },
      ),
    );
  }

  void _openWebEditor() async {
    final pid = _pid;
    final baseHost = ApiService.baseUrl.replaceAll('/api', '');
    final url = '$baseHost/editor?project=$pid';
    
    try {
      final uri = Uri.parse(url);
      if (await canLaunchUrl(uri)) {
        await launchUrl(uri, mode: LaunchMode.externalApplication);
      } else {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text(
                'Open in browser: $url',
                style: GoogleFonts.spaceMono(fontSize: 11, color: Colors.white),
              ),
              backgroundColor: purple,
              duration: const Duration(seconds: 8),
              action: SnackBarAction(
                label: 'COPY',
                textColor: gold,
                onPressed: () {
                  Clipboard.setData(ClipboardData(text: url));
                },
              ),
            ),
          );
        }
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Open in browser: $url', style: GoogleFonts.spaceMono(fontSize: 11, color: Colors.white)),
            backgroundColor: purple,
            duration: const Duration(seconds: 8),
          ),
        );
      }
    }
  }

  // ─── PHOTO REORDER ───

  void _openPhotoReorder() {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: bgDark,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      builder: (ctx) => _PhotoReorderSheet(
        projectId: _pid,
        api: _api,
      ),
    );
  }
}

// ──────────────────────────────────────────────────
// SECTION EDITOR — Bottom sheet for mobile editing
// ──────────────────────────────────────────────────

class _SectionEditorSheet extends StatefulWidget {
  final String projectId;
  final ApiService api;
  final VoidCallback onSaved;

  const _SectionEditorSheet({
    required this.projectId,
    required this.api,
    required this.onSaved,
  });

  @override
  State<_SectionEditorSheet> createState() => _SectionEditorSheetState();
}

class _SectionEditorSheetState extends State<_SectionEditorSheet> {
  bool _isLoading = true;
  String _fullMd = '';
  List<Map<String, String>> _sections = [];
  int? _editingIndex;
  final _editController = TextEditingController();
  bool _isSaving = false;

  static const gold = Color(0xFFD4A843);
  static const bgCard = Color(0xFF1E1E2A);
  static const bgDark = Color(0xFF12121C);
  static const purple = Color(0xFF4D2D69);
  static const textSecondary = Color(0xFF8A8A9E);

  @override
  void initState() {
    super.initState();
    _loadMd();
  }

  @override
  void dispose() {
    _editController.dispose();
    super.dispose();
  }

  Future<void> _loadMd() async {
    try {
      final res = await widget.api.getFinalReportMd(widget.projectId);
      if (res != null && res['content'] != null) {
        setState(() {
          _fullMd = res['content'] as String;
          _sections = _parseSections(_fullMd);
          _isLoading = false;
        });
      } else {
        setState(() => _isLoading = false);
      }
    } catch (e) {
      setState(() => _isLoading = false);
    }
  }

  List<Map<String, String>> _parseSections(String md) {
    final result = <Map<String, String>>[];
    final lines = md.split('\n');
    String currentTitle = 'Header';
    List<String> currentLines = [];

    for (final line in lines) {
      if (line.startsWith('## ') || line.startsWith('# ')) {
        if (currentLines.isNotEmpty || currentTitle != 'Header') {
          result.add({'title': currentTitle, 'content': currentLines.join('\n')});
        }
        currentTitle = line.replaceFirst(RegExp(r'^#{1,2}\s*'), '').trim();
        currentLines = [line];
      } else {
        currentLines.add(line);
      }
    }
    if (currentLines.isNotEmpty) {
      result.add({'title': currentTitle, 'content': currentLines.join('\n')});
    }
    return result;
  }

  Future<void> _saveSection(int index) async {
    setState(() => _isSaving = true);
    _sections[index] = {
      'title': _sections[index]['title']!,
      'content': _editController.text,
    };
    final updatedMd = _sections.map((s) => s['content']).join('\n\n');
    try {
      await widget.api.updateFinalReportMd(
        widget.projectId,
        updatedMd,
        'Edited section: ${_sections[index]['title']}',
      );
      widget.onSaved();
      setState(() { _editingIndex = null; _isSaving = false; });
    } catch (e) {
      setState(() => _isSaving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return DraggableScrollableSheet(
      initialChildSize: 0.85,
      minChildSize: 0.4,
      maxChildSize: 0.95,
      expand: false,
      builder: (_, scrollCtrl) => Column(
        children: [
          // Handle
          Container(
            margin: const EdgeInsets.symmetric(vertical: 10),
            width: 40,
            height: 4,
            decoration: BoxDecoration(
              color: textSecondary,
              borderRadius: BorderRadius.circular(2),
            ),
          ),
          // Title
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 20),
            child: Row(
              children: [
                const Icon(Icons.edit_document, color: gold, size: 22),
                const SizedBox(width: 10),
                Text(
                  'SECTION EDITOR',
                  style: GoogleFonts.spaceMono(
                    color: gold,
                    fontSize: 14,
                    fontWeight: FontWeight.bold,
                    letterSpacing: 2,
                  ),
                ),
              ],
            ),
          ),
          const Divider(color: Colors.white10, height: 20),
          // Content
          Expanded(
            child: _isLoading
                ? const Center(child: CircularProgressIndicator(color: gold))
                : _sections.isEmpty
                    ? Center(
                        child: Text(
                          'No report content. Generate a report first.',
                          style: GoogleFonts.spaceMono(color: textSecondary, fontSize: 12),
                        ),
                      )
                    : ListView.builder(
                        controller: scrollCtrl,
                        padding: const EdgeInsets.symmetric(horizontal: 16),
                        itemCount: _sections.length,
                        itemBuilder: (_, i) => _buildSectionTile(i),
                      ),
          ),
        ],
      ),
    );
  }

  Widget _buildSectionTile(int index) {
    final section = _sections[index];
    final isEditing = _editingIndex == index;
    final contentPreview = (section['content'] ?? '').length > 120
        ? '${section['content']!.substring(0, 120)}...'
        : section['content'] ?? '';

    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      decoration: BoxDecoration(
        color: isEditing ? purple.withOpacity(0.15) : bgCard,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(
          color: isEditing ? gold.withOpacity(0.5) : Colors.white.withOpacity(0.05),
        ),
      ),
      child: isEditing
          ? Padding(
              padding: const EdgeInsets.all(12),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Expanded(
                        child: Text(
                          '✏️ ${section['title']}',
                          style: GoogleFonts.outfit(
                            color: gold,
                            fontSize: 14,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                      ),
                      if (_isSaving)
                        const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(color: gold, strokeWidth: 2)),
                    ],
                  ),
                  const SizedBox(height: 8),
                  TextField(
                    controller: _editController,
                    maxLines: 12,
                    style: GoogleFonts.spaceMono(color: Colors.white, fontSize: 11, height: 1.4),
                    decoration: InputDecoration(
                      filled: true,
                      fillColor: bgDark,
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(8),
                        borderSide: BorderSide.none,
                      ),
                    ),
                  ),
                  const SizedBox(height: 8),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.end,
                    children: [
                      TextButton(
                        onPressed: () => setState(() => _editingIndex = null),
                        child: Text('Cancel', style: GoogleFonts.outfit(color: textSecondary)),
                      ),
                      const SizedBox(width: 8),
                      ElevatedButton.icon(
                        icon: const Icon(Icons.save, size: 16),
                        label: Text('Save', style: GoogleFonts.outfit(fontWeight: FontWeight.w700)),
                        style: ElevatedButton.styleFrom(
                          backgroundColor: gold,
                          foregroundColor: bgDark,
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                        ),
                        onPressed: _isSaving ? null : () => _saveSection(index),
                      ),
                    ],
                  ),
                ],
              ),
            )
          : ListTile(
              contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
              title: Text(
                section['title'] ?? 'Untitled',
                style: GoogleFonts.outfit(
                  color: Colors.white,
                  fontSize: 14,
                  fontWeight: FontWeight.w600,
                ),
              ),
              subtitle: Text(
                contentPreview,
                style: GoogleFonts.spaceMono(color: textSecondary, fontSize: 9, height: 1.3),
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
              ),
              trailing: IconButton(
                icon: const Icon(Icons.edit, color: gold, size: 18),
                onPressed: () {
                  setState(() {
                    _editingIndex = index;
                    _editController.text = section['content'] ?? '';
                  });
                },
              ),
            ),
    );
  }
}


// ──────────────────────────────────────────────────
// PHOTO REORDER — Drag-and-drop photo ordering
// ──────────────────────────────────────────────────

class _PhotoReorderSheet extends StatefulWidget {
  final String projectId;
  final ApiService api;

  const _PhotoReorderSheet({
    required this.projectId,
    required this.api,
  });

  @override
  State<_PhotoReorderSheet> createState() => _PhotoReorderSheetState();
}

class _PhotoReorderSheetState extends State<_PhotoReorderSheet> {
  bool _isLoading = true;
  List<Map<String, dynamic>> _photos = [];
  bool _isSaving = false;
  bool _hasChanged = false;

  static const gold = Color(0xFFD4A843);
  static const bgCard = Color(0xFF1E1E2A);
  static const bgDark = Color(0xFF12121C);
  static const cyan = Color(0xFF00BCD4);
  static const textSecondary = Color(0xFF8A8A9E);

  @override
  void initState() {
    super.initState();
    _loadPhotos();
  }

  Future<void> _loadPhotos() async {
    try {
      final res = await widget.api.getReportPhotos(widget.projectId);
      if (res != null && res['photos'] != null) {
        setState(() {
          _photos = List<Map<String, dynamic>>.from(res['photos']);
          _isLoading = false;
        });
      } else {
        setState(() => _isLoading = false);
      }
    } catch (e) {
      setState(() => _isLoading = false);
    }
  }

  Future<void> _saveOrder() async {
    setState(() => _isSaving = true);
    final ids = _photos.map((p) => p['id'] as String).toList();
    try {
      await widget.api.reorderReportPhotos(widget.projectId, ids);
      setState(() { _isSaving = false; _hasChanged = false; });
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('✅ Photo order saved', style: GoogleFonts.spaceMono(color: Colors.white)),
            backgroundColor: cyan,
          ),
        );
      }
    } catch (e) {
      setState(() => _isSaving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return DraggableScrollableSheet(
      initialChildSize: 0.85,
      minChildSize: 0.4,
      maxChildSize: 0.95,
      expand: false,
      builder: (_, scrollCtrl) => Column(
        children: [
          // Handle
          Container(
            margin: const EdgeInsets.symmetric(vertical: 10),
            width: 40,
            height: 4,
            decoration: BoxDecoration(
              color: textSecondary,
              borderRadius: BorderRadius.circular(2),
            ),
          ),
          // Title bar
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 20),
            child: Row(
              children: [
                const Icon(Icons.photo_library, color: cyan, size: 22),
                const SizedBox(width: 10),
                Text(
                  'REORDER PHOTOS',
                  style: GoogleFonts.spaceMono(
                    color: cyan,
                    fontSize: 14,
                    fontWeight: FontWeight.bold,
                    letterSpacing: 2,
                  ),
                ),
                const Spacer(),
                if (_hasChanged)
                  ElevatedButton.icon(
                    icon: _isSaving
                        ? const SizedBox(
                            width: 14, height: 14,
                            child: CircularProgressIndicator(
                              color: Colors.white, strokeWidth: 2,
                            ),
                          )
                        : const Icon(Icons.save, size: 16),
                    label: Text(
                      'SAVE',
                      style: GoogleFonts.outfit(fontWeight: FontWeight.w700),
                    ),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: cyan,
                      foregroundColor: Colors.white,
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(10),
                      ),
                    ),
                    onPressed: _isSaving ? null : _saveOrder,
                  ),
              ],
            ),
          ),
          const Divider(color: Colors.white10, height: 20),
          // Content
          Expanded(
            child: _isLoading
                ? const Center(child: CircularProgressIndicator(color: cyan))
                : _photos.isEmpty
                    ? Center(
                        child: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Icon(Icons.photo_camera_outlined, color: textSecondary, size: 48),
                            const SizedBox(height: 16),
                            Text(
                              'No photos found',
                              style: GoogleFonts.outfit(color: textSecondary, fontSize: 16),
                            ),
                            const SizedBox(height: 8),
                            Text(
                              'Photos will appear here after you\ncapture evidence during inspections.',
                              textAlign: TextAlign.center,
                              style: GoogleFonts.spaceMono(color: textSecondary.withOpacity(0.6), fontSize: 11),
                            ),
                          ],
                        ),
                      )
                    : ReorderableListView.builder(
                        scrollController: scrollCtrl,
                        padding: const EdgeInsets.symmetric(horizontal: 16),
                        itemCount: _photos.length,
                        onReorder: (oldIndex, newIndex) {
                          if (newIndex > oldIndex) newIndex--;
                          setState(() {
                            final item = _photos.removeAt(oldIndex);
                            _photos.insert(newIndex, item);
                            _hasChanged = true;
                          });
                        },
                        itemBuilder: (_, i) => _buildPhotoTile(i),
                      ),
          ),
        ],
      ),
    );
  }

  Widget _buildPhotoTile(int index) {
    final photo = _photos[index];
    final baseUrl = ApiService.baseUrl.replaceAll('/api', '');
    final imageUrl = '$baseUrl${photo['path']}';

    return Container(
      key: ValueKey(photo['id']),
      margin: const EdgeInsets.only(bottom: 8),
      decoration: BoxDecoration(
        color: bgCard,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: Colors.white.withOpacity(0.05)),
      ),
      child: ListTile(
        contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
        leading: ClipRRect(
          borderRadius: BorderRadius.circular(8),
          child: Image.network(
            imageUrl,
            width: 56,
            height: 56,
            fit: BoxFit.cover,
            errorBuilder: (_, __, ___) => Container(
              width: 56, height: 56,
              decoration: BoxDecoration(
                color: bgDark,
                borderRadius: BorderRadius.circular(8),
              ),
              child: const Icon(Icons.broken_image, color: textSecondary, size: 24),
            ),
          ),
        ),
        title: Text(
          photo['filename'] ?? '',
          style: GoogleFonts.outfit(
            color: Colors.white,
            fontSize: 13,
            fontWeight: FontWeight.w600,
          ),
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
        ),
        subtitle: Text(
          '${photo['size_kb']} KB',
          style: GoogleFonts.spaceMono(color: textSecondary, fontSize: 10),
        ),
        trailing: const Icon(Icons.drag_handle, color: textSecondary, size: 20),
      ),
    );
  }
}
