import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/constants/app_constants.dart';

/// API 服务 - 统一网络请求
final apiServiceProvider = Provider<ApiService>((ref) {
  return ApiService();
});

class ApiService {
  late final Dio _dio;

  ApiService() {
    _dio = Dio(BaseOptions(
      baseUrl: '${AppConstants.baseUrl}${AppConstants.apiPrefix}',
      connectTimeout: const Duration(seconds: 10),
      receiveTimeout: const Duration(seconds: 30),
      headers: {
        'Content-Type': 'application/json',
      },
    ));

    // 拦截器 - 添加 Token
    _dio.interceptors.add(InterceptorsWrapper(
      onRequest: (options, handler) async {
        // TODO: 从本地存储获取 token
        // final token = await _getToken();
        // if (token != null) {
        //   options.headers['Authorization'] = 'Bearer $token';
        // }
        handler.next(options);
      },
      onError: (error, handler) {
        // TODO: 统一错误处理
        handler.next(error);
      },
    ));
  }

  // Auth
  Future<Response> login(Map<String, dynamic> data) {
    return _dio.post('/auth/login', data: data);
  }

  Future<Response> register(Map<String, dynamic> data) {
    return _dio.post('/auth/register', data: data);
  }

  // Characters
  Future<Response> getCharacters() {
    return _dio.get('/characters');
  }

  Future<Response> getCharacter(String id) {
    return _dio.get('/characters/$id');
  }

  Future<Response> selectCharacter(String characterId) {
    return _dio.post('/characters/select', data: {'character_id': characterId});
  }

  // Chat
  Future<Response> getChatHistory(String characterId, {int limit = 50, int offset = 0}) {
    return _dio.get('/chat/$characterId/history', queryParameters: {
      'limit': limit,
      'offset': offset,
    });
  }

  Future<Response> sendMessage(String characterId, Map<String, dynamic> data) {
    return _dio.post('/chat/$characterId/message', data: data);
  }

  // Memory
  Future<Response> getMemories(String characterId, {String? category}) {
    final params = <String, dynamic>{};
    if (category != null) params['category'] = category;
    return _dio.get('/memory/$characterId', queryParameters: params);
  }

  Future<Response> deleteMemory(String characterId, String memoryId) {
    return _dio.delete('/memory/$characterId/$memoryId');
  }

  // Settings
  Future<Response> getSettings() {
    return _dio.get('/settings');
  }

  Future<Response> updateSettings(Map<String, dynamic> data) {
    return _dio.put('/settings', data: data);
  }
}
