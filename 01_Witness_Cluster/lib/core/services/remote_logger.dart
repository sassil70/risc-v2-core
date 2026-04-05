import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'dart:async';

class RemoteLogger {
  // Singleton pattern
  static final RemoteLogger _instance = RemoteLogger._internal();
  factory RemoteLogger() => _instance;
  RemoteLogger._internal();

  final Dio _dio = Dio(BaseOptions(
    connectTimeout: const Duration(milliseconds: 2000), // Drop unreachable connections quickly
  ));
  // Phase 17: Hardcoded for ADB Localhost USB Debugging on 8999
  final String _endpoint = 'http://172.16.2.84:8999/api/v2/monitor/logs';

  String? currentSessionId;

  // Buffer for batched logs (future optimization)
  // For now, we send immediately to ensure we see the crash BEFORE the app dies.

  Future<void> log(String level, String message, {String? sessionId}) async {
    // 1. Always print to local console (for Android Studio / VS Code)
    debugPrint('[$level] $message');

    // 2. Send to Brain Cluster (Laptop)
    try {
      await _dio.post(
        _endpoint,
        data: {
          'level': level,
          'message': message,
          'session_id': sessionId ?? currentSessionId,
          'timestamp': DateTime.now().toIso8601String(),
        },
        options: Options(
          sendTimeout: const Duration(milliseconds: 5000), // 5s is enough
          receiveTimeout: const Duration(milliseconds: 5000),
        ),
      );
    } catch (e) {
      // If we can't log remotely, we just print locally.
      // We don't want the logger itself to crash the app.
      debugPrint('[LOGGER-FAIL] Could not send log: $e');
    }
  }

  static Future<void> info(String message, {String? sessionId}) async {
    _instance.log('INFO', message, sessionId: sessionId); // Fire-and-forget without blocking UI thread
  }

  static Future<void> error(String message, {String? sessionId}) async {
    _instance.log('ERROR', message, sessionId: sessionId); // Fire-and-forget
  }

  static Future<void> action(String message, {String? sessionId}) async {
    _instance.log('ACTION', message, sessionId: sessionId); // Fire-and-forget
  }
}
