import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:dio/dio.dart';
import 'package:shared_preferences/shared_preferences.dart';

class ApiClient {
  static String get baseUrl {
    if (kIsWeb) {
      return 'http://localhost:8000'; // Chrome/Web
    }
    return 'http://10.0.2.2:8000'; // Android emulator
    // return 'http://localhost:8000'; // iOS simulator
  }

  late final Dio _dio;

  ApiClient() {
    _dio = Dio(BaseOptions(
      baseUrl: baseUrl,
      connectTimeout: const Duration(seconds: 10),
      receiveTimeout: const Duration(seconds: 30),
      headers: {
        'Content-Type': 'application/json',
      },
    ));

    _dio.interceptors.add(InterceptorsWrapper(
      onRequest: _onRequest,
      onError: _onError,
    ));
  }

  Future<void> _onRequest(
    RequestOptions options,
    RequestInterceptorHandler handler,
  ) async {
    final prefs = await SharedPreferences.getInstance();
    final token = prefs.getString('access_token');
    if (token != null) {
      options.headers['Authorization'] = 'Bearer $token';
    }
    handler.next(options);
  }

  void _onError(DioException error, ErrorInterceptorHandler handler) {
    if (error.response?.statusCode == 401) {
      // Token expired, redirect to login
      SharedPreferences.getInstance().then((prefs) {
        prefs.remove('access_token');
      });
    }
    handler.next(error);
  }

  Dio get client => _dio;

  // Auth
  Future<Response> register(Map<String, dynamic> data) =>
      _dio.post('/api/v1/auth/register', data: data);

  Future<Response> login(Map<String, dynamic> data) =>
      _dio.post('/api/v1/auth/login', data: data);

  Future<Response> getMe() => _dio.get('/api/v1/auth/me');

  Future<Response> updatePushToken(String token, String platform) =>
      _dio.post('/api/v1/auth/push-token', data: {
        'push_token': token,
        'push_platform': platform,
      });

  // Characters
  Future<Response> getCharacters() => _dio.get('/api/v1/characters');

  Future<Response> getCharactersWithRelation() =>
      _dio.get('/api/v1/characters/with-relation');

  Future<Response> selectCharacter(String characterId) =>
      _dio.post('/api/v1/characters/select', data: {
        'character_id': characterId,
      });

  Future<Response> getRelation(String characterId) =>
      _dio.get('/api/v1/characters/$characterId/relation');

  // Chat
  Future<Response> getChatHistory(String characterId, {int limit = 50, int offset = 0}) =>
      _dio.get('/api/v1/chat/$characterId/history', queryParameters: {
        'limit': limit,
        'offset': offset,
      });

  // Memory
  Future<Response> getMemories(String characterId, {String? category}) =>
      _dio.get('/api/v1/memory/$characterId', queryParameters: {
        if (category != null) 'category': category,
      });

  Future<Response> deleteMemory(String characterId, String memoryId) =>
      _dio.delete('/api/v1/memory/$characterId/$memoryId');

  // Settings
  Future<Response> getSettings() => _dio.get('/api/v1/settings');

  Future<Response> updateSettings(Map<String, dynamic> settings) =>
      _dio.put('/api/v1/settings', data: {'settings': settings});
}

final apiClient = ApiClient();
