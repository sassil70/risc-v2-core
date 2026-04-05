
import 'package:flutter_test/flutter_test.dart';
import 'package:witness_v2/core/models/forensic_session.dart';

void main() {
  group('ForensicSession Logic Integrity', () {
    
    test('Should create a valid RICS-V2 Session JSON', () {
      // 1. Setup
      final session = ForensicSession(
        sessionId: 'test_uuid_123',
        roomId: 'room_kitchen_01',
        contextType: 'Walls',
        startTimeUtc: DateTime.utc(2026, 2, 8, 10, 0, 0),
      );

      // 2. Act
      final json = session.toJson();

      // 3. Assert (Syntax)
      expect(json['session_id'], 'test_uuid_123');
      expect(json['context_type'], 'Walls');
      expect(json['start_time'], '2026-02-08T10:00:00.000Z');
      expect(json['evidence'], isEmpty);
    });

    test('Should warn on non-standard Context but allow Elasticity', () {
      // 1. Setup (Ad-hoc Context)
      final session = ForensicSession(
        sessionId: 'test_uuid_456',
        roomId: 'room_lobby',
        contextType: 'CustomFeature', // Not in RICS list
        startTimeUtc: DateTime.now().toUtc(),
      );

      // 2. Act
      final json = session.toJson();

      // 3. Assert (Logic)
      // It should NOT crash, but allow the type through
      expect(json['context_type'], 'CustomFeature');
    });

    test('Should correctly parse evidence list', () {
       // 1. Setup
       final evidence = ForensicEvidence(
         filename: 'img_001.jpg', 
         timestampUtc: DateTime.utc(2026, 2, 8, 10, 0, 5),
         type: 'PHOTO'
       );

       final session = ForensicSession(
         sessionId: 'id', roomId: 'room', contextType: 'Floor',
         startTimeUtc: DateTime.now().toUtc(),
         evidence: [evidence]
       );

       // 2. Act
       final json = session.toJson();
       final parsedSession = ForensicSession.fromJson(json);

       // 3. Assert (Round Trip)
       expect(parsedSession.evidence.first.filename, 'img_001.jpg');
       expect(parsedSession.evidence.first.type, 'PHOTO');
    });

  });

  group('Traffic Light Constraints (RICS Validation)', () {
    test('Should be RED if photos < 3', () {
      final session = ForensicSession(
        sessionId: 'id', roomId: 'room', contextType: 'Walls',
        startTimeUtc: DateTime.now().toUtc(),
        evidence: [
          ForensicEvidence(filename: '1.jpg', timestampUtc: DateTime.now(), type: 'PHOTO'),
          ForensicEvidence(filename: '2.jpg', timestampUtc: DateTime.now(), type: 'PHOTO'),
        ],
        audioDurationSeconds: 10, // Good audio, not enough photos
      );
      expect(session.isGreen, isFalse);
    });

    test('Should be RED if audio < 5 seconds', () {
      final session = ForensicSession(
        sessionId: 'id', roomId: 'room', contextType: 'Walls',
        startTimeUtc: DateTime.now().toUtc(),
        evidence: [
           ForensicEvidence(filename: '1.jpg', timestampUtc: DateTime.now(), type: 'PHOTO'),
           ForensicEvidence(filename: '2.jpg', timestampUtc: DateTime.now(), type: 'PHOTO'),
           ForensicEvidence(filename: '3.jpg', timestampUtc: DateTime.now(), type: 'PHOTO'),
        ],
        audioDurationSeconds: 4, // Not enough audio
      );
      expect(session.isGreen, isFalse);
    });

    test('Should be GREEN if photos >= 3 AND audio >= 5 seconds', () {
      final session = ForensicSession(
        sessionId: 'id', roomId: 'room', contextType: 'Walls',
        startTimeUtc: DateTime.now().toUtc(),
        evidence: [
           ForensicEvidence(filename: '1.jpg', timestampUtc: DateTime.now(), type: 'PHOTO'),
           ForensicEvidence(filename: '2.jpg', timestampUtc: DateTime.now(), type: 'PHOTO'),
           ForensicEvidence(filename: '3.jpg', timestampUtc: DateTime.now(), type: 'PHOTO'),
        ],
        audioDurationSeconds: 5, // Just enough
      );
      expect(session.isGreen, isTrue);
    });
  });
}
