import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import '../../services/api_service.dart';

final sessionServiceProvider = Provider((ref) => SessionService());

class SessionService {
  final Dio _dio = Dio(BaseOptions(baseUrl: ApiService.baseUrl));
  final FlutterSecureStorage _storage;

  SessionService([FlutterSecureStorage? storage]) 
      : _storage = storage ?? const FlutterSecureStorage() {
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

  Future<List<Map<String, dynamic>>> getSessions(String userId) async {
    try {
      final response = await _dio.get('/surveyor/sessions', queryParameters: {
        'user_id': userId,
      });
      return List<Map<String, dynamic>>.from(response.data);
    } catch (e) {
      throw Exception("Failed to load sessions: ${e.toString()}");
    }
  }

  Future<Map<String, dynamic>> createSession(String title, String surveyorId) async {
    try {
      final response = await _dio.post('/surveyor/sessions', data: {
        'title': title,
        'surveyor_id': surveyorId,
        'project_id': '11111111-1111-1111-1111-111111111111' // Simulation Project UUID
      });
      return response.data;
    } catch (e) {
      throw Exception("Failed to create session: ${e.toString()}");
    }
  }
}
