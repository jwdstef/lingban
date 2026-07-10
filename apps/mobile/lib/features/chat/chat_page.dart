import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:audioplayers/audioplayers.dart';
import 'package:record/record.dart';

import '../../core/api/api_client.dart';
import '../../core/api/sse_client.dart';
import '../../core/theme/app_theme.dart';
import '../auth/providers/auth_provider.dart';

class ChatPage extends ConsumerStatefulWidget {
  final String characterId;
  final String? careMessageId;

  const ChatPage({
    super.key,
    required this.characterId,
    this.careMessageId,
  });

  @override
  ConsumerState<ChatPage> createState() => _ChatPageState();
}

class _ChatPageState extends ConsumerState<ChatPage> {
  final _messageController = TextEditingController();
  final _scrollController = ScrollController();
  final _voiceRecorder = AudioRecorder();
  final _ttsPlayer = AudioPlayer();
  final List<Uint8List> _voiceChunks = [];
  final List<_ChatMessage> _messages = [];
  StreamSubscription<Uint8List>? _voiceSubscription;
  StreamSubscription<void>? _ttsCompleteSubscription;
  Completer<void>? _voiceStreamDone;
  bool _isLoading = true;
  bool _isSending = false;
  bool _isLoadingMore = false;
  bool _isPreparingRecording = false;
  bool _isRecording = false;
  bool _scrollToBottomScheduled = false;
  bool _initialScrollToBottomDone = false;
  bool _markInitialScrollPending = false;
  String? _playingMessageId;
  bool _hasMoreMessages = true;
  bool _hasMarkedCareReply = false;
  DateTime? _recordingStartedAt;
  int _currentPage = 0;
  String? _characterName;
  late Future<Map<String, dynamic>> _relationFuture;

  static const int _pageSize = 20;
  static const int _voiceSampleRate = 16000;
  static const int _voiceChannels = 1;

  @override
  void initState() {
    super.initState();
    _relationFuture = _fetchRelation();
    _loadHistory();
    _loadCharacterName();
    _scrollController.addListener(_onScroll);
    _ttsCompleteSubscription = _ttsPlayer.onPlayerComplete.listen((_) {
      if (mounted) setState(() => _playingMessageId = null);
    });
  }

  @override
  void dispose() {
    _messageController.dispose();
    _scrollController.removeListener(_onScroll);
    _scrollController.dispose();
    unawaited(_voiceSubscription?.cancel());
    unawaited(_ttsCompleteSubscription?.cancel());
    unawaited(_voiceRecorder.dispose());
    unawaited(_ttsPlayer.dispose());
    super.dispose();
  }

  void _onScroll() {
    if (!_initialScrollToBottomDone || !_scrollController.hasClients) return;

    // 滚动到顶部时加载更多历史消息
    if (_scrollController.position.pixels <= 0 &&
        !_isLoadingMore &&
        _hasMoreMessages) {
      _loadMoreHistory();
    }
  }

  Future<void> _loadCharacterName() async {
    try {
      final response = await apiClient.getCharacters();
      final characters = List<Map<String, dynamic>>.from(response.data);
      final char = characters.firstWhere(
        (c) => c['id'] == widget.characterId,
        orElse: () => {},
      );
      if (mounted) setState(() => _characterName = char['name'] ?? '灵伴');
    } catch (e) {
      debugPrint('加载角色名失败: $e');
    }
  }

  Future<void> _loadHistory() async {
    try {
      final response = await apiClient.getChatHistory(
        widget.characterId,
        limit: _pageSize,
        offset: 0,
      );
      final data = response.data;
      final messages = List<Map<String, dynamic>>.from(data['messages'] ?? []);
      if (mounted) {
        setState(() {
          _messages.clear();
          for (final msg in messages) {
            _messages.add(_ChatMessage(
              id: msg['id'] ?? '',
              role: msg['role'] ?? 'user',
              content: msg['content'] ?? '',
              createdAt:
                  DateTime.tryParse(msg['created_at'] ?? '') ?? DateTime.now(),
            ));
          }
          _isLoading = false;
          _hasMoreMessages = messages.length >= _pageSize;
          _currentPage = 0;
        });
        _scrollToBottom(animated: false, markInitialComplete: true);
      }
    } catch (e) {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Future<void> _loadMoreHistory() async {
    if (_isLoadingMore || !_hasMoreMessages) return;

    setState(() => _isLoadingMore = true);

    try {
      final nextPage = _currentPage + 1;
      final response = await apiClient.getChatHistory(
        widget.characterId,
        limit: _pageSize,
        offset: nextPage * _pageSize,
      );
      final data = response.data;
      final olderMessages =
          List<Map<String, dynamic>>.from(data['messages'] ?? []);

      if (mounted) {
        final previousMaxScrollExtent = _scrollController.hasClients
            ? _scrollController.position.maxScrollExtent
            : null;
        final previousPixels = _scrollController.hasClients
            ? _scrollController.position.pixels
            : null;

        setState(() {
          // 将旧消息插入到列表顶部
          final newMessages = <_ChatMessage>[];
          for (final msg in olderMessages) {
            newMessages.add(_ChatMessage(
              id: msg['id'] ?? '',
              role: msg['role'] ?? 'user',
              content: msg['content'] ?? '',
              createdAt:
                  DateTime.tryParse(msg['created_at'] ?? '') ?? DateTime.now(),
            ));
          }
          _messages.insertAll(0, newMessages);
          _currentPage = nextPage;
          _isLoadingMore = false;
          _hasMoreMessages = olderMessages.length >= _pageSize;
        });

        if (previousMaxScrollExtent != null && previousPixels != null) {
          WidgetsBinding.instance.addPostFrameCallback((_) {
            if (!mounted || !_scrollController.hasClients) return;

            final addedExtent = _scrollController.position.maxScrollExtent -
                previousMaxScrollExtent;
            final target = previousPixels + addedExtent;
            final clampedTarget = target
                .clamp(
                  _scrollController.position.minScrollExtent,
                  _scrollController.position.maxScrollExtent,
                )
                .toDouble();
            _scrollController.jumpTo(clampedTarget);
          });
        }
      }
    } catch (e) {
      if (mounted) setState(() => _isLoadingMore = false);
    }
  }

  void _scrollToBottom({
    bool animated = true,
    bool markInitialComplete = false,
  }) {
    if (markInitialComplete) {
      _markInitialScrollPending = true;
    }

    if (_scrollToBottomScheduled) return;

    _scrollToBottomScheduled = true;
    var remainingAttempts = animated ? 1 : 3;

    void scrollAfterNextFrame() {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        final didScroll = _performScrollToBottom(animated: animated);
        remainingAttempts -= 1;

        if (mounted && (!didScroll || !animated) && remainingAttempts > 0) {
          scrollAfterNextFrame();
          return;
        }

        _scrollToBottomScheduled = false;
        if (_markInitialScrollPending && mounted) {
          _initialScrollToBottomDone = true;
          _markInitialScrollPending = false;
        }
      });
    }

    scrollAfterNextFrame();
  }

  bool _performScrollToBottom({required bool animated}) {
    if (!mounted || !_scrollController.hasClients) return false;

    final target = _scrollController.position.maxScrollExtent;
    if (animated) {
      unawaited(
        _scrollController.animateTo(
          target,
          duration: const Duration(milliseconds: 220),
          curve: Curves.easeOut,
        ),
      );
    } else {
      _scrollController.jumpTo(target);
    }

    return true;
  }

  Future<void> _sendMessage() async {
    final content = _messageController.text.trim();
    if (content.isEmpty || _isSending) return;

    _messageController.clear();

    late final int aiMsgIndex;
    setState(() {
      _isSending = true;
      _messages.add(_ChatMessage(
        id: 'temp_${DateTime.now().millisecondsSinceEpoch}',
        role: 'user',
        content: content,
        createdAt: DateTime.now(),
      ));

      aiMsgIndex = _messages.length;
      _messages.add(_ChatMessage(
        id: 'temp_ai_${DateTime.now().millisecondsSinceEpoch}',
        role: 'assistant',
        content: '',
        createdAt: DateTime.now(),
        isStreaming: true,
      ));
    });
    _scrollToBottom();

    try {
      final stream = SSEClient.sendMessage(
        characterId: widget.characterId,
        content: content,
      );

      String fullResponse = '';
      await for (final chunk in stream) {
        fullResponse += chunk;
        if (mounted) {
          setState(() {
            _messages[aiMsgIndex] = _ChatMessage(
              id: _messages[aiMsgIndex].id,
              role: 'assistant',
              content: fullResponse,
              createdAt: _messages[aiMsgIndex].createdAt,
              isStreaming: true,
            );
          });
          _scrollToBottom();
        }
      }

      if (!fullResponse.startsWith('[错误:')) {
        await _markCareReplyIfNeeded();
      }

      if (mounted) {
        setState(() {
          _messages[aiMsgIndex] = _ChatMessage(
            id: _messages[aiMsgIndex].id,
            role: 'assistant',
            content: fullResponse,
            createdAt: _messages[aiMsgIndex].createdAt,
            isStreaming: false,
          );
          _isSending = false;
          _relationFuture = _fetchRelation();
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _messages[aiMsgIndex] = _ChatMessage(
            id: _messages[aiMsgIndex].id,
            role: 'assistant',
            content: '[发送失败: $e]',
            createdAt: _messages[aiMsgIndex].createdAt,
            isStreaming: false,
          );
          _isSending = false;
        });
      }
    }
  }

  Future<bool> _startVoiceRecording() async {
    if (_isSending || _isRecording || _isPreparingRecording) return false;

    setState(() => _isPreparingRecording = true);

    try {
      final hasPermission = await _voiceRecorder.hasPermission();
      if (!hasPermission) {
        if (mounted) {
          setState(() => _isPreparingRecording = false);
          _showMessage('需要麦克风权限后才能发送语音');
        }
        return false;
      }

      await _voiceSubscription?.cancel();
      _voiceChunks.clear();
      _voiceStreamDone = Completer<void>();
      final stream = await _voiceRecorder.startStream(
        const RecordConfig(
          encoder: AudioEncoder.pcm16bits,
          sampleRate: _voiceSampleRate,
          numChannels: _voiceChannels,
          autoGain: true,
          echoCancel: true,
          noiseSuppress: true,
          streamBufferSize: 4096,
        ),
      );
      _voiceSubscription = stream.listen(
        (chunk) => _voiceChunks.add(Uint8List.fromList(chunk)),
        onError: (Object error, StackTrace stackTrace) {
          debugPrint('语音录制流异常: $error');
          final done = _voiceStreamDone;
          if (done != null && !done.isCompleted) done.complete();
        },
        onDone: () {
          final done = _voiceStreamDone;
          if (done != null && !done.isCompleted) done.complete();
        },
      );

      if (mounted) {
        setState(() {
          _recordingStartedAt = DateTime.now();
          _isRecording = true;
          _isPreparingRecording = false;
        });
      }
      return true;
    } catch (e) {
      try {
        await _voiceRecorder.cancel();
      } catch (_) {}
      if (mounted) {
        setState(() {
          _isRecording = false;
          _isPreparingRecording = false;
        });
        _showMessage('录音启动失败: $e');
      }
      return false;
    }
  }

  Future<_VoiceRecording?> _stopVoiceRecording() async {
    if (!_isRecording) return null;

    final startedAt = _recordingStartedAt ?? DateTime.now();
    try {
      await _voiceRecorder.stop();
      final done = _voiceStreamDone;
      if (done != null && !done.isCompleted) {
        await done.future.timeout(
          const Duration(milliseconds: 500),
          onTimeout: () {},
        );
      }
    } catch (e) {
      if (mounted) _showMessage('录音停止失败: $e');
      return null;
    } finally {
      await _voiceSubscription?.cancel();
      _voiceSubscription = null;
      _voiceStreamDone = null;
      if (mounted) {
        setState(() {
          _isRecording = false;
          _isPreparingRecording = false;
          _recordingStartedAt = null;
        });
      }
    }

    final pcmBytes = Uint8List.fromList(
      _voiceChunks.expand((chunk) => chunk).toList(growable: false),
    );
    _voiceChunks.clear();
    if (pcmBytes.isEmpty) {
      _showMessage('没有录到声音，请重试');
      return null;
    }

    return _VoiceRecording(
      audioBytes: _buildWavFile(pcmBytes),
      duration: DateTime.now().difference(startedAt),
    );
  }

  Future<void> _cancelVoiceRecording() async {
    try {
      if (_isRecording || _isPreparingRecording) {
        await _voiceRecorder.cancel();
      }
    } catch (_) {
      try {
        await _voiceRecorder.stop();
      } catch (_) {}
    } finally {
      await _voiceSubscription?.cancel();
      _voiceSubscription = null;
      _voiceStreamDone = null;
      _voiceChunks.clear();
      if (mounted) {
        setState(() {
          _isRecording = false;
          _isPreparingRecording = false;
          _recordingStartedAt = null;
        });
      }
    }
  }

  Future<void> _sendVoiceRecording(_VoiceRecording recording) async {
    if (_isSending) return;

    final tempContent = '语音消息 ${_formatDuration(recording.duration)}';
    final userMsgIndex = _messages.length;

    setState(() {
      _isSending = true;
      _messages.add(_ChatMessage(
        id: 'temp_voice_${DateTime.now().millisecondsSinceEpoch}',
        role: 'user',
        content: tempContent,
        createdAt: DateTime.now(),
      ));
      _messages.add(_ChatMessage(
        id: 'temp_ai_voice_${DateTime.now().millisecondsSinceEpoch}',
        role: 'assistant',
        content: '正在听你说...',
        createdAt: DateTime.now(),
        isStreaming: true,
      ));
    });
    _scrollToBottom();

    final aiMsgIndex = userMsgIndex + 1;

    try {
      final response = await apiClient.sendVoiceMessage(
        widget.characterId,
        audioBytes: recording.audioBytes,
        filename: 'voice-${DateTime.now().millisecondsSinceEpoch}.wav',
        contentType: 'audio/wav',
        includeTts: true,
      );
      final data = response.data as Map<String, dynamic>;
      final transcript = (data['transcript'] as String?)?.trim();
      final reply = data['reply'] as String? ?? '';
      final ttsAudio = _ttsAudioFromResponse(data);

      await _markCareReplyIfNeeded();

      if (mounted) {
        setState(() {
          _messages[userMsgIndex] = _ChatMessage(
            id: data['user_message_id'] as String? ??
                _messages[userMsgIndex].id,
            role: 'user',
            content: transcript?.isNotEmpty == true ? transcript! : tempContent,
            createdAt: _messages[userMsgIndex].createdAt,
          );
          _messages[aiMsgIndex] = _ChatMessage(
            id: data['assistant_message_id'] as String? ??
                _messages[aiMsgIndex].id,
            role: 'assistant',
            content: reply,
            createdAt: _messages[aiMsgIndex].createdAt,
            isStreaming: false,
            ttsAudioBytes: ttsAudio?.bytes,
            ttsContentType: ttsAudio?.contentType,
          );
          _isSending = false;
          _relationFuture = _fetchRelation();
        });
        _scrollToBottom();
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _messages[aiMsgIndex] = _ChatMessage(
            id: _messages[aiMsgIndex].id,
            role: 'assistant',
            content: '[语音发送失败: $e]',
            createdAt: _messages[aiMsgIndex].createdAt,
            isStreaming: false,
          );
          _isSending = false;
        });
      }
    }
  }

  Future<void> _showVoiceRecorderSheet() async {
    if (_isSending) return;
    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: AppTheme.surfaceColor,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (sheetContext) => _VoiceRecorderSheet(
        onStart: _startVoiceRecording,
        onStop: _stopVoiceRecording,
        onCancel: _cancelVoiceRecording,
        onSend: _sendVoiceRecording,
      ),
    );
  }

  Uint8List _buildWavFile(Uint8List pcmBytes) {
    final output = Uint8List(44 + pcmBytes.length);
    final data = ByteData.view(output.buffer);

    void writeAscii(int offset, String value) {
      output.setRange(offset, offset + value.length, value.codeUnits);
    }

    writeAscii(0, 'RIFF');
    data.setUint32(4, 36 + pcmBytes.length, Endian.little);
    writeAscii(8, 'WAVE');
    writeAscii(12, 'fmt ');
    data.setUint32(16, 16, Endian.little);
    data.setUint16(20, 1, Endian.little);
    data.setUint16(22, _voiceChannels, Endian.little);
    data.setUint32(24, _voiceSampleRate, Endian.little);
    data.setUint32(28, _voiceSampleRate * _voiceChannels * 2, Endian.little);
    data.setUint16(32, _voiceChannels * 2, Endian.little);
    data.setUint16(34, 16, Endian.little);
    writeAscii(36, 'data');
    data.setUint32(40, pcmBytes.length, Endian.little);
    output.setRange(44, output.length, pcmBytes);
    return output;
  }

  String _formatDuration(Duration duration) {
    final totalSeconds = duration.inSeconds;
    final minutes = (totalSeconds ~/ 60).toString().padLeft(2, '0');
    final seconds = (totalSeconds % 60).toString().padLeft(2, '0');
    return '$minutes:$seconds';
  }

  void _showMessage(String message) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(message)),
    );
  }

  _TtsAudio? _ttsAudioFromResponse(Map<String, dynamic> data) {
    if (data['tts_status'] != 'generated') return null;
    final encoded = data['tts_audio_base64'] as String?;
    if (encoded == null || encoded.isEmpty) return null;

    try {
      return _TtsAudio(
        bytes: base64Decode(encoded),
        contentType: data['tts_content_type'] as String? ?? 'audio/mpeg',
      );
    } catch (e) {
      debugPrint('TTS 音频解码失败: $e');
      return null;
    }
  }

  Future<void> _playTtsAudio(_ChatMessage message) async {
    final audioBytes = message.ttsAudioBytes;
    if (audioBytes == null || audioBytes.isEmpty) return;

    try {
      if (_playingMessageId == message.id) {
        await _ttsPlayer.stop();
        if (mounted) setState(() => _playingMessageId = null);
        return;
      }

      await _ttsPlayer.stop();
      if (mounted) setState(() => _playingMessageId = message.id);
      await _ttsPlayer.play(
        BytesSource(
          audioBytes,
          mimeType: message.ttsContentType ?? 'audio/mpeg',
        ),
      );
    } catch (e) {
      if (mounted) {
        setState(() => _playingMessageId = null);
        _showMessage('语音播放失败: $e');
      }
    }
  }

  Future<void> _sendVoiceTranscript(String transcript) async {
    final content = transcript.trim();
    if (content.isEmpty || _isSending) return;

    setState(() => _isSending = true);
    _messages.add(_ChatMessage(
      id: 'temp_voice_${DateTime.now().millisecondsSinceEpoch}',
      role: 'user',
      content: content,
      createdAt: DateTime.now(),
    ));
    _scrollToBottom();

    final aiMsgIndex = _messages.length;
    _messages.add(_ChatMessage(
      id: 'temp_ai_voice_${DateTime.now().millisecondsSinceEpoch}',
      role: 'assistant',
      content: '正在听你说...',
      createdAt: DateTime.now(),
      isStreaming: true,
    ));
    _scrollToBottom();

    try {
      final response = await apiClient.sendVoiceMessage(
        widget.characterId,
        audioBytes: Uint8List.fromList(utf8.encode(content)),
        filename: 'voice-transcript.txt',
        contentType: 'text/plain',
        transcript: content,
      );
      final data = response.data as Map<String, dynamic>;
      final reply = data['reply'] as String? ?? '';

      await _markCareReplyIfNeeded();

      if (mounted) {
        setState(() {
          _messages[aiMsgIndex] = _ChatMessage(
            id: data['assistant_message_id'] as String? ??
                _messages[aiMsgIndex].id,
            role: 'assistant',
            content: reply,
            createdAt: _messages[aiMsgIndex].createdAt,
            isStreaming: false,
          );
          _isSending = false;
          _relationFuture = _fetchRelation();
        });
        _scrollToBottom();
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _messages[aiMsgIndex] = _ChatMessage(
            id: _messages[aiMsgIndex].id,
            role: 'assistant',
            content: '[语音发送失败: $e]',
            createdAt: _messages[aiMsgIndex].createdAt,
            isStreaming: false,
          );
          _isSending = false;
        });
      }
    }
  }

  Future<void> _showVoiceInputSheet() async {
    if (_isSending) return;
    final controller = TextEditingController();
    final transcript = await showModalBottomSheet<String>(
      context: context,
      isScrollControlled: true,
      backgroundColor: AppTheme.surfaceColor,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (sheetContext) {
        final bottomInset = MediaQuery.of(sheetContext).viewInsets.bottom;
        return Padding(
          padding: EdgeInsets.fromLTRB(20, 18, 20, 20 + bottomInset),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  const Icon(Icons.mic, color: AppTheme.spiritGlow, size: 20),
                  const SizedBox(width: 8),
                  const Text(
                    '语音消息',
                    style: TextStyle(
                      color: AppTheme.primaryColor,
                      fontSize: 18,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  const Spacer(),
                  IconButton(
                    onPressed: () => Navigator.of(sheetContext).pop(),
                    icon: Icon(
                      Icons.close,
                      color: AppTheme.primaryColor.withValues(alpha: 0.55),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              TextField(
                controller: controller,
                autofocus: true,
                minLines: 3,
                maxLines: 5,
                style: const TextStyle(color: AppTheme.primaryColor),
                decoration: InputDecoration(
                  hintText: '输入语音转写内容',
                  hintStyle: TextStyle(
                    color: AppTheme.primaryColor.withValues(alpha: 0.35),
                  ),
                ),
              ),
              const SizedBox(height: 14),
              SizedBox(
                width: double.infinity,
                child: FilledButton.icon(
                  onPressed: () {
                    Navigator.of(sheetContext).pop(controller.text);
                  },
                  icon: const Icon(Icons.mic),
                  label: const Text('发送语音'),
                ),
              ),
            ],
          ),
        );
      },
    );
    controller.dispose();

    if (transcript != null) {
      await _sendVoiceTranscript(transcript);
    }
  }

  Future<void> _markCareReplyIfNeeded() async {
    final careMessageId = widget.careMessageId;
    if (careMessageId == null || _hasMarkedCareReply) return;

    try {
      await apiClient.markCareMessageReplied(careMessageId);
      _hasMarkedCareReply = true;
    } catch (e) {
      debugPrint('标记主动关怀回复失败: $e');
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.transparent,
      // 自定义顶栏，不用 AppBar
      body: SafeArea(
        child: Column(
          children: [
            // 自定义顶栏
            _buildTopBar(),
            if (_messages.isNotEmpty) _buildMoodStrip(),
            // 消息列表
            Expanded(
              child: _isLoading
                  ? const Center(child: CircularProgressIndicator())
                  : _buildMessageList(),
            ),
            // 输入栏
            _buildInputBar(),
          ],
        ),
      ),
    );
  }

  Widget _buildTopBar() {
    final characterId =
        ref.read(authStateProvider).selectedCharacterId ?? widget.characterId;

    return Container(
      height: 88,
      padding: const EdgeInsets.fromLTRB(16, 14, 16, 0),
      decoration: BoxDecoration(
        color: AppTheme.surfaceColor.withValues(alpha: 0.82),
        border: Border(
          bottom: BorderSide(
            color: AppTheme.primaryColor.withValues(alpha: 0.08),
            width: 0.5,
          ),
        ),
      ),
      child: Row(
        children: [
          GestureDetector(
            onTap: () => context.pop(),
            child: Container(
              width: 36,
              height: 36,
              decoration: BoxDecoration(
                color: Colors.white.withValues(alpha: 0.05),
                shape: BoxShape.circle,
                border: Border.all(
                  color: Colors.white.withValues(alpha: 0.08),
                  width: 0.5,
                ),
              ),
              child: const Icon(
                Icons.arrow_back_ios_new,
                color: AppTheme.textSecondary,
                size: 17,
              ),
            ),
          ),
          const SizedBox(width: 12),
          // 角色头像
          Container(
            width: 40,
            height: 40,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              gradient: RadialGradient(
                colors: [
                  AppTheme.spiritGlow.withValues(alpha: 0.4),
                  AppTheme.spiritGlow.withValues(alpha: 0.1),
                ],
              ),
              boxShadow: [
                BoxShadow(
                  color: AppTheme.spiritGlow.withValues(alpha: 0.3),
                  blurRadius: 20,
                ),
              ],
            ),
            child: const Icon(Icons.auto_awesome,
                color: AppTheme.spiritGlow, size: 16),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  _characterName ?? '聊天',
                  style: const TextStyle(
                    color: AppTheme.primaryColor,
                    fontSize: 16,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const SizedBox(height: 2),
                FutureBuilder<Map<String, dynamic>>(
                  future: _relationFuture,
                  builder: (context, snapshot) {
                    final level = snapshot.data?['level'] as int? ?? 1;
                    final consecutiveDays =
                        snapshot.data?['consecutive_days'] as int? ?? 0;

                    String status;
                    if (consecutiveDays >= 7) {
                      status = '已陪伴 $consecutiveDays 天';
                    } else if (level >= 3) {
                      status = '老朋友';
                    } else if (level >= 2) {
                      status = '越来越熟了';
                    } else {
                      status = '刚认识';
                    }

                    return Text(
                      status,
                      style: TextStyle(
                        color: AppTheme.textSecondary.withValues(alpha: 0.72),
                        fontSize: 11,
                      ),
                    );
                  },
                ),
              ],
            ),
          ),
          _buildHeaderAction(
            icon: Icons.psychology_outlined,
            onTap: () => context.push('/memory/$characterId'),
          ),
          const SizedBox(width: 8),
          _buildHeaderAction(
            icon: Icons.more_horiz,
            onTap: _showMoreOptions,
          ),
        ],
      ),
    );
  }

  Widget _buildHeaderAction({
    required IconData icon,
    required VoidCallback onTap,
  }) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        width: 36,
        height: 36,
        decoration: BoxDecoration(
          color: Colors.white.withValues(alpha: 0.05),
          shape: BoxShape.circle,
          border: Border.all(
            color: Colors.white.withValues(alpha: 0.08),
            width: 0.5,
          ),
        ),
        child: Icon(icon, color: AppTheme.textSecondary, size: 18),
      ),
    );
  }

  Widget _buildMoodStrip() {
    final name = _characterName ?? '灵伴';
    return FutureBuilder<Map<String, dynamic>>(
      future: _relationFuture,
      builder: (context, snapshot) {
        final intimacy = snapshot.data?['intimacy'] as int? ?? 0;
        final level = snapshot.data?['level'] as int? ?? 1;

        String status;
        if (level >= 3) {
          status = '$name很想你';
        } else if (level >= 2) {
          status = '$name在等你';
        } else if (intimacy >= 50) {
          status = '$name有点担心你';
        } else {
          status = '$name醒着';
        }

        return Container(
          margin: const EdgeInsets.fromLTRB(16, 10, 16, 0),
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
          decoration: BoxDecoration(
            color: AppTheme.cardColor.withValues(alpha: 0.72),
            borderRadius: BorderRadius.circular(16),
            border: Border.all(
              color: AppTheme.spiritGlow.withValues(alpha: 0.16),
              width: 0.5,
            ),
          ),
          child: Row(
            children: [
              const Icon(Icons.auto_awesome,
                  color: AppTheme.spiritGlow, size: 14),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  status,
                  style: TextStyle(
                    color: AppTheme.primaryColor.withValues(alpha: 0.72),
                    fontSize: 12,
                    fontWeight: FontWeight.w500,
                  ),
                ),
              ),
            ],
          ),
        );
      },
    );
  }

  Future<Map<String, dynamic>> _fetchRelation() async {
    try {
      final response = await apiClient.getRelation(widget.characterId);
      return Map<String, dynamic>.from(response.data);
    } catch (_) {
      return {};
    }
  }

  Widget _buildMessageList() {
    if (_messages.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.chat_bubble_outline,
                size: 48, color: AppTheme.primaryColor.withValues(alpha: 0.2)),
            const SizedBox(height: 16),
            Text(
              '开始和 ${_characterName ?? 'TA'} 聊天吧',
              style: TextStyle(
                  color: AppTheme.primaryColor.withValues(alpha: 0.4),
                  fontSize: 14),
            ),
          ],
        ),
      );
    }

    return ListView.builder(
      controller: _scrollController,
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      itemCount: _messages.length + (_isLoadingMore ? 1 : 0),
      itemBuilder: (context, index) {
        // 顶部加载更多指示器
        if (_isLoadingMore && index == 0) {
          return const Padding(
            padding: EdgeInsets.symmetric(vertical: 16),
            child: Center(
              child: SizedBox(
                width: 20,
                height: 20,
                child: CircularProgressIndicator(strokeWidth: 2),
              ),
            ),
          );
        }
        final msgIndex = _isLoadingMore ? index - 1 : index;
        return _buildMessageBubble(_messages[msgIndex]);
      },
    );
  }

  Widget _buildMessageBubble(_ChatMessage message) {
    final isUser = message.role == 'user';

    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Row(
        mainAxisAlignment:
            isUser ? MainAxisAlignment.end : MainAxisAlignment.start,
        crossAxisAlignment: CrossAxisAlignment.end,
        children: [
          if (!isUser) ...[
            Container(
              width: 32,
              height: 32,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                gradient: RadialGradient(
                  colors: [
                    AppTheme.spiritGlow.withValues(alpha: 0.3),
                    AppTheme.spiritGlow.withValues(alpha: 0.05),
                  ],
                ),
              ),
              child: const Icon(Icons.auto_awesome,
                  color: AppTheme.spiritGlow, size: 14),
            ),
            const SizedBox(width: 8),
          ],
          Flexible(
            child: Container(
              constraints: BoxConstraints(
                maxWidth: MediaQuery.of(context).size.width * 0.75,
              ),
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
              decoration: BoxDecoration(
                color: isUser ? null : AppTheme.cardColor,
                gradient: isUser
                    ? const LinearGradient(
                        colors: [Color(0xFF7C5CFF), Color(0xFF6D28D9)],
                        begin: Alignment.topLeft,
                        end: Alignment.bottomRight,
                      )
                    : null,
                borderRadius: BorderRadius.only(
                  topLeft: const Radius.circular(18),
                  topRight: const Radius.circular(18),
                  bottomLeft: Radius.circular(isUser ? 18 : 4),
                  bottomRight: Radius.circular(isUser ? 4 : 18),
                ),
                border: Border.all(
                  color: isUser
                      ? AppTheme.primaryColor.withValues(alpha: 0.2)
                      : AppTheme.primaryColor.withValues(alpha: 0.08),
                  width: 0.5,
                ),
              ),
              child: _buildMessageContent(message, isUser),
            ),
          ),
          if (isUser) const SizedBox(width: 8),
        ],
      ),
    );
  }

  Widget _buildMessageContent(_ChatMessage message, bool isUser) {
    final hasTts = !isUser && message.ttsAudioBytes != null;
    final isPlaying = _playingMessageId == message.id;
    final text = message.content.isEmpty && message.isStreaming
        ? '...'
        : message.content;

    final textWidget = Text(
      text,
      style: TextStyle(
        color: AppTheme.primaryColor.withValues(alpha: isUser ? 0.9 : 0.85),
        fontSize: 15,
        height: 1.5,
      ),
    );

    if (!hasTts) return textWidget;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        textWidget,
        const SizedBox(height: 10),
        InkWell(
          onTap: () => _playTtsAudio(message),
          borderRadius: BorderRadius.circular(18),
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
            decoration: BoxDecoration(
              color: AppTheme.spiritGlow.withValues(alpha: 0.14),
              borderRadius: BorderRadius.circular(18),
              border: Border.all(
                color: AppTheme.spiritGlow.withValues(alpha: 0.24),
                width: 0.5,
              ),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(
                  isPlaying ? Icons.stop_rounded : Icons.play_arrow_rounded,
                  color: AppTheme.spiritGlow,
                  size: 16,
                ),
                const SizedBox(width: 4),
                Text(
                  isPlaying ? '停止' : '播放语音',
                  style: const TextStyle(
                    color: AppTheme.spiritGlow,
                    fontSize: 12,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildInputBar() {
    return Container(
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 12),
      decoration: BoxDecoration(
        color: AppTheme.surfaceColor.withValues(alpha: 0.95),
        border: Border(
          top: BorderSide(
            color: AppTheme.primaryColor.withValues(alpha: 0.1),
            width: 0.5,
          ),
        ),
      ),
      child: Row(
        children: [
          GestureDetector(
            onTap: _isSending ? null : _showVoiceRecorderSheet,
            onLongPress: _isSending ? null : _showVoiceInputSheet,
            child: Container(
              width: 44,
              height: 44,
              margin: const EdgeInsets.only(right: 8),
              decoration: BoxDecoration(
                color: AppTheme.cardColor,
                shape: BoxShape.circle,
                border: Border.all(
                  color: AppTheme.spiritGlow.withValues(alpha: 0.2),
                  width: 0.5,
                ),
              ),
              child: Icon(
                Icons.mic_none,
                color: _isSending
                    ? AppTheme.primaryColor.withValues(alpha: 0.25)
                    : AppTheme.spiritGlow,
                size: 20,
              ),
            ),
          ),
          Expanded(
            child: TextField(
              controller: _messageController,
              style: const TextStyle(color: AppTheme.primaryColor),
              decoration: InputDecoration(
                hintText: '跟${_characterName ?? 'TA'}说点什么...',
                hintStyle: TextStyle(
                    color: AppTheme.primaryColor.withValues(alpha: 0.3)),
                filled: true,
                fillColor: AppTheme.cardColor,
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(24),
                  borderSide: BorderSide.none,
                ),
                contentPadding:
                    const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
              ),
              maxLines: 4,
              minLines: 1,
              textInputAction: TextInputAction.send,
              onSubmitted: (_) => _sendMessage(),
            ),
          ),
          const SizedBox(width: 8),
          GestureDetector(
            onTap: _isSending ? null : _sendMessage,
            child: Container(
              width: 44,
              height: 44,
              decoration: BoxDecoration(
                color: _isSending
                    ? AppTheme.primaryColor.withValues(alpha: 0.2)
                    : AppTheme.spiritGlow.withValues(alpha: 0.3),
                shape: BoxShape.circle,
                border: Border.all(
                  color: _isSending
                      ? AppTheme.primaryColor.withValues(alpha: 0.1)
                      : AppTheme.spiritGlow.withValues(alpha: 0.5),
                  width: 1,
                ),
              ),
              child: Icon(
                Icons.send,
                color: _isSending
                    ? AppTheme.primaryColor.withValues(alpha: 0.3)
                    : AppTheme.spiritGlow,
                size: 18,
              ),
            ),
          ),
        ],
      ),
    );
  }

  void _showMoreOptions() {
    final characterId =
        ref.read(authStateProvider).selectedCharacterId ?? widget.characterId;
    showModalBottomSheet(
      context: context,
      backgroundColor: AppTheme.surfaceColor,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (context) => SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            ListTile(
              leading: Icon(Icons.psychology,
                  color: AppTheme.primaryColor.withValues(alpha: 0.7)),
              title: const Text('查看记忆',
                  style: TextStyle(color: AppTheme.primaryColor)),
              onTap: () {
                Navigator.pop(context);
                context.push('/memory/$characterId');
              },
            ),
            ListTile(
              leading:
                  const Icon(Icons.delete_outline, color: Colors.redAccent),
              title:
                  const Text('清空对话', style: TextStyle(color: Colors.redAccent)),
              onTap: () {
                Navigator.pop(context);
                _confirmClearHistory();
              },
            ),
          ],
        ),
      ),
    );
  }

  void _confirmClearHistory() {
    final messenger = ScaffoldMessenger.of(context);
    showDialog(
      context: context,
      builder: (dialogContext) => AlertDialog(
        backgroundColor: AppTheme.surfaceColor,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        title: const Text('确认清空'),
        content: const Text('清空后无法恢复，确定要清空所有对话吗？'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(dialogContext),
            child: Text('取消',
                style: TextStyle(
                    color: AppTheme.primaryColor.withValues(alpha: 0.5))),
          ),
          TextButton(
            onPressed: () async {
              Navigator.pop(dialogContext);
              try {
                await apiClient.clearChatHistory(widget.characterId);
                if (mounted) setState(() => _messages.clear());
              } catch (e) {
                if (mounted) {
                  messenger.showSnackBar(
                    SnackBar(content: Text('清空失败: $e')),
                  );
                }
              }
            },
            child: const Text('确认', style: TextStyle(color: Colors.redAccent)),
          ),
        ],
      ),
    );
  }
}

class _VoiceRecording {
  final Uint8List audioBytes;
  final Duration duration;

  const _VoiceRecording({
    required this.audioBytes,
    required this.duration,
  });
}

class _TtsAudio {
  final Uint8List bytes;
  final String contentType;

  const _TtsAudio({
    required this.bytes,
    required this.contentType,
  });
}

class _VoiceRecorderSheet extends StatefulWidget {
  final Future<bool> Function() onStart;
  final Future<_VoiceRecording?> Function() onStop;
  final Future<void> Function() onCancel;
  final Future<void> Function(_VoiceRecording recording) onSend;

  const _VoiceRecorderSheet({
    required this.onStart,
    required this.onStop,
    required this.onCancel,
    required this.onSend,
  });

  @override
  State<_VoiceRecorderSheet> createState() => _VoiceRecorderSheetState();
}

class _VoiceRecorderSheetState extends State<_VoiceRecorderSheet> {
  bool _isPreparing = false;
  bool _isRecording = false;
  bool _isStopping = false;
  bool _ownsActiveRecording = false;
  Duration _duration = Duration.zero;
  Timer? _timer;
  String? _error;

  @override
  void dispose() {
    _timer?.cancel();
    if (_ownsActiveRecording) {
      unawaited(widget.onCancel());
    }
    super.dispose();
  }

  Future<void> _start() async {
    if (_isPreparing || _isRecording || _isStopping) return;
    setState(() {
      _error = null;
      _isPreparing = true;
      _duration = Duration.zero;
    });

    final started = await widget.onStart();
    if (!mounted) return;

    if (!started) {
      setState(() => _isPreparing = false);
      return;
    }

    _timer?.cancel();
    _timer = Timer.periodic(const Duration(seconds: 1), (_) {
      if (!mounted) return;
      setState(() => _duration += const Duration(seconds: 1));
    });

    setState(() {
      _ownsActiveRecording = true;
      _isRecording = true;
      _isPreparing = false;
    });
  }

  Future<void> _stopAndSend() async {
    if (!_isRecording || _isStopping) return;

    _timer?.cancel();
    setState(() {
      _error = null;
      _isStopping = true;
    });

    final recording = await widget.onStop();
    if (!mounted) return;

    _ownsActiveRecording = false;
    if (recording == null) {
      setState(() {
        _isRecording = false;
        _isStopping = false;
        _error = '录音失败，请重试';
      });
      return;
    }

    setState(() {
      _isRecording = false;
      _isStopping = false;
    });
    unawaited(widget.onSend(recording));
    Navigator.of(context).pop();
  }

  Future<void> _cancel() async {
    _timer?.cancel();
    _ownsActiveRecording = false;
    await widget.onCancel();
    if (mounted) Navigator.of(context).pop();
  }

  String _formatDuration(Duration duration) {
    final totalSeconds = duration.inSeconds;
    final minutes = (totalSeconds ~/ 60).toString().padLeft(2, '0');
    final seconds = (totalSeconds % 60).toString().padLeft(2, '0');
    return '$minutes:$seconds';
  }

  @override
  Widget build(BuildContext context) {
    final busy = _isPreparing || _isStopping;
    final primaryLabel = _isRecording ? '停止并发送' : '开始录音';
    final status = _isPreparing
        ? '正在准备麦克风...'
        : _isStopping
            ? '正在整理语音...'
            : _isRecording
                ? _formatDuration(_duration)
                : '语音消息';

    return SafeArea(
      top: false,
      child: Padding(
        padding: const EdgeInsets.fromLTRB(20, 18, 20, 20),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Row(
              children: [
                const Icon(Icons.mic, color: AppTheme.spiritGlow, size: 20),
                const SizedBox(width: 8),
                const Text(
                  '语音消息',
                  style: TextStyle(
                    color: AppTheme.primaryColor,
                    fontSize: 18,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                const Spacer(),
                IconButton(
                  onPressed: busy ? null : _cancel,
                  icon: Icon(
                    Icons.close,
                    color: AppTheme.primaryColor.withValues(alpha: 0.55),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 18),
            AnimatedContainer(
              duration: const Duration(milliseconds: 180),
              width: 92,
              height: 92,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: _isRecording
                    ? AppTheme.spiritGlow.withValues(alpha: 0.18)
                    : AppTheme.cardColor,
                border: Border.all(
                  color: AppTheme.spiritGlow.withValues(
                    alpha: _isRecording ? 0.75 : 0.25,
                  ),
                ),
              ),
              child: Icon(
                _isRecording ? Icons.graphic_eq : Icons.mic_none,
                color: AppTheme.spiritGlow,
                size: 34,
              ),
            ),
            const SizedBox(height: 14),
            SizedBox(
              height: 24,
              child: Center(
                child: Text(
                  status,
                  style: TextStyle(
                    color: AppTheme.primaryColor.withValues(alpha: 0.74),
                    fontSize: 15,
                    fontWeight:
                        _isRecording ? FontWeight.w700 : FontWeight.w500,
                  ),
                ),
              ),
            ),
            if (_error != null) ...[
              const SizedBox(height: 8),
              Text(
                _error!,
                style: const TextStyle(color: Colors.redAccent, fontSize: 13),
              ),
            ],
            const SizedBox(height: 18),
            SizedBox(
              width: double.infinity,
              child: FilledButton.icon(
                onPressed: busy
                    ? null
                    : _isRecording
                        ? _stopAndSend
                        : _start,
                icon: Icon(_isRecording ? Icons.send : Icons.mic),
                label: Text(primaryLabel),
              ),
            ),
            const SizedBox(height: 8),
            SizedBox(
              width: double.infinity,
              child: TextButton(
                onPressed: busy ? null : _cancel,
                child: Text(
                  '取消',
                  style: TextStyle(
                    color: AppTheme.primaryColor.withValues(alpha: 0.55),
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _ChatMessage {
  final String id;
  final String role;
  final String content;
  final DateTime createdAt;
  final bool isStreaming;
  final Uint8List? ttsAudioBytes;
  final String? ttsContentType;

  _ChatMessage({
    required this.id,
    required this.role,
    required this.content,
    required this.createdAt,
    this.isStreaming = false,
    this.ttsAudioBytes,
    this.ttsContentType,
  });
}
