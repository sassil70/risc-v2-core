import 'dart:convert';
import 'package:http/http.dart' as http;
import 'dart:io';
import '../core/services/remote_logger.dart';

class ApiService {
  // Configurable via: flutter run --dart-define=API_URL=https://...
  static const String _envBaseUrl = String.fromEnvironment('API_URL', defaultValue: '');

  // Default to production Cloud Run URL if not overridden
  static String get baseDomain {
    if (_envBaseUrl.isNotEmpty) return _envBaseUrl;
    return 'https://risc-v2-brain-926489000848.europe-west1.run.app';
  }

  static String get baseUrl => '$baseDomain/api';

  Future<Map<String, dynamic>> checkHealth() async {
    try {
      final url = '$baseDomain/';
      final response = await http.get(Uri.parse(url));
      if (response.statusCode == 200) {
        return json.decode(response.body);
      }
    } catch (e) {
      print("Health Check Error: $e");
    }
    return {"status": "error"};
  }

  Future<Map<String, dynamic>> lookupPostcode(String postcode) async {
    final response = await http.get(
      Uri.parse('$baseUrl/lookup/postcode/$postcode'),
    );
    if (response.statusCode == 200) {
      return json.decode(response.body);
    } else {
      throw Exception('Failed to lookup postcode: ${response.statusCode}');
    }
  }

  Future<Map<String, dynamic>> generateFloorPlan(
    File audioFile,
    String propertyType,
    int floors,
  ) async {
    try {
      await RemoteLogger.action('Generating Floor Plan (Voice Architect)...');

      var request = http.MultipartRequest(
        'POST',
        Uri.parse('$baseUrl/floorplan/init'),
      );

      request.files.add(
        await http.MultipartFile.fromPath('file', audioFile.path),
      );
      request.fields['property_type'] = propertyType;
      request.fields['floors'] = floors.toString();

      final streamedResponse = await request.send();
      final response = await http.Response.fromStream(streamedResponse);

      if (response.statusCode == 200) {
        return json.decode(response.body);
      } else {
        await RemoteLogger.error(
          'Architect Error ${response.statusCode}: ${response.body}',
        );
        throw Exception('Architect Failed: ${response.statusCode}');
      }
    } catch (e) {
      await RemoteLogger.error('Architect Network Exception: $e');
      rethrow;
    }
  }

  Future<Map<String, dynamic>> initProperty(Map<String, dynamic> data) async {
    try {
      await RemoteLogger.action('Initializing Property via API...');
      final response = await http.post(
        Uri.parse('$baseUrl/property/init'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode(data),
      );

      if (response.statusCode == 200) {
        final result = json.decode(response.body);
        // Set Session ID globally for future logs
        if (result['session_id'] != null) {
          RemoteLogger().currentSessionId = result['session_id'];
          await RemoteLogger.info('Session Created: ${result['session_id']}');
        }
        return result;
      } else {
        await RemoteLogger.error(
          'API Error ${response.statusCode}: ${response.body}',
        );
        throw Exception('Failed to initialize property: ${response.body}');
      }
    } catch (e) {
      await RemoteLogger.error('Network Exception: $e');
      rethrow;
    }
  }

  Future<bool> uploadRoomEvidence(
    String sessionId,
    String roomId,
    File zipFile,
  ) async {
    try {
      await RemoteLogger.action('Uploading Room Evidence: $roomId');
      final request = http.MultipartRequest(
        'POST',
        Uri.parse('$baseUrl/v2/sync/upload_room'),
      );
      request.fields['session_id'] = sessionId;
      request.fields['room_id'] = roomId;

      request.files.add(
        await http.MultipartFile.fromPath('file', zipFile.path),
      );

      final streamedResponse = await request.send();
      final response = await http.Response.fromStream(streamedResponse);

      if (response.statusCode == 200) {
        await RemoteLogger.info('Upload Success: $roomId');
        return true;
      } else {
        await RemoteLogger.error(
          'Upload Failed ${response.statusCode}: ${response.body}',
        );
        return false;
      }
    } catch (e) {
      await RemoteLogger.error('Upload Exception: $e');
      return false;
    }
  }

  Future<Map<String, dynamic>> getStatus({String? sessionId}) async {
    String url = '$baseUrl/inspection/status';
    if (sessionId != null) {
      url += '?session_id=$sessionId';
    }
    final response = await http.get(Uri.parse(url));
    if (response.statusCode == 200) {
      return json.decode(response.body);
    } else {
      throw Exception('Failed to get status');
    }
  }

  // getPropertyDetails removed — use getProjectDetails() instead

  // --- Phase 4 Integration ---

  Future<Map<String, dynamic>?> uploadVoiceAddendum(
    String projectId,
    String roomId,
    File audioFile,
  ) async {
    try {
      await RemoteLogger.action('Uploading Voice Addendum for Room: $roomId');
      final request = http.MultipartRequest(
        'POST',
        Uri.parse('$baseUrl/projects/$projectId/rooms/$roomId/addendum'),
      );

      request.files.add(
        await http.MultipartFile.fromPath('audio_file', audioFile.path),
      );

      final streamedResponse = await request.send();
      final response = await http.Response.fromStream(streamedResponse);

      if (response.statusCode == 200) {
        await RemoteLogger.info('Addendum Upload Success: $roomId');
        return json.decode(response.body);
      } else {
        await RemoteLogger.error(
          'Addendum Upload Failed ${response.statusCode}: ${response.body}',
        );
        return null;
      }
    } catch (e) {
      await RemoteLogger.error('Addendum Upload Exception: $e');
      return null;
    }
  }

  Future<List<dynamic>> getProjects() async {
    try {
      final response = await http.get(Uri.parse('$baseUrl/projects'));
      if (response.statusCode == 200) {
        return json.decode(response.body);
      }
    } catch (e) {
      print("Error fetching projects: $e");
    }
    return [];
  }

  Future<Map<String, dynamic>?> getProjectDetails(String projectId) async {
    try {
      final response = await http.get(
        Uri.parse('$baseUrl/projects/$projectId'),
      );
      if (response.statusCode == 200) {
        return json.decode(response.body);
      }
    } catch (e) {
      print("Error fetching project details: $e");
    }
    return null;
  }

  Future<void> generateFinalRicsPdf({required String projectId}) async {
    try {
      await RemoteLogger.info(
        'Triggering AI Synthesis & PDF Generation for Project: $projectId',
      );
      final response = await http.post(
        Uri.parse('$baseUrl/projects/$projectId/generate_final_rics_pdf'),
      );

      if (response.statusCode != 200) {
        throw Exception(
          'Server returned ${response.statusCode}: ${response.body}',
        );
      }
      await RemoteLogger.info('PDF Generation Successful.');
    } catch (e) {
      await RemoteLogger.error('Failed to generate PDF: $e');
      rethrow;
    }
  }

  Future<bool> addRoomToProject(
    String projectId,
    Map<String, dynamic> roomData,
  ) async {
    try {
      await RemoteLogger.action('Adding Room to Project $projectId');
      final response = await http.post(
        Uri.parse('$baseUrl/projects/$projectId/rooms'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode(roomData),
      );
      if (response.statusCode == 200) {
        return true;
      } else {
        await RemoteLogger.error('Failed to add room: ${response.body}');
        return false;
      }
    } catch (e) {
      await RemoteLogger.error('Add Room Exception: $e');
      return false;
    }
  }

  Future<bool> approveRoom(
    String projectId,
    String roomId,
    List<String> selectedImages,
  ) async {
    try {
      await RemoteLogger.action('Approving Room & Locking Images: $roomId');
      final response = await http.put(
        Uri.parse('$baseUrl/projects/$projectId/rooms/$roomId/approve'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({'selected_diagnostic_images': selectedImages}),
      );
      if (response.statusCode == 200) {
        await RemoteLogger.info('Room Approved Successfully: $roomId');
        return true;
      } else {
        await RemoteLogger.error('Failed to approve room: ${response.body}');
        return false;
      }
    } catch (e) {
      await RemoteLogger.error('Approve Room Exception: $e');
      return false;
    }
  }

  Future<Map<String, dynamic>> createSession({
    required String projectId,
    required String surveyorId,
    String? title,
  }) async {
    try {
      await RemoteLogger.action('Creating Session for Project: $projectId');
      final response = await http.post(
        Uri.parse('$baseUrl/surveyor/sessions'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({
          "title": title ?? "Mobile Inspection",
          "project_id": projectId,
          "surveyor_id": surveyorId,
        }),
      ).timeout(const Duration(seconds: 15));

      if (response.statusCode == 200) {
        final result = json.decode(response.body);
        if (result['id'] != null) {
          RemoteLogger().currentSessionId = result['id'];
        }
        return result;
      } else {
        throw Exception("Failed to create session: ${response.body}");
      }
    } catch (e) {
      await RemoteLogger.error('Session Creation Error: $e');
      rethrow;
    }
  }

  Future<Map<String, dynamic>?> createProject(
    String reference,
    String client, {
    Map<String, dynamic>? metadata,
  }) async {
    try {
      await RemoteLogger.action('Creating Project: $reference');
      final response = await http.post(
        Uri.parse('$baseUrl/projects'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({
          "reference_number": reference,
          "client_name": client,
          if (metadata != null) "metadata": metadata,
        }),
      ).timeout(const Duration(seconds: 15));

      if (response.statusCode == 200) {
        return json.decode(response.body);
      } else {
        await RemoteLogger.error('Project Creation Failed: ${response.body}');
        return null;
      }
    } catch (e) {
      await RemoteLogger.error('Project Creation Exception: $e');
      return null;
    }
  }

  Future<Map<String, dynamic>?> updateProject(
    String projectId,
    String reference,
    String client, {
    Map<String, dynamic>? metadata,
  }) async {
    try {
      await RemoteLogger.action('Updating Project: $projectId');
      final response = await http.put(
        Uri.parse('$baseUrl/projects/$projectId'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({
          "reference_number": reference,
          "client_name": client,
          if (metadata != null) "metadata": metadata,
        }),
      ).timeout(const Duration(seconds: 15));

      if (response.statusCode == 200) {
        return json.decode(response.body);
      } else {
        await RemoteLogger.error('Project Update Failed: ${response.body}');
        return null;
      }
    } catch (e) {
      await RemoteLogger.error('Project Update Exception: $e');
      return null;
    }
  }

  // === Report API Methods ===

  /// Generate a partial report for a specific room
  Future<Map<String, dynamic>?> generatePartialReport(
      String projectId, String roomId) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/projects/$projectId/generate_partial_report'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({'room_id': roomId}),
      );
      if (response.statusCode == 200) {
        return json.decode(response.body);
      } else {
        await RemoteLogger.error(
            'Generate Partial Report Failed: ${response.body}');
        return null;
      }
    } catch (e) {
      await RemoteLogger.error('Generate Partial Report Exception: $e');
      return null;
    }
  }

  /// Get an existing partial report for a room
  Future<Map<String, dynamic>?> getPartialReport(
      String projectId, String roomId) async {
    try {
      final response = await http.get(
        Uri.parse(
            '$baseUrl/projects/$projectId/partial_report?room_id=$roomId'),
      );
      if (response.statusCode == 200) {
        return json.decode(response.body);
      }
      return null;
    } catch (e) {
      await RemoteLogger.error('Get Partial Report Exception: $e');
      return null;
    }
  }

  /// Apply a voice edit instruction to a partial report
  Future<Map<String, dynamic>?> voiceEditReport(
      String projectId, String roomId, String instruction) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/projects/$projectId/voice_edit_report'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({
          'room_id': roomId,
          'instruction': instruction,
        }),
      );
      if (response.statusCode == 200) {
        return json.decode(response.body);
      } else {
        await RemoteLogger.error('Voice Edit Failed: ${response.body}');
        return null;
      }
    } catch (e) {
      await RemoteLogger.error('Voice Edit Exception: $e');
      return null;
    }
  }

  /// Get evidence (photos) for a specific room, grouped by context
  Future<List<dynamic>?> getRoomEvidence(
      String projectId, String roomId) async {
    try {
      final response = await http.get(
        Uri.parse('$baseUrl/projects/$projectId/rooms/$roomId/evidence'),
      );
      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        return data['evidence'] as List<dynamic>? ?? [];
      }
      return [];
    } catch (e) {
      await RemoteLogger.error('Get Room Evidence Exception: $e');
      return [];
    }
  }

  /// Get structured evidence grouped by context for a room
  Future<Map<String, dynamic>?> getRoomContexts(
      String projectId, String roomId) async {
    try {
      final response = await http.get(
        Uri.parse('$baseUrl/projects/$projectId/rooms/$roomId/contexts'),
      );
      if (response.statusCode == 200) {
        return json.decode(response.body) as Map<String, dynamic>;
      }
      return null;
    } catch (e) {
      await RemoteLogger.error('Get Room Contexts Exception: $e');
      return null;
    }
  }

  /// Toggle a photo's exclusion status for report generation
  Future<Map<String, dynamic>?> togglePhotoExclude(
      String projectId, String roomId, String filename) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/projects/$projectId/rooms/$roomId/toggle_photo_exclude'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({'filename': filename}),
      );
      if (response.statusCode == 200) {
        return json.decode(response.body) as Map<String, dynamic>;
      }
      return null;
    } catch (e) {
      await RemoteLogger.error('Toggle Photo Exclude Exception: $e');
      return null;
    }
  }

  // ═══════════════════════════════════════════
  // FINAL REPORT — RICS Markdown Report System
  // ═══════════════════════════════════════════

  /// Generate the full RICS Level 3 PDF from all inspection data
  Future<Map<String, dynamic>?> generateFinalReport(String projectId) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/projects/$projectId/generate-final-report'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({}),
      ).timeout(const Duration(seconds: 120));
      if (response.statusCode == 200) {
        return json.decode(response.body) as Map<String, dynamic>;
      }
      await RemoteLogger.error('Generate Final Report failed: ${response.statusCode}');
      return null;
    } catch (e) {
      await RemoteLogger.error('Generate Final Report Exception: $e');
      return null;
    }
  }

  /// Get the current Markdown content of the RICS report
  Future<Map<String, dynamic>?> getFinalReportMd(String projectId) async {
    try {
      final response = await http.get(
        Uri.parse('$baseUrl/projects/$projectId/report-md'),
      );
      if (response.statusCode == 200) {
        return json.decode(response.body) as Map<String, dynamic>;
      }
      return null;
    } catch (e) {
      await RemoteLogger.error('Get Final Report MD Exception: $e');
      return null;
    }
  }

  /// Update the RICS report Markdown content (save / save-as)
  Future<Map<String, dynamic>?> updateFinalReportMd(
    String projectId, String content, String changesSummary,
  ) async {
    try {
      final response = await http.put(
        Uri.parse('$baseUrl/projects/$projectId/report-md'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({
          'content': content,
          'changes_summary': changesSummary,
        }),
      );
      if (response.statusCode == 200) {
        return json.decode(response.body) as Map<String, dynamic>;
      }
      return null;
    } catch (e) {
      await RemoteLogger.error('Update Report MD Exception: $e');
      return null;
    }
  }

  /// List all versions of the RICS report
  Future<Map<String, dynamic>?> getReportVersions(String projectId) async {
    try {
      final response = await http.get(
        Uri.parse('$baseUrl/projects/$projectId/report-versions'),
      );
      if (response.statusCode == 200) {
        return json.decode(response.body) as Map<String, dynamic>;
      }
      return null;
    } catch (e) {
      await RemoteLogger.error('Get Report Versions Exception: $e');
      return null;
    }
  }

  /// Mark a specific version as the final report
  Future<Map<String, dynamic>?> markReportFinal(
    String projectId, String versionId,
  ) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/projects/$projectId/report-mark-final'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({'version_id': versionId}),
      );
      if (response.statusCode == 200) {
        return json.decode(response.body) as Map<String, dynamic>;
      }
      return null;
    } catch (e) {
      await RemoteLogger.error('Mark Report Final Exception: $e');
      return null;
    }
  }

  /// Apply a voice command edit to the RICS final report
  Future<Map<String, dynamic>?> voiceEditFinalReport(
    String projectId, String voiceText, {bool confirm = false}
  ) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/projects/$projectId/report-voice-edit'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({
          'voice_text': voiceText,
          'confirm': confirm,
        }),
      );
      if (response.statusCode == 200) {
        return json.decode(response.body) as Map<String, dynamic>;
      }
      return null;
    } catch (e) {
      await RemoteLogger.error('Voice Edit Report Exception: $e');
      return null;
    }
  }

  // ══════════════════════════════════════════════════════════
  //  SURVEYOR APPROVAL WORKFLOW
  // ══════════════════════════════════════════════════════════

  /// Approve the final RICS report
  Future<Map<String, dynamic>?> approveReport(
    String projectId, {String? versionId}
  ) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/projects/$projectId/report-approve'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({
          if (versionId != null) 'version_id': versionId,
        }),
      );
      if (response.statusCode == 200) {
        return json.decode(response.body) as Map<String, dynamic>;
      }
      return null;
    } catch (e) {
      await RemoteLogger.error('Approve Report Exception: $e');
      return null;
    }
  }

  /// Reject the final RICS report with reasons and optional voice feedback
  Future<Map<String, dynamic>?> rejectReport(
    String projectId, {
    List<String> reasons = const [],
    String? voiceFeedbackPath,
    String? versionId,
  }) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/projects/$projectId/report-reject'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({
          'reasons': reasons,
          if (voiceFeedbackPath != null) 'voice_feedback_path': voiceFeedbackPath,
          if (versionId != null) 'version_id': versionId,
        }),
      );
      if (response.statusCode == 200) {
        return json.decode(response.body) as Map<String, dynamic>;
      }
      return null;
    } catch (e) {
      await RemoteLogger.error('Reject Report Exception: $e');
      return null;
    }
  }

  /// Get current approval status
  Future<Map<String, dynamic>?> getApprovalStatus(String projectId) async {
    try {
      final response = await http.get(
        Uri.parse('$baseUrl/projects/$projectId/report-approval'),
      );
      if (response.statusCode == 200) {
        return json.decode(response.body) as Map<String, dynamic>;
      }
      return null;
    } catch (e) {
      await RemoteLogger.error('Get Approval Status Exception: $e');
      return null;
    }
  }

  // ─── PHOTO REORDER ───

  Future<Map<String, dynamic>?> getReportPhotos(String projectId) async {
    try {
      final response = await http.get(
        Uri.parse('$baseUrl/projects/$projectId/report-photos'),
      );
      if (response.statusCode == 200) {
        return json.decode(response.body) as Map<String, dynamic>;
      }
      return null;
    } catch (e) {
      await RemoteLogger.error('Get Report Photos Exception: $e');
      return null;
    }
  }

  Future<Map<String, dynamic>?> reorderReportPhotos(String projectId, List<String> photoIds) async {
    try {
      final response = await http.put(
        Uri.parse('$baseUrl/projects/$projectId/report-photos/reorder'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({'photo_ids': photoIds}),
      );
      if (response.statusCode == 200) {
        return json.decode(response.body) as Map<String, dynamic>;
      }
      return null;
    } catch (e) {
      await RemoteLogger.error('Reorder Report Photos Exception: $e');
      return null;
    }
  }
}
