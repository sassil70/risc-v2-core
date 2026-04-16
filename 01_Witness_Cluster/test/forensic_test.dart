import 'dart:io';
import 'package:flutter_test/flutter_test.dart';
import 'package:witness_v2/core/utils/forensic_utils.dart';
import 'package:crypto/crypto.dart';
import 'dart:convert';

void main() {
  test('SHA-256 Hashing Consistency', () async {
    // 1. Create a dummy file
    final file = File('test_evidence.txt');
    await file.writeAsString('RISC V2.0 Evidence');
    
    // 2. Calculate expected hash
    // "RISC V2.0 Evidence" -> SHA256
    final bytes = utf8.encode('RISC V2.0 Evidence');
    final expectedHash = sha256.convert(bytes).toString();
    
    // 3. Run Utils
    final calculatedHash = await ForensicUtils.calculateFileHash(file);
    
    // 4. Verify
    expect(calculatedHash, equals(expectedHash));
    
    // Clean up
    await file.delete();
  });
  
  test('Package Signature consistency', () {
      const manifest = '{"file": "abc.jpg"}';
      final sig1 = ForensicUtils.generatePackageSignature(manifest);
      final sig2 = ForensicUtils.generatePackageSignature(manifest);
      expect(sig1, equals(sig2));
  });
}
