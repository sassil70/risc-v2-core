import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:flutter/foundation.dart';
import 'dart:io';
import '../core/services/remote_logger.dart';

class ApiService {
  // Use localhost for Web (prevents CORS/IP issues on same machine)
  // Use Physical IP for Mobile (Wireless)
  // Use localhost for Web and USB Debugging (adb reverse)
  // Standard Wi-Fi IP fallback if 127.0.0.1 not used
  // Updated for Phase 5 Driveway Scenario: Wireless Connectivity
  static String get baseUrl => kIsWeb 
    ? 'http://localhost:8001/api' 
    : 'https://risc-v2-brain-926489000848.europe-west1.run.app/api'; 

  Future<Map<String, dynamic>> checkHealth() async {
    try {
      final url = kIsWeb ? 'http://localhost:8001/' : 'https://risc-v2-brain-926489000848.europe-west1.run.app/';
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
    final response = await http.get(Uri.parse('$baseUrl/lookup/postcode/$postcode'));
    if (response.statusCode == 200) {
      return json.decode(response.body);
    } else {
      // Mock for offline dev if API fails
      return {
          "addresses": [
              {"number": "10", "street": "Downing Street", "city": "London"},
              {"number": "221B", "street": "Baker Street", "city": "London"}
          ]
      };
      // throw Exception('Failed to lookup postcode');
    }
  }

  Future<Map<String, dynamic>> generateFloorPlan(File audioFile, String propertyType, int floors) async {
    try {
      await RemoteLogger.action('Generating Floor Plan (Voice Architect)...');
      
      var request = http.MultipartRequest(
        'POST',
        Uri.parse('$baseUrl/floorplan/init')
      );
      
      request.files.add(await http.MultipartFile.fromPath('file', audioFile.path));
      request.fields['property_type'] = propertyType;
      request.fields['floors'] = floors.toString();
      
      final streamedResponse = await request.send();
      final response = await http.Response.fromStream(streamedResponse);
      
      if (response.statusCode == 200) {
        return json.decode(response.body);
      } else {
        await RemoteLogger.error('Architect Error ${response.statusCode}: ${response.body}');
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
        await RemoteLogger.error('API Error ${response.statusCode}: ${response.body}');
        throw Exception('Failed to initialize property: ${response.body}');
      }
    } catch (e) {
      await RemoteLogger.error('Network Exception: $e');
      rethrow;
    }
  }

  Future<bool> uploadRoomEvidence(String sessionId, String roomId, File zipFile) async {
    try {
      await RemoteLogger.action('Uploading Room Evidence: $roomId');
      final request = http.MultipartRequest('POST', Uri.parse('$baseUrl/v2/sync/upload_room'));
      request.fields['session_id'] = sessionId;
      request.fields['room_id'] = roomId;
      
      request.files.add(
        await http.MultipartFile.fromPath('file', zipFile.path)
      );

      final streamedResponse = await request.send();
      final response = await http.Response.fromStream(streamedResponse);

      if (response.statusCode == 200) {
        await RemoteLogger.info('Upload Success: $roomId');
        return true;
      } else {
        await RemoteLogger.error('Upload Failed ${response.statusCode}: ${response.body}');
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

  Future<Map<String, dynamic>> getPropertyDetails(String projectId) async {
    final response = await http.get(Uri.parse('$baseUrl/projects/$projectId'));
    if (response.statusCode == 200) {
      return json.decode(response.body);
    } else {
      await RemoteLogger.error('Fetch Property Error ${response.statusCode}: ${response.body}');
      throw Exception('Failed to fetch property details');
    }
  }

  // --- Phase 4 Integration ---
  
  Future<Map<String, dynamic>?> uploadVoiceAddendum(String projectId, String roomId, File audioFile) async {
    try {
      await RemoteLogger.action('Uploading Voice Addendum for Room: $roomId');
      final request = http.MultipartRequest('POST', Uri.parse('$baseUrl/projects/$projectId/rooms/$roomId/addendum'));
      
      request.files.add(
        await http.MultipartFile.fromPath('audio_file', audioFile.path)
      );

      final streamedResponse = await request.send();
      final response = await http.Response.fromStream(streamedResponse);

      if (response.statusCode == 200) {
        await RemoteLogger.info('Addendum Upload Success: $roomId');
        return json.decode(response.body);
      } else {
        await RemoteLogger.error('Addendum Upload Failed ${response.statusCode}: ${response.body}');
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
      final response = await http.get(Uri.parse('$baseUrl/projects/$projectId'));
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
      await RemoteLogger.info('Triggering AI Synthesis & PDF Generation for Project: $projectId');
      final response = await http.post(Uri.parse('$baseUrl/projects/$projectId/generate_final_rics_pdf'));
      
      if (response.statusCode != 200) {
        throw Exception('Server returned ${response.statusCode}: ${response.body}');
      }
      await RemoteLogger.info('PDF Generation Successful.');
    } catch (e) {
      await RemoteLogger.error('Failed to generate PDF: $e');
      throw e;
    }
  }

  Future<bool> addRoomToProject(String projectId, Map<String, dynamic> roomData) async {
    try {
      await RemoteLogger.action('Adding Room to Project $projectId');
      final response = await http.post(
        Uri.parse('$baseUrl/projects/$projectId/rooms'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode(roomData)
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

  Future<bool> approveRoom(String projectId, String roomId, List<String> selectedImages) async {
    try {
      await RemoteLogger.action('Approving Room & Locking Images: $roomId');
      final response = await http.put(
        Uri.parse('$baseUrl/projects/$projectId/rooms/$roomId/approve'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({'selected_diagnostic_images': selectedImages})
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
    String? title
  }) async {
    try {
      await RemoteLogger.action('Creating Session for Project: $projectId');
      final response = await http.post(
        Uri.parse('$baseUrl/surveyor/sessions'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({
          "title": title ?? "Mobile Inspection",
          "project_id": projectId,
          "surveyor_id": surveyorId
        })
      );
      
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

  Future<Map<String, dynamic>?> createProject(String reference, String client, {Map<String, dynamic>? metadata}) async {
    try {
      await RemoteLogger.action('Creating Project: $reference');
      final response = await http.post(
        Uri.parse('$baseUrl/projects'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({
          "reference_number": reference,
          "client_name": client,
          if (metadata != null) "metadata": metadata
        })
      );

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

  Future<Map<String, dynamic>?> updateProject(String projectId, String reference, String client, {Map<String, dynamic>? metadata}) async {
    try {
      await RemoteLogger.action('Updating Project: $projectId');
      final response = await http.put(
        Uri.parse('$baseUrl/projects/$projectId'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({
          "reference_number": reference,
          "client_name": client,
          if (metadata != null) "metadata": metadata
        })
      );

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
}
