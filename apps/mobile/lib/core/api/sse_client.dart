import 'dart:async';
import 'dart:convert';
import 'package:dio/dio.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../config/app_config.dart';

class SSEClient {
  /// 发送消息并接收 SSE 流式响应
  /// 使用 utf8.decoder + LineSplitter 确保中文多字节安全
  static Stream<String> sendMessage({
    required String characterId,
    required String content,
    String messageType = 'text',
  }) async* {
    final prefs = await SharedPreferences.getInstance();
    final token = prefs.getString('access_token');

    final dio = Dio(BaseOptions(
      baseUrl: AppConfig.baseUrl,
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

      // 用 utf8.decoder + LineSplitter 安全处理流式数据
      final byteStream = response.data!.stream;
      final decodedStream =
          byteStream.transform(const Utf8Decoder(allowMalformed: true));
      final lineStream = decodedStream.transform(const LineSplitter());

      await for (final line in lineStream) {
        if (line.startsWith('data: ')) {
          final data = line.substring(6);

          // 跳过 [DONE] 信号
          if (data == '[DONE]') {
            return;
          }

          // 跳过 message_id JSON 协议数据
          if (data.startsWith('{') && data.contains('message_id')) {
            continue;
          }

          if (data.isNotEmpty) {
            yield data;
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
