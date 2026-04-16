import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:glassmorphism/glassmorphism.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:witness_v2/core/services/auth_service.dart';
import 'package:witness_v2/core/services/session_service.dart';
import '../../services/api_service.dart';
import '../../screens/property_init_screen.dart';
import '../../screens/floor_plan_hub.dart';
import '../../screens/property_details_screen.dart';

// --- Providers ---
final sessionsProvider = FutureProvider.autoDispose((ref) async {
  final user = ref.watch(userProvider);
  if (user == null) return <Map<String, dynamic>>[];
  final service = ref.watch(sessionServiceProvider);
  return service.getSessions(user['id']);
});

final projectsProvider = FutureProvider.autoDispose((ref) async {
  final api = ApiService();
  return api.getProjects();
});

class DashboardScreen extends ConsumerStatefulWidget {
  const DashboardScreen({super.key});

  @override
  ConsumerState<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends ConsumerState<DashboardScreen> {
  void _showStartOptions(BuildContext parentContext) {
    showModalBottomSheet(
      context: context,
      backgroundColor: Colors.transparent,
      isScrollControlled: true,
      builder: (context) => _StartOptionsModal(
        onNewProperty: () {
          Navigator.pop(context); // close modal
          Navigator.push(
            context,
            MaterialPageRoute(builder: (_) => const PropertyInitScreen()),
          );
        },
        onSelectExisting: () {
          Navigator.pop(context); // close modal
          DefaultTabController.of(
            parentContext,
          ).animateTo(1); // switch to archives tab
        },
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final user = ref.watch(userProvider);
    const midnight = Color(0xFF05080D);
    const gold = Color(0xFFFFD700);

    return DefaultTabController(
      length: 2,
      child: Scaffold(
        backgroundColor: midnight,
        extendBodyBehindAppBar: true,

        // Background Texture (Blueprint Grid)
        body: Stack(
          children: [
            Positioned.fill(
              child: Container(
                decoration: const BoxDecoration(
                  gradient: RadialGradient(
                    center: Alignment.topLeft,
                    radius: 1.5,
                    colors: [Color(0xFF0F172A), Color(0xFF020408)],
                  ),
                ),
              ),
            ),
            Positioned.fill(
              child: Opacity(
                opacity: 0.03,
                child: Image.network(
                  "https://www.transparenttextures.com/patterns/graphy.png",
                  repeat: ImageRepeat.repeat,
                ),
              ),
            ),
            Positioned(
              top: -100,
              right: -100,
              child: Container(
                width: 300,
                height: 300,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: const Color(0xFF1E88E5).withOpacity(0.15),
                  boxShadow: [
                    BoxShadow(
                      color: const Color(0xFF1E88E5).withOpacity(0.2),
                      blurRadius: 100,
                      spreadRadius: 50,
                    ),
                  ],
                ),
              ).animate(onPlay: (loop) => loop.repeat(reverse: true)).scale(
                    duration: 5.seconds,
                    begin: const Offset(1, 1),
                    end: const Offset(1.2, 1.2),
                  ),
            ),
            SafeArea(
              child: Column(
                children: [
                  _buildAppBar(user),
                  const SizedBox(height: 20),

                  // Tab Bar (Custom Glass)
                  Container(
                    margin: const EdgeInsets.symmetric(horizontal: 24),
                    height: 50,
                    decoration: BoxDecoration(
                      color: Colors.white.withOpacity(0.05),
                      borderRadius: BorderRadius.circular(25),
                      border: Border.all(color: Colors.white.withOpacity(0.1)),
                    ),
                    child: TabBar(
                      indicator: BoxDecoration(
                        color: gold.withOpacity(0.8),
                        borderRadius: BorderRadius.circular(25),
                        boxShadow: [
                          BoxShadow(
                            color: gold.withOpacity(0.3),
                            blurRadius: 10,
                          ),
                        ],
                      ),
                      labelColor: Colors.black,
                      unselectedLabelColor: Colors.white54,
                      labelStyle: GoogleFonts.outfit(
                        fontWeight: FontWeight.bold,
                        fontSize: 13,
                        letterSpacing: 1,
                      ),
                      tabs: const [
                        Tab(text: "ACTIVE MISSIONS"),
                        Tab(text: "PROPERTY ARCHIVES"),
                      ],
                    ),
                  ).animate().fadeIn(delay: 200.ms).slideY(begin: -0.2, end: 0),

                  const SizedBox(height: 24),

                  // Tab Views
                  Expanded(
                    child: TabBarView(
                      children: [
                        // Tab 1: ACTIVE MISSIONS — shows all projects (in-process)
                        _buildProjectsList(),
                        // Tab 2: PROPERTY ARCHIVES — only manually archived
                        _buildArchivedList(),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),

        floatingActionButton: Container(
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            boxShadow: [
              BoxShadow(
                color: gold.withOpacity(0.4),
                blurRadius: 20,
                spreadRadius: 2,
              ),
            ],
          ),
          child: FloatingActionButton(
            backgroundColor: gold,
            foregroundColor: Colors.black,
            elevation: 0,
            onPressed: () => _showStartOptions(context),
            child: const Icon(Icons.add_rounded, size: 36),
          ),
        ).animate().scale(
              delay: 500.ms,
              duration: 400.ms,
              curve: Curves.elasticOut,
            ),
      ),
    );
  }

  Widget _buildAppBar(Map<String, dynamic>? user) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  "COMMAND CENTER",
                  style: GoogleFonts.spaceMono(
                    fontSize: 10,
                    color: Colors.white38,
                    letterSpacing: 2,
                  ),
                  overflow: TextOverflow.ellipsis,
                ),
                Text(
                  "ULTIMATE DASHBOARD",
                  style: GoogleFonts.outfit(
                    fontSize: 22,
                    color: Colors.white,
                    fontWeight: FontWeight.bold,
                    letterSpacing: 1,
                  ),
                  overflow: TextOverflow.ellipsis,
                ),
              ],
            ),
          ),
          const SizedBox(width: 12),
          Container(
            padding: const EdgeInsets.all(2),
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              border: Border.all(color: const Color(0xFFFFD700), width: 1),
            ),
            child: const CircleAvatar(
              radius: 18,
              backgroundColor: Colors.white10,
              child: Icon(Icons.person, color: Colors.white70, size: 20),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildInspectionsList() {
    final sessionsAsync = ref.watch(sessionsProvider);

    return sessionsAsync.when(
      data: (sessions) {
        if (sessions.isEmpty) {
          return _buildEmptyState("NO ACTIVE MISSIONS", Icons.radar);
        }
        return ListView.builder(
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 0),
          itemCount: sessions.length,
          itemBuilder: (context, index) {
            return _buildSessionCard(sessions[index])
                .animate()
                .fadeIn(delay: (50 * index).ms)
                .slideX(begin: 0.1, end: 0);
          },
        );
      },
      loading: () => const Center(
        child: CircularProgressIndicator(color: Color(0xFFFFD700)),
      ),
      error: (err, stack) => Center(
        child: Text(
          "SYSTEM ERROR",
          style: GoogleFonts.spaceMono(color: Colors.red),
        ),
      ),
    );
  }

  Widget _buildProjectsList() {
    final projectsAsync = ref.watch(projectsProvider);

    return projectsAsync.when(
      data: (projects) {
        // Show all projects that are NOT archived (active missions)
        final activeProjects = projects.where((p) {
          // A project is archived ONLY when it has a final report AND is explicitly marked
          return p['archived'] != true;
        }).toList();
        if (activeProjects.isEmpty) {
          return _buildEmptyState("NO ACTIVE MISSIONS", Icons.business);
        }
        return ListView.builder(
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 0),
          itemCount: activeProjects.length,
          itemBuilder: (context, index) {
            return _buildProjectCard(activeProjects[index])
                .animate()
                .fadeIn(delay: (50 * index).ms)
                .slideX(begin: 0.1, end: 0);
          },
        );
      },
      loading: () => const Center(
        child: CircularProgressIndicator(color: Color(0xFFFFD700)),
      ),
      error: (err, stack) => Center(
        child: Text(
          "SYSTEM ERROR",
          style: GoogleFonts.spaceMono(color: Colors.red),
        ),
      ),
    );
  }

  Widget _buildArchivedList() {
    final projectsAsync = ref.watch(projectsProvider);

    return projectsAsync.when(
      data: (projects) {
        // Only show explicitly archived projects
        final archivedProjects = projects.where((p) {
          return p['archived'] == true;
        }).toList();
        if (archivedProjects.isEmpty) {
          return _buildEmptyState(
            "NO ARCHIVED PROPERTIES",
            Icons.archive_outlined,
          );
        }
        return ListView.builder(
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 0),
          itemCount: archivedProjects.length,
          itemBuilder: (context, index) {
            return _buildProjectCard(archivedProjects[index])
                .animate()
                .fadeIn(delay: (50 * index).ms)
                .slideX(begin: 0.1, end: 0);
          },
        );
      },
      loading: () => const Center(
        child: CircularProgressIndicator(color: Color(0xFFFFD700)),
      ),
      error: (err, stack) => Center(
        child: Text(
          "SYSTEM ERROR",
          style: GoogleFonts.spaceMono(color: Colors.red),
        ),
      ),
    );
  }

  Widget _buildEmptyState(String msg, IconData icon) {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(icon, size: 60, color: Colors.white.withOpacity(0.1)),
          const SizedBox(height: 16),
          Text(msg, style: GoogleFonts.spaceMono(color: Colors.white30)),
        ],
      ),
    );
  }

  Widget _buildSessionCard(Map<String, dynamic> session) {
    final status = session['status']?.toString().toLowerCase() ?? 'pending';
    final isActive = status == 'active';
    final isCompleted = status == 'completed';

    Color statusColor = isActive
        ? const Color(0xFF00E5FF)
        : (isCompleted ? Colors.greenAccent : const Color(0xFFFFD700));
    String statusText =
        isActive ? "LIVE LINK" : (isCompleted ? "SYNCED" : "PENDING");
    IconData icon = isActive
        ? Icons.wifi_tethering
        : (isCompleted ? Icons.cloud_done : Icons.hourglass_empty);

    return Padding(
      padding: const EdgeInsets.only(bottom: 16),
      child: GlassmorphicContainer(
        width: double.infinity,
        height: 100,
        borderRadius: 16,
        blur: 10,
        alignment: Alignment.center,
        border: 1,
        linearGradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            Colors.white.withOpacity(0.08),
            Colors.white.withOpacity(0.02),
          ],
        ),
        borderGradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            statusColor.withOpacity(0.5),
            Colors.white.withOpacity(0.05),
          ],
        ),
        child: Material(
          color: Colors.transparent,
          child: InkWell(
            onTap: () {
              Navigator.push(
                context,
                MaterialPageRoute(
                  builder: (_) => FloorPlanHubScreen(sessionId: session['id']),
                ),
              );
            },
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Row(
                children: [
                  Container(
                    width: 4,
                    height: 40,
                    decoration: BoxDecoration(
                      color: statusColor,
                      borderRadius: BorderRadius.circular(2),
                    ),
                  ),
                  const SizedBox(width: 16),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Text(
                          session['title'] ?? 'UNKNOWN SECTOR',
                          style: GoogleFonts.outfit(
                            color: Colors.white,
                            fontWeight: FontWeight.bold,
                            fontSize: 16,
                          ),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          "ID: ${session['id'].toString().substring(0, 8)}..."
                              .toUpperCase(),
                          style: GoogleFonts.spaceMono(
                            color: Colors.white38,
                            fontSize: 10,
                          ),
                        ),
                      ],
                    ),
                  ),
                  Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    crossAxisAlignment: CrossAxisAlignment.end,
                    children: [
                      Icon(icon, color: statusColor, size: 20),
                      const SizedBox(height: 4),
                      Text(
                        statusText,
                        style: GoogleFonts.spaceMono(
                          color: statusColor,
                          fontSize: 9,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildProjectCard(dynamic project) {
    if (project == null) return const SizedBox.shrink();

    final refStr = project['reference_number'] ?? 'No Ref';
    final metadata = project['metadata'] ?? {};
    final addressObj = metadata['address'] ?? {};
    final addressText =
        addressObj['full_address'] ?? project['client_name'] ?? 'No Address';
    final propType = metadata['property_type'] ?? 'Unknown Type';

    // === Status Logic ===
    final rooms = project['rooms'] as List<dynamic>? ?? [];
    final totalRooms = rooms.length;
    int completedRooms = 0;
    int totalPhotos = 0;
    int totalAudio = 0;
    for (var r in rooms) {
      if (r is Map) {
        final imgCount = r['images_count'] ?? 0;
        final audCount = r['audio_count'] ?? 0;
        totalPhotos += (imgCount as num).toInt();
        totalAudio += (audCount as num).toInt();
        if (r['status'] == 'completed') completedRooms++;
      }
    }

    String statusLabel;
    Color statusColor;
    IconData statusIcon;
    if (project['has_final_report'] == true) {
      statusLabel = 'REPORT READY';
      statusColor = const Color(0xFF00E676);
      statusIcon = Icons.check_circle;
    } else if (totalRooms > 0 && completedRooms == totalRooms) {
      statusLabel = 'EVIDENCE COMPLETE';
      statusColor = const Color(0xFFFFD700);
      statusIcon = Icons.assignment;
    } else {
      statusLabel = 'IN PROGRESS';
      statusColor = const Color(0xFFFF5252);
      statusIcon = Icons.hourglass_bottom;
    }

    final progress = totalRooms > 0 ? completedRooms / totalRooms : 0.0;

    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: GlassmorphicContainer(
        width: double.infinity,
        height: 130,
        borderRadius: 16,
        blur: 15,
        alignment: Alignment.center,
        border: 1,
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
          colors: [statusColor.withOpacity(0.5), Colors.white10],
        ),
        child: Material(
          color: Colors.transparent,
          child: InkWell(
            onTap: () {
              Navigator.push(
                context,
                MaterialPageRoute(
                  builder: (_) =>
                      PropertyDetailsScreen(propertyId: project['id']),
                ),
              );
            },
            child: Column(
              children: [
                Container(
                  height: 3,
                  decoration: BoxDecoration(
                    color: statusColor,
                    borderRadius: const BorderRadius.only(
                      topLeft: Radius.circular(16),
                      topRight: Radius.circular(16),
                    ),
                  ),
                ),
                Expanded(
                  child: Padding(
                    padding: const EdgeInsets.symmetric(
                        horizontal: 16, vertical: 10),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Expanded(
                              child: Text(
                                refStr,
                                style: GoogleFonts.outfit(
                                  fontWeight: FontWeight.bold,
                                  fontSize: 15,
                                  color: Colors.white,
                                ),
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                              ),
                            ),
                            Container(
                              padding: const EdgeInsets.symmetric(
                                  horizontal: 8, vertical: 3),
                              decoration: BoxDecoration(
                                color: statusColor.withOpacity(0.15),
                                borderRadius: BorderRadius.circular(8),
                                border: Border.all(
                                    color: statusColor.withOpacity(0.4)),
                              ),
                              child: Row(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  Icon(statusIcon,
                                      color: statusColor, size: 12),
                                  const SizedBox(width: 4),
                                  Text(
                                    statusLabel,
                                    style: GoogleFonts.spaceMono(
                                      color: statusColor,
                                      fontSize: 8,
                                      fontWeight: FontWeight.bold,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 4),
                        Text(
                          addressText,
                          style: GoogleFonts.spaceMono(
                              fontSize: 10, color: Colors.white54),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                        const Spacer(),
                        Row(
                          children: [
                            _statChip('📷', '$totalPhotos'),
                            const SizedBox(width: 8),
                            _statChip('🎤', '$totalAudio'),
                            const SizedBox(width: 8),
                            _statChip('🚪', '$completedRooms/$totalRooms'),
                            const Spacer(),
                            Text(
                              propType.toUpperCase(),
                              style: GoogleFonts.spaceMono(
                                  color: Colors.white30, fontSize: 8),
                            ),
                            const SizedBox(width: 4),
                            const Icon(Icons.chevron_right,
                                color: Colors.white30, size: 16),
                          ],
                        ),
                        const SizedBox(height: 6),
                        ClipRRect(
                          borderRadius: BorderRadius.circular(4),
                          child: LinearProgressIndicator(
                            value: progress,
                            backgroundColor: Colors.white10,
                            valueColor:
                                AlwaysStoppedAnimation<Color>(statusColor),
                            minHeight: 3,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _statChip(String emoji, String value) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.05),
        borderRadius: BorderRadius.circular(6),
      ),
      child: Text(
        '$emoji $value',
        style: GoogleFonts.spaceMono(color: Colors.white70, fontSize: 10),
      ),
    );
  }
}

// Bottom Sheet Wizard Entry
class _StartOptionsModal extends StatelessWidget {
  final VoidCallback onNewProperty;
  final VoidCallback onSelectExisting;

  const _StartOptionsModal({
    required this.onNewProperty,
    required this.onSelectExisting,
  });

  @override
  Widget build(BuildContext context) {
    return GlassmorphicContainer(
      width: double.infinity,
      height: 300,
      borderRadius: 30,
      blur: 20,
      alignment: Alignment.center,
      border: 1,
      linearGradient: LinearGradient(
        begin: Alignment.topCenter,
        end: Alignment.bottomCenter,
        colors: [
          const Color(0xFF1A1A24).withOpacity(0.95),
          const Color(0xFF05080D).withOpacity(0.98),
        ],
      ),
      borderGradient: LinearGradient(
        colors: [const Color(0xFFFFD700).withOpacity(0.5), Colors.transparent],
      ),
      child: Padding(
        padding: const EdgeInsets.all(24.0),
        child: Column(
          children: [
            Container(
              width: 40,
              height: 4,
              decoration: BoxDecoration(
                color: Colors.white24,
                borderRadius: BorderRadius.circular(2),
              ),
            ),
            const SizedBox(height: 24),
            Text(
              "MISSION LAUNCHPAD",
              style: GoogleFonts.spaceMono(
                fontSize: 12,
                letterSpacing: 2,
                color: const Color(0xFFFFD700),
              ),
            ),
            const SizedBox(height: 8),
            Text(
              "How would you like to start?",
              style: GoogleFonts.outfit(
                fontSize: 22,
                fontWeight: FontWeight.bold,
                color: Colors.white,
              ),
            ),
            const SizedBox(height: 32),

            // Option 1
            Material(
              color: Colors.transparent,
              child: ListTile(
                onTap: onNewProperty,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(16),
                ),
                tileColor: Colors.white.withOpacity(0.05),
                leading: Container(
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: const Color(0xFFFFD700).withOpacity(0.2),
                  ),
                  child: const Icon(
                    Icons.maps_home_work,
                    color: Color(0xFFFFD700),
                  ),
                ),
                title: Text(
                  "Create New Property Profile",
                  style: GoogleFonts.outfit(
                    fontWeight: FontWeight.bold,
                    color: Colors.white,
                  ),
                ),
                subtitle: Text(
                  "Start from scratch with a new client.",
                  style: GoogleFonts.spaceMono(
                    fontSize: 10,
                    color: Colors.white54,
                  ),
                ),
                trailing: const Icon(
                  Icons.chevron_right,
                  color: Colors.white30,
                ),
              ),
            ),
            const SizedBox(height: 12),

            // Option 2
            Material(
              color: Colors.transparent,
              child: ListTile(
                onTap: onSelectExisting,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(16),
                ),
                tileColor: Colors.white.withOpacity(0.05),
                leading: Container(
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: Colors.blue.withOpacity(0.2),
                  ),
                  child: const Icon(Icons.archive, color: Colors.blue),
                ),
                title: Text(
                  "Inspect Existing Property",
                  style: GoogleFonts.outfit(
                    fontWeight: FontWeight.bold,
                    color: Colors.white,
                  ),
                ),
                subtitle: Text(
                  "Select an archived property from database.",
                  style: GoogleFonts.spaceMono(
                    fontSize: 10,
                    color: Colors.white54,
                  ),
                ),
                trailing: const Icon(
                  Icons.chevron_right,
                  color: Colors.white30,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
