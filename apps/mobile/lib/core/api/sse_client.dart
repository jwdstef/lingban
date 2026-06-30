import 'dart:async';
import 'dart:convert';
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:dio/dio.dart';
import 'package:shared_preferences/shared_preferences.dart';

class SSEClient {
  static String get baseUrl {
    if (kIsWeb) {
      return 'http://localhost:8000'; // Chrome/Web
    }
    return 'http://10.0.2.2:8000'; // Android emulator
  }

  /// 发送消息并接收 SSE 流式响应
  static Stream<String> sendMessage({
    required String characterId,
    required String content,
    String messageType = 'text',
  }) async* {
    final prefs = await SharedPreferences.getInstance();
    final token = prefs.getString('access_token');

    final dio = Dio(BaseOptions(
      baseUrl: baseUrl,
      headers: {
        'Content-Type': 'application/json',
        if (token != null) 'Authorization': 'Bearer $token',
      },
      receiveTimeout: const Duration(minutes: 5),
    ));

    try {
      final response = await dio.post<ResponseBody>(
        '/api/v1/chat/$characterId/message',
        data: {
          'content': content,
          'message_type': messageType,
        },
        options: Options(responseType: ResponseType.stream),
      );

      final stream = response.data!.stream;
      final buffer = StringBuffer();

      await for (final chunk in stream) {
        final text = utf8.decode(chunk);
        buffer.write(text);

        // 解析 SSE 格式
        final lines = buffer.toString().split('\n');
        buffer.clear();

        for (final line in lines) {
          if (line.startsWith('data: ')) {
            final data = line.substring(6);
            if (data == '[DONE]') {
              return;
            }
            if (data.isNotEmpty) {
              yield data;
            }
          } else if (line.isNotEmpty) {
            // 不完整的行，放回缓冲区
            buffer.write(line);
            buffer.write('\n');
          }
        }
      }
    } on DioException catch (e) {
      yield '[错误: ${e.message}]';
    } catch (e) {
      yield '[错误: $e]';
    }
  }
}
