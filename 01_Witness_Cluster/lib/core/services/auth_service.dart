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

  // --- Login ---
  Future<Map<String, dynamic>> login(String username, String password) async {
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
      throw Exception("Connection Error: ${e.message}");
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
