import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api/api_client.dart';
import '../../core/api/sse_client.dart';
import '../../core/theme/app_theme.dart';

class ChatPage extends ConsumerStatefulWidget {
  final String characterId;

  const ChatPage({super.key, required this.characterId});

  @override
  ConsumerState<ChatPage> createState() => _ChatPageState();
}

class _ChatPageState extends ConsumerState<ChatPage> {
  final _messageController = TextEditingController();
  final _scrollController = ScrollController();
  final List<_ChatMessage> _messages = [];
  bool _isLoading = true;
  bool _isSending = false;
  String? _characterName;

  @override
  void initState() {
    super.initState();
    _loadHistory();
    _loadCharacterName();
  }

  @override
  void dispose() {
    _messageController.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  Future<void> _loadCharacterName() async {
    try {
      final response = await apiClient.getCharacters();
      final characters = List<Map<String, dynamic>>.from(response.data);
      final char = characters.firstWhere(
        (c) => c['id'] == widget.characterId,
        orElse: () => {},
      );
      if (mounted) {
        setState(() => _characterName = char['name'] ?? '灵伴');
      }
    } catch (e) {
      debugPrint('加载角色名失败: $e');
    }
  }

  Future<void> _loadHistory() async {
    try {
      final response = await apiClient.getChatHistory(widget.characterId);
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
              createdAt: DateTime.tryParse(msg['created_at'] ?? '') ?? DateTime.now(),
            ));
          }
          _isLoading = false;
        });
        _scrollToBottom();
      }
    } catch (e) {
      if (mounted) {
        setState(() => _isLoading = false);
      }
    }
  }

  void _scrollToBottom() {
    if (_scrollController.hasClients) {
      Future.delayed(const Duration(milliseconds: 100), () {
        _scrollController.animateTo(
          _scrollController.position.maxScrollExtent,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOut,
        );
      });
    }
  }

  Future<void> _sendMessage() async {
    final content = _messageController.text.trim();
    if (content.isEmpty || _isSending) return;

    setState(() => _isSending = true);
    _messageController.clear();

    // 添加用户消息
    final userMsg = _ChatMessage(
      id: 'temp_${DateTime.now().millisecondsSinceEpoch}',
      role: 'user',
      content: content,
      createdAt: DateTime.now(),
    );
    setState(() => _messages.add(userMsg));
    _scrollToBottom();

    // 添加 AI 消息占位
    final aiMsgIndex = _messages.length;
    final aiMsg = _ChatMessage(
      id: 'temp_ai_${DateTime.now().millisecondsSinceEpoch}',
      role: 'assistant',
      content: '',
      createdAt: DateTime.now(),
      isStreaming: true,
    );
    setState(() => _messages.add(aiMsg));
    _scrollToBottom();

    // SSE 流式接收
    try {
      final stream = SSEClient.sendMessage(
        characterId: widget.characterId,
        content: content,
      );

      String fullResponse = '';
      await for (final chunk in stream) {
        if (chunk.startsWith('[错误:')) {
          fullResponse = chunk;
        } else {
          fullResponse += chunk;
        }

        if (mounted) {
          setState(() {
            _messages[aiMsgIndex] = _ChatMessage(
              id: aiMsg.id,
              role: 'assistant',
              content: fullResponse,
              createdAt: aiMsg.createdAt,
              isStreaming: true,
            );
          });
          _scrollToBottom();
        }
      }

      // 流结束
      if (mounted) {
        setState(() {
          _messages[aiMsgIndex] = _ChatMessage(
            id: aiMsg.id,
            role: 'assistant',
            content: fullResponse,
            createdAt: aiMsg.createdAt,
            isStreaming: false,
          );
          _isSending = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _messages[aiMsgIndex] = _ChatMessage(
            id: aiMsg.id,
            role: 'assistant',
            content: '[发送失败: $e]',
            createdAt: aiMsg.createdAt,
            isStreaming: false,
          );
          _isSending = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.backgroundColor,
      appBar: AppBar(
        title: Text(_characterName ?? '聊天'),
        actions: [
          IconButton(
            icon: const Icon(Icons.more_vert),
            onPressed: () => _showMoreOptions(),
          ),
        ],
      ),
      body: Column(
        children: [
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
    );
  }

  Widget _buildMessageList() {
    if (_messages.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.chat_bubble_outline,
              size: 64,
              color: Colors.white.withOpacity(0.3),
            ),
            const SizedBox(height: 16),
            Text(
              '开始和 ${_characterName ?? 'TA'} 聊天吧',
              style: TextStyle(
                color: Colors.white.withOpacity(0.5),
                fontSize: 16,
              ),
            ),
          ],
        ),
      );
    }

    return ListView.builder(
      controller: _scrollController,
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      itemCount: _messages.length,
      itemBuilder: (context, index) {
        final message = _messages[index];
        return _buildMessageBubble(message);
      },
    );
  }

  Widget _buildMessageBubble(_ChatMessage message) {
    final isUser = message.role == 'user';

    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Row(
        mainAxisAlignment: isUser ? MainAxisAlignment.end : MainAxisAlignment.start,
        crossAxisAlignment: CrossAxisAlignment.end,
        children: [
          if (!isUser) _buildAvatar(),
          if (!isUser) const SizedBox(width: 8),
          Flexible(
            child: Container(
              constraints: BoxConstraints(
                maxWidth: MediaQuery.of(context).size.width * 0.75,
              ),
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
              decoration: BoxDecoration(
                color: isUser
                    ? AppTheme.primaryColor
                    : AppTheme.cardColor,
                borderRadius: BorderRadius.only(
                  topLeft: const Radius.circular(18),
                  topRight: const Radius.circular(18),
                  bottomLeft: Radius.circular(isUser ? 18 : 4),
                  bottomRight: Radius.circular(isUser ? 4 : 18),
                ),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    message.content.isEmpty && message.isStreaming
                        ? '...'
                        : message.content,
                    style: TextStyle(
                      color: Colors.white,
                      fontSize: 15,
                      height: 1.4,
                    ),
                  ),
                  if (message.isStreaming)
                    const Padding(
                      padding: EdgeInsets.only(top: 4),
                      child: SizedBox(
                        width: 16,
                        height: 16,
                        child: CircularProgressIndicator(
                          strokeWidth: 2,
                          color: Colors.white54,
                        ),
                      ),
                    ),
                ],
              ),
            ),
          ),
          if (isUser) const SizedBox(width: 8),
        ],
      ),
    );
  }

  Widget _buildAvatar() {
    return Container(
      width: 36,
      height: 36,
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          colors: [AppTheme.primaryColor, AppTheme.accentColor],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(10),
      ),
      child: const Icon(
        Icons.auto_awesome,
        color: Colors.white,
        size: 18,
      ),
    );
  }

  Widget _buildInputBar() {
    return Container(
      padding: EdgeInsets.fromLTRB(
        16,
        12,
        16,
        12 + MediaQuery.of(context).padding.bottom,
      ),
      decoration: BoxDecoration(
        color: AppTheme.surfaceColor,
        border: Border(
          top: BorderSide(
            color: Colors.white.withOpacity(0.1),
            width: 0.5,
          ),
        ),
      ),
      child: Row(
        children: [
          Expanded(
            child: TextField(
              controller: _messageController,
              style: const TextStyle(color: Colors.white),
              decoration: InputDecoration(
                hintText: '输入消息...',
                hintStyle: TextStyle(color: Colors.white.withOpacity(0.4)),
                filled: true,
                fillColor: AppTheme.cardColor,
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(24),
                  borderSide: BorderSide.none,
                ),
                contentPadding: const EdgeInsets.symmetric(
                  horizontal: 20,
                  vertical: 12,
                ),
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
                    ? Colors.grey
                    : AppTheme.primaryColor,
                shape: BoxShape.circle,
              ),
              child: const Icon(
                Icons.send,
                color: Colors.white,
                size: 20,
              ),
            ),
          ),
        ],
      ),
    );
  }

  void _showMoreOptions() {
    showModalBottomSheet(
      context: context,
      backgroundColor: AppTheme.surfaceColor,
      builder: (context) => SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            ListTile(
              leading: const Icon(Icons.psychology, color: Colors.white70),
              title: const Text('查看记忆', style: TextStyle(color: Colors.white)),
              onTap: () {
                Navigator.pop(context);
                // TODO: 跳转到记忆页
              },
            ),
            ListTile(
              leading: const Icon(Icons.delete_outline, color: Colors.redAccent),
              title: const Text('清空对话', style: TextStyle(color: Colors.redAccent)),
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
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: AppTheme.surfaceColor,
        title: const Text('确认清空'),
        content: const Text('清空后无法恢复，确定要清空所有对话吗？'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('取消'),
          ),
          TextButton(
            onPressed: () {
              Navigator.pop(context);
              setState(() => _messages.clear());
            },
            child: const Text('确认', style: TextStyle(color: Colors.redAccent)),
          ),
        ],
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

  _ChatMessage({
    required this.id,
    required this.role,
    required this.content,
    required this.createdAt,
    this.isStreaming = false,
  });
}
