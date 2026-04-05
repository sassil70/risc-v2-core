import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:flutter_animate/flutter_animate.dart';
import '../services/api_service.dart';

/// Evidence Gallery — displays photos grouped by context tabs
/// with ability to exclude/include photos from reports.
class EvidenceGalleryScreen extends StatefulWidget {
  final String projectId;
  final String roomId;
  final String roomName;

  const EvidenceGalleryScreen({
    super.key,
    required this.projectId,
    required this.roomId,
    required this.roomName,
  });

  @override
  State<EvidenceGalleryScreen> createState() => _EvidenceGalleryScreenState();
}

class _EvidenceGalleryScreenState extends State<EvidenceGalleryScreen>
    with SingleTickerProviderStateMixin {
  final ApiService _api = ApiService();
  bool _isLoading = true;
  Map<String, List<Map<String, dynamic>>> _contextImages = {};
  List<String> _contexts = [];
  TabController? _tabController;
  final Set<String> _excludedPhotos = {};

  @override
  void initState() {
    super.initState();
    _loadEvidence();
  }

  @override
  void dispose() {
    _tabController?.dispose();
    super.dispose();
  }

  Future<void> _loadEvidence() async {
    try {
      final serverHost = ApiService.baseUrl.replaceAll('/api', '');
      final evidence =
          await _api.getRoomEvidence(widget.projectId, widget.roomId);
      if (mounted && evidence != null) {
        final Map<String, List<Map<String, dynamic>>> grouped = {};
        for (var item in evidence) {
          final context = item['context'] ?? 'general';
          final relUrl = item['url'] ?? '';
          final filename = item['filename'] ?? '';
          final excluded = item['excluded'] == true;
          if (relUrl.isNotEmpty) {
            final fullUrl = '$serverHost$relUrl';
            grouped.putIfAbsent(context, () => []).add({
              'url': fullUrl,
              'filename': filename,
              'excluded': excluded,
            });
            if (excluded) _excludedPhotos.add(filename);
          }
        }
        setState(() {
          _contextImages = grouped;
          _contexts = grouped.keys.toList();
          _tabController = TabController(length: _contexts.length, vsync: this);
          _isLoading = false;
        });
      } else {
        if (mounted) setState(() => _isLoading = false);
      }
    } catch (e) {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  void _toggleExclude(String filename) async {
    setState(() {
      if (_excludedPhotos.contains(filename)) {
        _excludedPhotos.remove(filename);
      } else {
        _excludedPhotos.add(filename);
      }
    });

    final isNowExcluded = _excludedPhotos.contains(filename);
    HapticFeedback.mediumImpact();

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

    await _api.togglePhotoExclude(widget.projectId, widget.roomId, filename);
  }

  @override
  Widget build(BuildContext context) {
    final gold = const Color(0xFFFFD700);
    final excludedCount = _excludedPhotos.length;

    return Scaffold(
      backgroundColor: const Color(0xFF05080D),
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        title: Column(
          children: [
            Text(
              "EDIT EVIDENCE",
              style: GoogleFonts.spaceMono(
                color: gold,
                fontSize: 10,
                letterSpacing: 2,
              ),
            ),
            Text(
              widget.roomName,
              style: GoogleFonts.outfit(
                color: Colors.white,
                fontWeight: FontWeight.bold,
                fontSize: 16,
              ),
            ),
            if (excludedCount > 0)
              Text(
                '$excludedCount photo${excludedCount > 1 ? 's' : ''} excluded',
                style: GoogleFonts.spaceMono(
                  color: Colors.redAccent,
                  fontSize: 9,
                ),
              ),
          ],
        ),
        centerTitle: true,
        iconTheme: const IconThemeData(color: Colors.white),
      ),
      body: Stack(
        children: [
          Positioned.fill(
            child: Opacity(
              opacity: 0.03,
              child: Image.network(
                "https://www.transparenttextures.com/patterns/graphy.png",
                repeat: ImageRepeat.repeat,
              ),
            ),
          ),
          if (_isLoading)
            Center(child: CircularProgressIndicator(color: gold))
          else if (_contexts.isEmpty)
            Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(Icons.image_not_supported,
                      size: 64, color: Colors.white12),
                  const SizedBox(height: 16),
                  Text(
                    'No evidence found for this room',
                    style: GoogleFonts.spaceMono(
                        color: Colors.white30, fontSize: 12),
                  ),
                ],
              ),
            )
          else
            Column(
              children: [
                // Context Tabs
                Container(
                  margin:
                      const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                  height: 40,
                  decoration: BoxDecoration(
                    color: Colors.white.withOpacity(0.05),
                    borderRadius: BorderRadius.circular(20),
                  ),
                  child: TabBar(
                    controller: _tabController,
                    isScrollable: true,
                    indicator: BoxDecoration(
                      color: gold.withOpacity(0.8),
                      borderRadius: BorderRadius.circular(20),
                    ),
                    labelColor: Colors.black,
                    unselectedLabelColor: Colors.white54,
                    labelStyle: GoogleFonts.spaceMono(
                      fontSize: 9,
                      fontWeight: FontWeight.bold,
                    ),
                    tabs: _contexts
                        .map((c) => Tab(
                            text:
                                '${c.toUpperCase()} (${_contextImages[c]!.length})'))
                        .toList(),
                  ),
                ).animate().fadeIn(delay: 100.ms),

                // Hint
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 4),
                  child: Text(
                    'Tap photo to view full-screen & exclude',
                    style: GoogleFonts.spaceMono(
                      color: Colors.white24, fontSize: 8,
                    ),
                  ),
                ),

                // Photos Grid
                Expanded(
                  child: TabBarView(
                    controller: _tabController,
                    children: _contexts.map((ctx) {
                      final images = _contextImages[ctx]!;
                      return GridView.builder(
                        padding: const EdgeInsets.all(16),
                        gridDelegate:
                            const SliverGridDelegateWithFixedCrossAxisCount(
                          crossAxisCount: 3,
                          crossAxisSpacing: 8,
                          mainAxisSpacing: 8,
                        ),
                        itemCount: images.length,
                        itemBuilder: (context, i) {
                          final img = images[i];
                          final url = img['url'] as String;
                          final filename = img['filename'] as String;
                          final isExcluded = _excludedPhotos.contains(filename);

                          return GestureDetector(
                            onTap: () => _showFullImage(url, filename, ctx, i),
                            child: Hero(
                              tag: 'evidence_${ctx}_$i',
                              child: Stack(
                                fit: StackFit.expand,
                                children: [
                                  ClipRRect(
                                    borderRadius: BorderRadius.circular(12),
                                    child: Image.network(
                                      url,
                                      fit: BoxFit.cover,
                                      loadingBuilder:
                                          (ctx, child, loadingProgress) {
                                        if (loadingProgress == null) return child;
                                        return Container(
                                          color: Colors.white.withOpacity(0.05),
                                          child: Center(
                                            child: CircularProgressIndicator(
                                              strokeWidth: 2,
                                              color: gold,
                                              value: loadingProgress
                                                          .expectedTotalBytes !=
                                                      null
                                                  ? loadingProgress
                                                          .cumulativeBytesLoaded /
                                                      loadingProgress
                                                          .expectedTotalBytes!
                                                  : null,
                                            ),
                                          ),
                                        );
                                      },
                                      errorBuilder: (ctx, err, stack) =>
                                          Container(
                                        color: Colors.white.withOpacity(0.05),
                                        child: const Icon(Icons.broken_image,
                                            color: Colors.white24),
                                      ),
                                    ),
                                  ),
                                  // Excluded overlay
                                  if (isExcluded) ...[
                                    Positioned.fill(
                                      child: Container(
                                        decoration: BoxDecoration(
                                          color: Colors.red.withOpacity(0.4),
                                          borderRadius: BorderRadius.circular(12),
                                          border: Border.all(
                                            color: Colors.redAccent,
                                            width: 2,
                                          ),
                                        ),
                                        child: const Center(
                                          child: Icon(
                                            Icons.block,
                                            color: Colors.white,
                                            size: 32,
                                          ),
                                        ),
                                      ),
                                    ),
                                  ],
                                ],
                              ),
                            ),
                          )
                              .animate()
                              .fadeIn(delay: (30 * i).ms)
                              .scale(begin: const Offset(0.9, 0.9));
                        },
                      );
                    }).toList(),
                  ),
                ),
              ],
            ),
        ],
      ),
    );
  }

  void _showFullImage(String url, String filename, String ctx, int index) {
    final isExcluded = _excludedPhotos.contains(filename);
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => _FullScreenPhotoViewer(
          url: url,
          filename: filename,
          context: ctx,
          index: index,
          isExcluded: isExcluded,
          onToggleExclude: () {
            _toggleExclude(filename);
          },
        ),
      ),
    );
  }
}

/// Full-screen photo viewer with EXCLUDE/RE-INCLUDE button
class _FullScreenPhotoViewer extends StatefulWidget {
  final String url;
  final String filename;
  final String context;
  final int index;
  final bool isExcluded;
  final VoidCallback onToggleExclude;

  const _FullScreenPhotoViewer({
    required this.url,
    required this.filename,
    required this.context,
    required this.index,
    required this.isExcluded,
    required this.onToggleExclude,
  });

  @override
  State<_FullScreenPhotoViewer> createState() => _FullScreenPhotoViewerState();
}

class _FullScreenPhotoViewerState extends State<_FullScreenPhotoViewer> {
  late bool _isExcluded;

  @override
  void initState() {
    super.initState();
    _isExcluded = widget.isExcluded;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        title: Text(
          '${widget.context.toUpperCase()} — Photo ${widget.index + 1}',
          style: GoogleFonts.spaceMono(color: Colors.white70, fontSize: 12),
        ),
        iconTheme: const IconThemeData(color: Colors.white),
      ),
      body: Stack(
        children: [
          // Full-size photo with pinch zoom
          Center(
            child: Hero(
              tag: 'evidence_${widget.context}_${widget.index}',
              child: InteractiveViewer(
                minScale: 0.5,
                maxScale: 4.0,
                child: Image.network(widget.url, fit: BoxFit.contain),
              ),
            ),
          ),
          // Excluded banner
          if (_isExcluded)
            Positioned(
              top: 0,
              left: 0,
              right: 0,
              child: Container(
                padding: const EdgeInsets.symmetric(vertical: 8),
                color: Colors.redAccent.withOpacity(0.85),
                child: Text(
                  '⛔ EXCLUDED FROM REPORT',
                  style: GoogleFonts.spaceMono(
                    color: Colors.white,
                    fontSize: 11,
                    fontWeight: FontWeight.bold,
                  ),
                  textAlign: TextAlign.center,
                ),
              ),
            ),
          // Bottom action bar
          Positioned(
            bottom: 0,
            left: 0,
            right: 0,
            child: SafeArea(
              child: Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    begin: Alignment.bottomCenter,
                    end: Alignment.topCenter,
                    colors: [
                      Colors.black.withOpacity(0.9),
                      Colors.transparent,
                    ],
                  ),
                ),
                child: Row(
                  children: [
                    Expanded(
                      child: Text(
                        widget.filename,
                        style: GoogleFonts.spaceMono(
                          color: Colors.white38, fontSize: 8,
                        ),
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                    const SizedBox(width: 12),
                    ElevatedButton.icon(
                      onPressed: () {
                        widget.onToggleExclude();
                        setState(() => _isExcluded = !_isExcluded);
                      },
                      icon: Icon(
                        _isExcluded ? Icons.add_circle : Icons.block,
                        size: 18,
                      ),
                      label: Text(
                        _isExcluded ? 'RE-INCLUDE' : 'EXCLUDE',
                        style: GoogleFonts.spaceMono(
                          fontSize: 10, fontWeight: FontWeight.bold,
                        ),
                      ),
                      style: ElevatedButton.styleFrom(
                        backgroundColor:
                            _isExcluded ? const Color(0xFF00E676) : Colors.redAccent,
                        foregroundColor: Colors.white,
                        padding: const EdgeInsets.symmetric(
                            horizontal: 16, vertical: 10),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(10),
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
