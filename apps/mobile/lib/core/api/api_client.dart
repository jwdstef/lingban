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

  Future<Response> updateMemoryEnabled(bool enabled) =>
      _dio.put('/api/v1/memory/toggle', data: {
        'memory_enabled': enabled,
      });

  Future<Response> exportUserData() => _dio.get('/api/v1/data/export');

  Future<Response> deleteAccount({
    required String confirm,
    String? reason,
  }) =>
      _dio.post('/api/v1/data/delete-account', data: {
        'confirm': confirm,
        if (reason != null && reason.trim().isNotEmpty) 'reason': reason.trim(),
      });

  Future<Response> getSubscription() => _dio.get('/api/v1/subscription');

  Future<Response> createSubscription(String plan) =>
      _dio.post('/api/v1/subscription/create', data: {'plan': plan});

  Future<Response> cancelSubscription() =>
      _dio.post('/api/v1/subscription/cancel');

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

  Future<Response> sendVoiceMessage(
    String characterId, {
    required Uint8List audioBytes,
    String filename = 'voice.wav',
    String contentType = 'audio/wav',
    String? transcript,
    bool includeTts = false,
  }) {
    final formData = FormData.fromMap({
      if (transcript != null && transcript.trim().isNotEmpty)
        'transcript': transcript.trim(),
      'include_tts': includeTts.toString(),
      'audio': MultipartFile.fromBytes(
        audioBytes,
        filename: filename,
        contentType: DioMediaType.parse(contentType),
      ),
    });
    return _dio.post('/api/v1/chat/$characterId/voice', data: formData);
  }

  // Memory
  Future<Response> getMemories(String characterId,
          {String? category, String? query}) =>
      _dio.get('/api/v1/memory/$characterId', queryParameters: {
        if (category != null) 'category': category,
        if (query != null && query.isNotEmpty) 'query': query,
      });

  Future<Response> updateMemory(
          String characterId, String memoryId, Map<String, dynamic> data) =>
      _dio.put('/api/v1/memory/$characterId/$memoryId', data: data);

  Future<Response> deleteMemory(String characterId, String memoryId) =>
      _dio.delete('/api/v1/memory/$characterId/$memoryId');

  Future<Response> clearAllMemories(String characterId) =>
      _dio.delete('/api/v1/memory/$characterId/all');

  // Emotion diary
  Future<Response> getEmotionDiary({int limit = 30, int offset = 0}) =>
      _dio.get('/api/v1/emotion/diary', queryParameters: {
        'limit': limit,
        'offset': offset,
      });

  Future<Response> getEmotionTrend({int days = 14}) =>
      _dio.get('/api/v1/emotion/trend', queryParameters: {
        'days': days,
      });

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

  Future<Response> updateCareFrequency(String proactiveLevel) =>
      _dio.put('/api/v1/care/frequency', data: {
        'proactive_level': proactiveLevel,
      });

  Future<Response> updateCareDnd({
    required bool enabled,
    required String start,
    required String end,
  }) =>
      _dio.put('/api/v1/care/dnd', data: {
        'dnd_enabled': enabled,
        'dnd_start': start,
        'dnd_end': end,
      });
}

final apiClient = ApiClient();
