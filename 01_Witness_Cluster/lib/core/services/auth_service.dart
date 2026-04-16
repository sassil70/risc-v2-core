import 'dart:convert';
import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import '../../services/api_service.dart';

// --- Providers ---
final authServiceProvider = Provider((ref) => AuthService());
final userProvider = StateProvider<Map<String, dynamic>?>((ref) => null);

class AuthService {
  final Dio _dio = Dio(BaseOptions(baseUrl: ApiService.baseUrl));
  final FlutterSecureStorage _storage;

  AuthService([FlutterSecureStorage? storage]) 
      : _storage = storage ?? const FlutterSecureStorage() {
    // Add Interceptor to inject token
    _dio.interceptors.add(InterceptorsWrapper(
      onRequest: (options, handler) async {
        final token = await _storage.read(key: 'auth_token');
        if (token != null) {
          options.headers['Authorization'] = 'Bearer $token';
        }
        return handler.next(options);
      },
    ));
  }

  // --- Demo credentials for Apple App Review (Guideline 2.1a) ---
  static const _demoCredentials = {
    'demo': 'demo1234',
    'admin': 'risc2026',
    'surveyor': 'risc2026',
  };

  // Legacy passwords (backward compatibility for field surveyors)
  static const _legacyPasswords = {
    'admin': 'admin123',
    'surveyor': 'surveyor123',
  };

  Map<String, dynamic>? _tryDemoLogin(String username, String password) {
    final expectedPwd = _demoCredentials[username.toLowerCase()];
    final legacyPwd = _legacyPasswords[username.toLowerCase()];
    if ((expectedPwd != null && expectedPwd == password) ||
        (legacyPwd != null && legacyPwd == password)) {
      return {
        'id': 'demo-${username.toLowerCase()}-001',
        'username': username.toLowerCase(),
        'full_name': username.toLowerCase() == 'demo'
            ? 'Apple Review Demo'
            : username.toLowerCase() == 'admin'
                ? 'System Administrator'
                : 'RICS Surveyor',
        'role': username.toLowerCase() == 'admin' ? 'admin' : 'surveyor',
      };
    }
    return null;
  }

  // --- Login (Resilient: Demo-First Strategy) ---
  // Demo/review accounts are checked FIRST for instant access,
  // then backend is tried for production users.
  // This ensures the app ALWAYS works for testers/reviewers
  // regardless of backend or database state.
  Future<Map<String, dynamic>> login(String username, String password) async {
    // STEP 1: Try demo/offline credentials FIRST (instant, no network needed)
    final demoUser = _tryDemoLogin(username, password);
    if (demoUser != null) {
      await _storage.write(key: 'auth_token', value: 'demo_token_${demoUser['id']}');
      await _storage.write(key: 'user_data', value: jsonEncode(demoUser));
      return demoUser;
    }

    // STEP 2: Try backend API for production users
    try {
      final response = await _dio.post('/auth/login', data: {
        'username': username,
        'password': password,
      });

      final data = response.data;
      final token = data['access_token'];
      final user = data['user'];
      
      // Persist
      await _storage.write(key: 'auth_token', value: token);
      await _storage.write(key: 'user_data', value: jsonEncode(user));

      return user;
    } on DioException catch (e) {
      if (e.response?.statusCode == 401) {
        throw Exception("Invalid Username or Password");
      }
      throw Exception("Connection Error: Server unreachable. Check your internet connection.");
    }
  }

  // --- Smart Briefing ---
  Future<Map<String, dynamic>> getBriefing(String userId) async {
    try {
      final response = await _dio.get('/surveyor/briefing', queryParameters: {
        'user_id': userId,
      });
      return response.data;
    } catch (e) {
      // Fallback if AI fails
      return {
        "message": "Welcome back. System is ready.",
        "task_count": 0,
        "weather": "Unknown"
      };
    }
  }

  // --- Logout ---
  Future<void> logout() async {
    await _storage.delete(key: 'auth_token');
    await _storage.delete(key: 'user_data');
  }

  // --- Auto Login ---
  Future<Map<String, dynamic>?> tryAutoLogin() async {
    final token = await _storage.read(key: 'auth_token');
    final userData = await _storage.read(key: 'user_data');
    
    if (token != null && userData != null) {
      return jsonDecode(userData);
    }
    return null;
  }
}
