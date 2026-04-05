import 'package:flutter/material.dart';
import '../services/api_service.dart';
import 'floor_plan_hub.dart';

class PlanConfirmationScreen extends StatefulWidget {
  final Map<String, dynamic> propertyData;
  final Map<String, dynamic> generatedPlan;
  final String? sessionId;

  const PlanConfirmationScreen({
    super.key,
    required this.propertyData,
    required this.generatedPlan,
    this.sessionId,
  });

  @override
  State<PlanConfirmationScreen> createState() => _PlanConfirmationScreenState();
}

class _PlanConfirmationScreenState extends State<PlanConfirmationScreen> {
  final ApiService _api = ApiService();
  bool _isInit = false;

  Future<void> _confirmAndStart() async {
    setState(() => _isInit = true);

    try {
      final String? propertyId =
          widget.propertyData['property_id']?.toString() ??
              widget.propertyData['project_id']?.toString();

      if (propertyId == null || propertyId.isEmpty) {
        throw Exception(
          "Corrupt ZOMBIE Session: Property ID is missing. Cannot save rooms.",
        );
      }

      final floors = widget.generatedPlan['floors'] as List<dynamic>? ?? [];

      for (int i = 0; i < floors.length; i++) {
        final floor = floors[i];
        final rooms = floor['rooms'] as List<dynamic>? ?? [];
        for (var room in rooms) {
          final success = await _api.addRoomToProject(propertyId, {
            "name": room['name'],
            "type": room['type'] ?? "general",
            "floor_name": floor['name'] ?? "Ground Floor",
          });

          if (!success) {
            throw Exception(
                "Network Failure: Could not reach the Mac Host to save ${room['name']}. Check Wi-Fi IP.");
          }
        }
      }

      // CRITICAL: Finalize the session on the backend to create the storage directory!
      // Without this, /inspection/status returns 404 Session Not Found and the Hub collapses.
      try {
        await _api.initProperty({
          "session_id": widget.sessionId ?? '',
          "property_id": propertyId,
          "plan": widget.generatedPlan,
        });
      } catch (e) {
        // Silently catch to not break flow if it partially fails, or we can let it throw.
        print('Session Initialization Warning: $e');
      }

      if (mounted) {
        // RADICAL RE-ARCHITECTURE: Explicitly route the user to the Central Inspection Hub.
        // This solves the stack ambiguity where "New Projects" popped to Dashboard
        // while "Existing Projects" popped to Hub. Now, everyone goes to the Hub.
        // We use pushReplacement to pop the PlanConfirmationScreen and go to the Hub.
        // We do NOT use pushAndRemoveUntil(isFirst) because isFirst acts unpredictably when
        // dealing with AuthCheck's pushReplacementNamed('/dashboard').
        Navigator.pushAndRemoveUntil(
          context,
          MaterialPageRoute(
            builder: (_) => FloorPlanHubScreen(
              sessionId: widget.sessionId ?? '',
            ),
          ),
          (route) =>
              false, // Clear ALL routes: kills voice recorder, init screen, etc.
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text("Save Failed: $e"),
            backgroundColor: Colors.redAccent,
            duration: const Duration(seconds: 5),
            behavior: SnackBarBehavior.floating,
          ),
        );
        setState(() => _isInit = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    // Extract floors for display
    final floors = widget.generatedPlan['floors'] as List<dynamic>? ?? [];

    return Scaffold(
      appBar: AppBar(title: const Text("Step 3: Confirm Plan")),
      body: Column(
        children: [
          // Header
          Container(
            padding: const EdgeInsets.all(16),
            color: Colors.blue.shade50,
            child: const Row(
              children: [
                Icon(Icons.check_circle, color: Colors.green),
                SizedBox(width: 10),
                Expanded(
                  child: Text(
                    "The Architect has drafted this plan. Ensure it matches reality.",
                    style: TextStyle(fontSize: 14, color: Colors.black87),
                  ),
                ),
              ],
            ),
          ),

          // TREE VIEW
          Expanded(
            child: ListView.builder(
              itemCount: floors.length,
              itemBuilder: (ctx, i) {
                final floor = floors[i];
                final rooms = floor['rooms'] as List<dynamic>? ?? [];

                return ExpansionTile(
                  initiallyExpanded: true,
                  title: Text(
                    floor['name'] ?? "Floor $i",
                    style: const TextStyle(fontWeight: FontWeight.bold),
                  ),
                  leading: const Icon(Icons.layers),
                  children: rooms
                      .map(
                        (r) => ListTile(
                          title: Text(r['name'] ?? "Unknown Room"),
                          subtitle: Text(r['type'] ?? "general"),
                          leading: const Icon(Icons.meeting_room, size: 16),
                        ),
                      )
                      .toList(),
                );
              },
            ),
          ),

          // Footer Actions
          SafeArea(
            child: Container(
              padding: const EdgeInsets.all(16),
              color: const Color(0xFF0A0F1A),
              child: Row(
                children: [
                  // Retry Button
                  Expanded(
                    child: OutlinedButton(
                      onPressed: _isInit ? null : () => Navigator.pop(context),
                      style: OutlinedButton.styleFrom(
                        foregroundColor: Colors.white,
                        side: const BorderSide(color: Colors.white54),
                      ),
                      child: const Text("Retry Voice"),
                    ),
                  ),
                  const SizedBox(width: 16),
                  // Confirm Button
                  Expanded(
                    flex: 2,
                    child: ElevatedButton(
                      onPressed: _isInit ? null : _confirmAndStart,
                      style: ElevatedButton.styleFrom(
                        backgroundColor: Colors.blue[900],
                        foregroundColor: Colors.white,
                        padding: const EdgeInsets.symmetric(vertical: 16),
                      ),
                      child: _isInit
                          ? const CircularProgressIndicator(color: Colors.white)
                          : const Text(
                              "CONFIRM & INSPECT",
                              style: TextStyle(
                                fontSize: 16,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}
