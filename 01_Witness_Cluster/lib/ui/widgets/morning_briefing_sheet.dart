import 'package:flutter/material.dart';
import 'package:glassmorphism/glassmorphism.dart';
import 'package:google_fonts/google_fonts.dart';

class MorningBriefingSheet extends StatelessWidget {
  final Map<String, dynamic> data;
  final VoidCallback onDismiss;

  const MorningBriefingSheet({
    super.key,
    required this.data,
    required this.onDismiss,
  });

  @override
  Widget build(BuildContext context) {
    // Extract Data
    final message = data['message'] ?? "Welcome Surveyor.";
    final taskCount = data['task_count'] ?? 0;
    final weather = data['weather'] ?? "--";
    final traffic = data['traffic'] ?? "--";

    return Container(
      decoration: const BoxDecoration(
        color: Colors.transparent, // Let glass effect shine
      ),
      child: GlassmorphicContainer(
        width: double.infinity,
        height: 500,
        borderRadius: 20,
        blur: 20,
        alignment: Alignment.center,
        border: 2,
        linearGradient: LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [
             const Color(0xFF1E1E1E).withOpacity(0.9),
             const Color(0xFF1E1E1E).withOpacity(0.95),
          ],
        ),
        borderGradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            Colors.white.withOpacity(0.2),
            Colors.white.withOpacity(0.1),
          ],
        ),
        child: Padding(
          padding: const EdgeInsets.all(24.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Header
              Center(
                child: Container(
                  width: 40,
                  height: 4,
                  decoration: BoxDecoration(
                    color: Colors.white24,
                    borderRadius: BorderRadius.circular(2),
                  ),
                ),
              ),
              const SizedBox(height: 32),
              
              // Greeting
              Text(
                "Good Morning,",
                style: GoogleFonts.outfit(
                  color: Colors.white70,
                  fontSize: 24,
                ),
              ),
              const SizedBox(height: 8),
              Text(
                message, 
                style: GoogleFonts.outfit(
                  color: Colors.white,
                  fontSize: 18,
                  fontWeight: FontWeight.w300,
                  height: 1.5,
                ),
              ),
              
              const SizedBox(height: 48),

              // Metrics Row
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceAround,
                children: [
                  _buildMetric("Pending", "$taskCount", Icons.assignment_outlined, Colors.orangeAccent),
                  _buildMetric("Weather", weather, Icons.cloud_outlined, Colors.blueAccent),
                  _buildMetric("Traffic", traffic, Icons.traffic_outlined, Colors.redAccent),
                ],
              ),

              const Spacer(),

              // Action Button
              SizedBox(
                width: double.infinity,
                child: ElevatedButton(
                  onPressed: onDismiss,
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Colors.white,
                    foregroundColor: Colors.black,
                    padding: const EdgeInsets.symmetric(vertical: 18),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(12),
                    ),
                  ),
                  child: Text(
                    "START DAY",
                    style: GoogleFonts.outfit(
                      fontSize: 16,
                      fontWeight: FontWeight.bold,
                      letterSpacing: 1,
                    ),
                  ),
                ),
              ),
              const SizedBox(height: 20),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildMetric(String label, String value, IconData icon, Color color) {
    return Column(
      children: [
        Icon(icon, color: color, size: 32),
        const SizedBox(height: 12),
        Text(
          value,
          style: GoogleFonts.outfit(
            color: Colors.white,
            fontSize: 20,
            fontWeight: FontWeight.bold,
          ),
        ),
        Text(
          label,
          style: GoogleFonts.outfit(
            color: Colors.white54,
            fontSize: 12,
          ),
        ),
      ],
    );
  }
}
