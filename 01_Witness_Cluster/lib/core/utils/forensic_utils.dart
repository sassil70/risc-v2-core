import 'dart:io';
import 'package:crypto/crypto.dart';
import 'dart:convert';

class ForensicUtils {
  
  /// Calculates SHA-256 hash of a file.
  /// Used to fingerprint every image/audio captured effectively.
  static Future<String> calculateFileHash(File file) async {
    if (!await file.exists()) {
      throw Exception('File not found for forensic hashing: ${file.path}');
    }
    
    final stream = file.openRead();
    final digest = await sha256.bind(stream).first;
    return digest.toString();
  }

  /// Generates a composite signature for the entire session package.
  /// This is the "Wax Seal" for the digital parcel.
  static String generatePackageSignature(String manifestJson) {
    final bytes = utf8.encode(manifestJson);
    final digest = sha256.convert(bytes);
    return digest.toString();
  }
}
