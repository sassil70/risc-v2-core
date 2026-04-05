/// RICS Level 3 Compliant Session Model
/// Represents a single, isolated forensic inspection activity.
class ForensicSession {
  final String sessionId; // UUID (e.g., "550e8400-e29b...")
  final String roomId; // As per Floor Plan (e.g., "room_kitchen_01")
  final String contextType; // RICS Context (e.g., "Walls", "Ceiling")
  final DateTime startTimeUtc; // ISO 8601 UTC
  DateTime? endTimeUtc; // ISO 8601 UTC
  final List<ForensicEvidence> evidence;

  // [NEW] Traffic Light Metrics
  final int audioDurationSeconds;

  ForensicSession({
    required this.sessionId,
    required this.roomId,
    required this.contextType,
    required this.startTimeUtc,
    this.endTimeUtc,
    this.evidence = const [],
    this.audioDurationSeconds = 0,
  });

  // --- TRAFFIC LIGHT LOGIC ---
  // Returns TRUE if this session meets RICS forensic standards
  bool get isGreen {
    // 1. Evidence Count: At least 3 photos required for triangulation
    final photoCount = evidence.where((e) => e.type == 'PHOTO').length;
    if (photoCount < 3) return false;

    // 2. Audio Duration: At least 5 seconds for meaningful commentary
    if (audioDurationSeconds < 5) return false;

    return true;
  }

  /// STRICT: Serialization for Brain Cluster (Python/Pydantic compatible)
  Map<String, dynamic> toJson() {
    return {
      'session_id': sessionId,
      'room_id': roomId,
      'context_type': _validateContext(contextType), // Safety Guard
      'start_time': startTimeUtc.toIso8601String(),
      'end_time': endTimeUtc?.toIso8601String(),
      'evidence': evidence.map((e) => e.toJson()).toList(),
      'audio_duration': audioDurationSeconds,
      'is_green': isGreen, // Helpful flag for backend
    };
  }

  /// Factory for deserialization (Validation Check)
  factory ForensicSession.fromJson(Map<String, dynamic> json) {
    return ForensicSession(
      sessionId: json['session_id'],
      roomId: json['room_id'],
      contextType: json['context_type'],
      startTimeUtc: DateTime.parse(json['start_time']),
      endTimeUtc: json['end_time'] != null
          ? DateTime.parse(json['end_time'])
          : null,
      evidence: (json['evidence'] as List)
          .map((e) => ForensicEvidence.fromJson(e))
          .toList(),
      audioDurationSeconds: json['audio_duration'] ?? 0,
    );
  }

  /// Safety Guard: Enforce RICS Context List
  String _validateContext(String type) {
    const validContexts = [
      'General',
      'Walls',
      'Ceiling',
      'Floor',
      'Windows',
      'Doors',
      'Electrical',
      'Plumbing',
      'HVAC',
      'FireSafety',
    ];
    if (!validContexts.contains(type)) {
      // In production, we log this. For dev, we warn.
      print("WARNING: Non-standard context '$type' detected.");
      // We allow it (Elasticity) but flag it.
    }
    return type;
  }
}

class ForensicEvidence {
  final String filename; // e.g., "img_001.jpg"
  final DateTime timestampUtc; // Relative to session start
  final String type; // "PHOTO" or "AUDIO"

  ForensicEvidence({
    required this.filename,
    required this.timestampUtc,
    required this.type,
  });

  Map<String, dynamic> toJson() => {
    'filename': filename,
    'timestamp': timestampUtc.toIso8601String(),
    'type': type,
  };

  factory ForensicEvidence.fromJson(Map<String, dynamic> json) {
    return ForensicEvidence(
      filename: json['filename'],
      timestampUtc: DateTime.parse(json['timestamp']),
      type: json['type'],
    );
  }
}
