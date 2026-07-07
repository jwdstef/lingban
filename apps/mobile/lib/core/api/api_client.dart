import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../config/app_config.dart';

class ApiClient {
  late final Dio _dio;

  /// 401 时调用的回调，用于通知 auth provider 清除状态
  VoidCallback? onUnauthorized;

  ApiClient() {
    _dio = Dio(BaseOptions(
      baseUrl: AppConfig.baseUrl,
      connectTimeout: const Duration(seconds: 10),
      receiveTimeout: const Duration(seconds: 30),
      headers: {'Content-Type': 'application/json'},
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
      SharedPreferences.getInstance().then((prefs) {
        prefs.remove('access_token');
      });
      onUnauthorized?.call();
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

  Future<Response> updateSettings(Map<String, dynamic> settings) =>
      _dio.put('/api/v1/settings', data: {'settings': settings});

  Future<Response> getSettings() => _dio.get('/api/v1/settings');

  // Characters
  Future<Response> getCharacters() => _dio.get('/api/v1/characters');

  Future<Response> selectCharacter(String characterId) =>
      _dio.post('/api/v1/characters/select', data: {
        'character_id': characterId,
      });

  Future<Response> getRelation(String characterId) =>
      _dio.get('/api/v1/characters/$characterId/relation');

  // Chat
  Future<Response> getChatHistory(String characterId,
          {int limit = 50, int offset = 0}) =>
      _dio.get('/api/v1/chat/$characterId/history', queryParameters: {
        'limit': limit,
        'offset': offset,
      });

  Future<Response> clearChatHistory(String characterId) =>
      _dio.delete('/api/v1/chat/$characterId/history');

  // Memory
  Future<Response> getMemories(String characterId, {String? category}) =>
      _dio.get('/api/v1/memory/$characterId', queryParameters: {
        if (category != null) 'category': category,
      });

  Future<Response> deleteMemory(String characterId, String memoryId) =>
      _dio.delete('/api/v1/memory/$characterId/$memoryId');

  Future<Response> clearAllMemories(String characterId) =>
      _dio.delete('/api/v1/memory/$characterId/all');

  // Proactive care
  Future<Response> getCareMessages({
    int limit = 20,
    int offset = 0,
    String? characterId,
  }) =>
      _dio.get('/api/v1/care/messages', queryParameters: {
        'limit': limit,
        'offset': offset,
        if (characterId != null) 'character_id': characterId,
      });

  Future<Response> markCareMessageClicked(String messageId) =>
      _dio.post('/api/v1/care/messages/$messageId/click');

  Future<Response> markCareMessageReplied(String messageId) =>
      _dio.post('/api/v1/care/messages/$messageId/reply');
}

final apiClient = ApiClient();
