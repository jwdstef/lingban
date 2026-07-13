import 'dart:async';
import 'dart:convert';

import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart' show debugPrint, kDebugMode;
import 'package:shared_preferences/shared_preferences.dart';

import '../config/app_config.dart';

class SSEClient {
  static Stream<String> sendMessage({
    required String characterId,
    required String content,
    String messageType = 'text',
  }) async* {
    await for (final event in sendMessageEvents(
      characterId: characterId,
      content: content,
      messageType: messageType,
    )) {
      if (event is SSEContentEvent) {
        yield event.content;
      } else if (event is SSESilenceEvent) {
        yield '[SILENCED]';
      } else if (event is SSEErrorEvent) {
        yield '[错误: ${event.message}]';
      }
    }
  }

  /// 结构化 SSE 事件流：支持正文 / 沉默 / 记忆溯源
  static Stream<SSEEvent> sendMessageEvents({
    required String characterId,
    required String content,
    String messageType = 'text',
  }) async* {
    final requestId = DateTime.now().microsecondsSinceEpoch.toRadixString(16);
    final stopwatch = Stopwatch()..start();
    final prefs = await SharedPreferences.getInstance();
    final token = prefs.getString('access_token');
    _debugLog(
      requestId,
      'start character=$characterId contentChars=${content.length}',
    );

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
      _debugLog(
        requestId,
        'connected status=${response.statusCode} elapsedMs=${stopwatch.elapsedMilliseconds}',
      );

      final decodedStream =
          response.data!.stream.cast<List<int>>().map((bytes) {
        _debugLog(
          requestId,
          'rawChunk bytes=${bytes.length} elapsedMs=${stopwatch.elapsedMilliseconds}',
        );
        return bytes;
      }).transform(utf8.decoder);
      String buffer = '';
      var eventCount = 0;
      var contentChunkCount = 0;
      var firstContentLogged = false;

      await for (final chunk in decodedStream) {
        buffer += chunk;

        while (true) {
          final boundary = _findEventBoundary(buffer);
          if (boundary == null) break;

          final event = buffer.substring(0, boundary.start);
          buffer = buffer.substring(boundary.end);

          for (final comment in _parseEventComments(event)) {
            _debugLog(
              requestId,
              'comment "$comment" elapsedMs=${stopwatch.elapsedMilliseconds}',
            );
          }

          for (final data in _parseEventData(event)) {
            eventCount += 1;
            _debugLog(
              requestId,
              'event=$eventCount dataChars=${data.length} elapsedMs=${stopwatch.elapsedMilliseconds}',
            );
            if (data == '[DONE]') {
              _debugLog(
                requestId,
                'done contentChunks=$contentChunkCount elapsedMs=${stopwatch.elapsedMilliseconds}',
              );
              return;
            }

            final parsed = _eventFromData(data);
            if (parsed is SSEContentEvent) {
              contentChunkCount += 1;
              if (!firstContentLogged) {
                firstContentLogged = true;
                _debugLog(
                  requestId,
                  'firstContent elapsedMs=${stopwatch.elapsedMilliseconds} chars=${parsed.content.length}',
                );
              } else {
                _debugLog(
                  requestId,
                  'contentChunk=$contentChunkCount chars=${parsed.content.length} elapsedMs=${stopwatch.elapsedMilliseconds}',
                );
              }
            }
            if (parsed != null) {
              yield parsed;
            }
          }
        }
      }

      for (final data in _parseEventData(buffer)) {
        eventCount += 1;
        if (data == '[DONE]') {
          _debugLog(
            requestId,
            'done contentChunks=$contentChunkCount elapsedMs=${stopwatch.elapsedMilliseconds}',
          );
          return;
        }

        final parsed = _eventFromData(data);
        if (parsed is SSEContentEvent) {
          contentChunkCount += 1;
          if (!firstContentLogged) {
            firstContentLogged = true;
            _debugLog(
              requestId,
              'firstContent elapsedMs=${stopwatch.elapsedMilliseconds} chars=${parsed.content.length}',
            );
          } else {
            _debugLog(
              requestId,
              'contentChunk=$contentChunkCount chars=${parsed.content.length} elapsedMs=${stopwatch.elapsedMilliseconds}',
            );
          }
        }
        if (parsed != null) {
          yield parsed;
        }
      }
    } on DioException catch (e) {
      _debugLog(
        requestId,
        'dioError type=${e.type} message=${e.message} elapsedMs=${stopwatch.elapsedMilliseconds}',
      );
      yield SSEErrorEvent(e.message ?? e.toString());
    } catch (e) {
      _debugLog(
        requestId,
        'error $e elapsedMs=${stopwatch.elapsedMilliseconds}',
      );
      yield SSEErrorEvent(e.toString());
    }
  }

  static void _debugLog(String requestId, String message) {
    if (!kDebugMode) return;
    debugPrint('[SSE $requestId] $message');
  }

  static _EventBoundary? _findEventBoundary(String buffer) {
    final lfIndex = buffer.indexOf('\n\n');
    final crlfIndex = buffer.indexOf('\r\n\r\n');

    if (lfIndex == -1 && crlfIndex == -1) return null;
    if (lfIndex == -1) {
      return _EventBoundary(crlfIndex, crlfIndex + 4);
    }
    if (crlfIndex == -1 || lfIndex < crlfIndex) {
      return _EventBoundary(lfIndex, lfIndex + 2);
    }
    return _EventBoundary(crlfIndex, crlfIndex + 4);
  }

  static Iterable<String> _parseEventData(String event) sync* {
    final normalized = event.replaceAll('\r\n', '\n').replaceAll('\r', '\n');
    final dataLines = <String>[];

    for (final line in normalized.split('\n')) {
      if (!line.startsWith('data:')) continue;

      var value = line.substring(5);
      if (value.startsWith(' ')) {
        value = value.substring(1);
      }
      dataLines.add(value);
    }

    if (dataLines.isNotEmpty) {
      yield dataLines.join('\n');
    }
  }

  static Iterable<String> _parseEventComments(String event) sync* {
    final normalized = event.replaceAll('\r\n', '\n').replaceAll('\r', '\n');

    for (final line in normalized.split('\n')) {
      if (line.startsWith(':')) {
        yield line.substring(1).trimLeft();
      }
    }
  }

  static SSEEvent? _eventFromData(String data) {
    if (!data.startsWith('{')) {
      return data.isEmpty ? null : SSEContentEvent(data);
    }

    try {
      final decoded = jsonDecode(data);
      if (decoded is! Map<String, dynamic>) {
        return SSEContentEvent(data);
      }

      // 记忆溯源：{"memory_sources":[...]}
      if (decoded.containsKey('memory_sources')) {
        final raw = decoded['memory_sources'];
        final sources = <Map<String, dynamic>>[];
        if (raw is List) {
          for (final item in raw) {
            if (item is Map) {
              sources.add(Map<String, dynamic>.from(item));
            }
          }
        }
        return SSEMemorySourcesEvent(sources);
      }

      // 结束元信息：message_id 本身不渲染
      if (decoded.containsKey('message_id') &&
          !decoded.containsKey('content') &&
          !decoded.containsKey('delta')) {
        return null;
      }

      // 沉默标记：后端决定不回复时发送 {"silenced": true}
      if (decoded['silenced'] == true) {
        return const SSESilenceEvent();
      }

      final delta = decoded['delta'];
      if (delta is String && delta.isNotEmpty) {
        return SSEContentEvent(delta);
      }

      final content = decoded['content'];
      if (content is String && content.isNotEmpty) {
        return SSEContentEvent(content);
      }
    } catch (_) {
      return SSEContentEvent(data);
    }

    return null;
  }
}

sealed class SSEEvent {
  const SSEEvent();
}

class SSEContentEvent extends SSEEvent {
  final String content;
  const SSEContentEvent(this.content);
}

class SSESilenceEvent extends SSEEvent {
  const SSESilenceEvent();
}

class SSEMemorySourcesEvent extends SSEEvent {
  final List<Map<String, dynamic>> sources;
  const SSEMemorySourcesEvent(this.sources);
}

class SSEErrorEvent extends SSEEvent {
  final String message;
  const SSEErrorEvent(this.message);
}

class _EventBoundary {
  final int start;
  final int end;

  const _EventBoundary(this.start, this.end);
}
