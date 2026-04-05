import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:path_provider/path_provider.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:record/record.dart'; // Ensure record: ^5.1.0 in pubspec
import 'dart:convert';
import '../services/api_service.dart';
import 'plan_confirmation_screen.dart';

class FloorPlanRecorder extends StatefulWidget {
  final Map<String, dynamic> initialData;
  final String? sessionId;
  final String? userId;

  const FloorPlanRecorder({
    super.key,
    required this.initialData,
    this.sessionId,
    this.userId,
  });

  @override
  State<FloorPlanRecorder> createState() => _FloorPlanRecorderState();
}

class _FloorPlanRecorderState extends State<FloorPlanRecorder>
    with SingleTickerProviderStateMixin {
  late AudioRecorder _audioRecorder;
  bool _isRecording = false;
  bool _isProcessing = false;
  String? _audioPath;
  late AnimationController _pulseController;

  @override
  void initState() {
    super.initState();
    _audioRecorder = AudioRecorder();
    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 1),
      lowerBound: 0.8,
      upperBound: 1.2,
    )..repeat(reverse: true);
  }

  @override
  void dispose() {
    _audioRecorder.dispose();
    _pulseController.dispose();
    super.dispose();
  }

  Future<void> _toggleRecording() async {
    if (_isRecording) {
      // STOP
      final path = await _audioRecorder.stop();
      setState(() {
        _isRecording = false;
        _audioPath = path;
      });
      _pulseController.stop();

      // Auto-Send to Brain
      if (path != null) {
        await _generatePlan(path);
      }
    } else {
      // START
      if (await Permission.microphone.request().isGranted) {
        final dir = await getApplicationDocumentsDirectory();
        final path = '${dir.path}/floor_plan_voice.m4a';

        await _audioRecorder.start(const RecordConfig(), path: path);
        setState(() {
          _isRecording = true;
          _audioPath = null;
        });
        _pulseController.repeat(reverse: true);
      }
    }
  }

  Future<void> _generatePlan(String path) async {
    setState(() => _isProcessing = true);

    try {
      // [New V2 Endpoint: /floorplan/init]
      // We use direct http.MultipartRequest here or update ApiService
      // But for clarity, let's keep it self-contained or use ApiService helper?
      // Let's do raw request for now to match the file upload pattern

      var request = http.MultipartRequest(
        'POST',
        Uri.parse('${ApiService.baseUrl}/floorplan/init'),
      );

      request.files.add(await http.MultipartFile.fromPath('file', path));
      request.fields['property_type'] = widget.initialData['property_type'];
      request.fields['floors'] = widget.initialData['number_of_floors']
          .toString();
      if (widget.sessionId != null) {
        request.fields['session_id'] = widget.sessionId!;
      }
      if (widget.userId != null) {
        request.fields['user_id'] = widget.userId!;
      }

      var response = await request.send().timeout(const Duration(seconds: 300));
      var respStr = await response.stream.bytesToString();

      if (response.statusCode == 200) {
        final jsonPlan = jsonDecode(respStr);

        if (mounted) {
          // Navigate to Confirmation
          Navigator.push(
            context,
            MaterialPageRoute(
              builder: (_) => PlanConfirmationScreen(
                propertyData: widget.initialData,
                generatedPlan: jsonPlan,
                sessionId: widget.sessionId,
              ),
            ),
          );
        }
      } else {
        throw Exception("Brain Error: $respStr");
      }
    } catch (e) {
      if (mounted) {
        // [FORENSIC MODE] Show full error details in a dialog
        showDialog(
          context: context,
          builder: (context) => AlertDialog(
            title: const Text("Forensic Error Log"),
            content: SingleChildScrollView(
              child: SelectableText(
                "Error Details:\n$e",
                style: const TextStyle(color: Colors.red),
              ),
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(context),
                child: const Text("CLOSE"),
              ),
            ],
          ),
        );
      }
    } finally {
      if (mounted) setState(() => _isProcessing = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.blueGrey[900], // Dark Theme for "AI Mode"
      appBar: AppBar(
        title: const Text("Step 2: Voice Architect"),
        backgroundColor: Colors.transparent,
        elevation: 0,
        foregroundColor: Colors.white,
      ),
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            if (_isProcessing) ...[
              const CircularProgressIndicator(color: Colors.white),
              const SizedBox(height: 20),
              const Text(
                "The Architect is thinking...",
                style: TextStyle(color: Colors.white, fontSize: 18),
              ),
            ] else ...[
              const Text(
                "Describe the Property",
                style: TextStyle(
                  color: Colors.white,
                  fontSize: 24,
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(height: 10),
              const Padding(
                padding: EdgeInsets.symmetric(horizontal: 40),
                child: Text(
                  "Is it a standard layout? Mention any extensions, utility rooms, or the garden.",
                  textAlign: TextAlign.center,
                  style: TextStyle(color: Colors.white70),
                ),
              ),
              const SizedBox(height: 60),

              // RECORD BUTTON
              GestureDetector(
                onTap: _toggleRecording,
                child: ScaleTransition(
                  scale: _isRecording
                      ? _pulseController
                      : const AlwaysStoppedAnimation(1.0),
                  child: Container(
                    width: 120,
                    height: 120,
                    decoration: BoxDecoration(
                      color: _isRecording ? Colors.red : Colors.blue,
                      shape: BoxShape.circle,
                      boxShadow: [
                        BoxShadow(
                          color: (_isRecording ? Colors.red : Colors.blue)
                              .withOpacity(0.5),
                          blurRadius: 20,
                          spreadRadius: 5,
                        ),
                      ],
                    ),
                    child: Icon(
                      _isRecording ? Icons.stop : Icons.mic,
                      size: 50,
                      color: Colors.white,
                    ),
                  ),
                ),
              ),
              const SizedBox(height: 30),
              Text(
                _isRecording ? "Listening..." : "Tap to Speak",
                style: const TextStyle(color: Colors.white, fontSize: 16),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
