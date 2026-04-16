import 'package:flutter/foundation.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:witness_v2/core/services/auth_service.dart';
import 'package:witness_v2/core/services/session_service.dart';

// --- Mock Storage ---
class MockSecureStorage implements FlutterSecureStorage {
  final Map<String, String> _storage = {};

  @override
  Future<String?> read({
    required String key,
    IOSOptions? iOptions,
    AndroidOptions? aOptions,
    LinuxOptions? lOptions,
    WebOptions? webOptions,
    MacOsOptions? mOptions,
    WindowsOptions? wOptions,
  }) async {
    return _storage[key];
  }

  @override
  Future<void> write({
    required String key,
    required String? value,
    IOSOptions? iOptions,
    AndroidOptions? aOptions,
    LinuxOptions? lOptions,
    WebOptions? webOptions,
    MacOsOptions? mOptions,
    WindowsOptions? wOptions,
  }) async {
    if (value != null) _storage[key] = value;
  }

  @override
  Future<void> delete({
    required String key,
    IOSOptions? iOptions,
    AndroidOptions? aOptions,
    LinuxOptions? lOptions,
    WebOptions? webOptions,
    MacOsOptions? mOptions,
    WindowsOptions? wOptions,
  }) async {
    _storage.remove(key);
  }

  @override
  Future<void> deleteAll({
    IOSOptions? iOptions,
    AndroidOptions? aOptions,
    LinuxOptions? lOptions,
    WebOptions? webOptions,
    MacOsOptions? mOptions,
    WindowsOptions? wOptions,
  }) async {
    _storage.clear();
  }

  @override
  Future<Map<String, String>> readAll({
    IOSOptions? iOptions,
    AndroidOptions? aOptions,
    LinuxOptions? lOptions,
    WebOptions? webOptions,
    MacOsOptions? mOptions,
    WindowsOptions? wOptions,
  }) async {
    return _storage;
  }

  @override
  Future<bool> containsKey({
    required String key,
    IOSOptions? iOptions,
    AndroidOptions? aOptions,
    LinuxOptions? lOptions,
    WebOptions? webOptions,
    MacOsOptions? mOptions,
    WindowsOptions? wOptions,
  }) async {
    return _storage.containsKey(key);
  }

  // Boilerplate to satisfy interface
  @override
  AndroidOptions get aOptions => const AndroidOptions();
  @override
  IOSOptions get iOptions => const IOSOptions();
  @override
  LinuxOptions get lOptions => const LinuxOptions();
  @override
  MacOsOptions get mOptions => const MacOsOptions();
  @override
  WindowsOptions get wOptions => const WindowsOptions();
  @override
  WebOptions get webOptions => const WebOptions();

  @override
  void registerListener({
    required String key,
    required ValueChanged<String?> listener,
  }) {}
  @override
  void unregisterAllListeners() {}
  @override
  void unregisterListener({
    required String key,
    required ValueChanged<String?> listener,
  }) {}
  @override
  void unregisterAllListenersForKey({required String key}) {}

  @override
  Stream<bool>? get onCupertinoProtectedDataAvailabilityChanged => null;

  @override
  Future<bool?> isCupertinoProtectedDataAvailable() async => true;
}

// --- Driver ---
void main() async {
  print("\n--- 🚀 Starting RISC V2 Simulation Driver ---\n");

  // 1. Setup
  final mockStorage = MockSecureStorage();
  final authService = AuthService(mockStorage); // Inject Mock
  final sessionService = SessionService(mockStorage); // Inject Mock

  try {
    // 2. Login Flow
    print("🔹 Test 1: Authenticating as 'sassil'...");
    final user = await authService.login("sassil", "1234");
    print("✅ Login Success! User ID: ${user['id']}");
    print("   Token stored in MockStorage.");

    // 3. Briefing Flow
    print("\n🔹 Test 2: Fetching Smart Briefing...");
    final briefing = await authService.getBriefing(user['id']);
    print("✅ Briefing Received:");
    print("   Message: ${briefing['message']}");
    print("   Tasks: ${briefing['task_count']}");

    // 4. Session Creation Flow
    print("\n🔹 Test 3: Creating New Session 'Simulated Estate'...");
    final newSession = await sessionService.createSession(
      "Simulated Estate",
      user['id'],
    );
    print("✅ Session Created! ID: ${newSession['id']}");

    // 5. Session List Flow
    print("\n🔹 Test 4: Verifying Session List...");
    final sessions = await sessionService.getSessions(user['id']);
    bool found = sessions.any((s) => s['id'] == newSession['id']);

    if (found) {
      print("✅ Session '${newSession['title']}' found in list.");
      print("   Total Sessions: ${sessions.length}");
    } else {
      print("❌ CRITICAL: Created session NOT found in list!");
    }

    print("\n--- ✨ Simulation Complete: ALL SYSTEMS GO ---\n");
  } catch (e) {
    print("\n❌ SIMULATION FAILED: $e");
  }
}
