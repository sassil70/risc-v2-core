
import 'dart:convert';
import 'dart:io';
import 'package:flutter/foundation.dart';
import 'package:uuid/uuid.dart';
import 'package:witness_v2/core/models/forensic_session.dart';

/// Singleton Service to manage the forensic timeline state
/// Implements "Micro-Session" Architecture: 1 Context = 1 Isolated Session
class TimelineService {
  static final TimelineService _instance = TimelineService._internal();
  factory TimelineService() => _instance;
  TimelineService._internal();

  // State
  ForensicSession? _activeSession;
  final Uuid _uuid = const Uuid();

  // --- Testable State Access ---
  ForensicSession? get activeSession => _activeSession;

  // --- API ---

  /// Clears active state (safety)
  void enterRoom() {
    _activeSession = null;
    debugPrint("Timeline Service: Ready for new forensic context.");
  }

  /// Starts a new ISOLATED recording session (The Capsule)
  void startSession(String context, String audioPath) {
    // 1. Generate new Forensic UUID
    final String newSessionId = _uuid.v4();
    
    // 2. Create the Session Capsule
    // Note: room_id is passed as "UNKNOWN" here because this service 
    // focuses on the *Context Timeline*. The linking to the Room happens
    // at the folder level or could be injected. 
    // For Phase 1.2, we focus on the capsule integrity.
    _activeSession = ForensicSession(
      sessionId: newSessionId,
      roomId: "PENDING_LINK", // Will be linked by folder structure
      contextType: context,
      startTimeUtc: DateTime.now().toUtc(),
      evidence: []
    );
    
    debugPrint("Forensic Session Started: $context [ID: $newSessionId]");
  }

  /// Logs a photo evidence into the active capsule
  void logPhoto(String photoPath) {
    if (_activeSession == null) return;
    
    final evidence = ForensicEvidence(
      filename: photoPath.split('/').last,
      timestampUtc: DateTime.now().toUtc(),
      type: 'PHOTO'
    );
    
    _activeSession!.evidence.add(evidence);
    debugPrint("Forensic Evidence Logged: ${evidence.filename}");
  }

  /// Ends the capsule and seals it (Saves to JSON)
  Future<void> endSessionAndSave(String contextFolderPath, int durationSeconds) async {
    if (_activeSession == null) return;
    
    // 1. Seal the Time & Duration
    _activeSession!.endTimeUtc = DateTime.now().toUtc();
    // We create a new instance because fields are final (Immutable Model)
    // Or we should have made it mutable. For now, let's reconstruct since it's cleaner state.
    // Actually, let's just use the constructor copy or similar. 
    // Wait, the model fields are final.
    // Let's modify the standard pattern:
    
    final sealedSession = ForensicSession(
        sessionId: _activeSession!.sessionId,
        roomId: _activeSession!.roomId,
        contextType: _activeSession!.contextType,
        startTimeUtc: _activeSession!.startTimeUtc,
        endTimeUtc: DateTime.now().toUtc(),
        evidence: _activeSession!.evidence,
        audioDurationSeconds: durationSeconds
    );

    // 2. Serialize
    final sessionData = sealedSession.toJson();
    
    // 3. Generate Filename using Session ID (Collision Proof)
    final String fileName = 'timeline_${sealedSession.sessionId}.json';
    
    _activeSession = null; // Reset immediately
    
    try {
      final file = File('$contextFolderPath/$fileName');
      await file.writeAsString(jsonEncode(sessionData));
      debugPrint("Forensic Capsule Sealed: ${file.path} [Duration: ${durationSeconds}s, Green: ${sealedSession.isGreen}]");
    } catch (e) {
      debugPrint("CRITICAL ERROR: Failed to seal forensic capsule: $e");
    }
  }
}
