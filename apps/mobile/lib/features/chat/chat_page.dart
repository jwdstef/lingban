import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/api/api_client.dart';
import '../../core/api/sse_client.dart';
import '../../core/theme/app_theme.dart';
import '../auth/providers/auth_provider.dart';

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
      if (mounted) setState(() => _characterName = char['name'] ?? '灵伴');
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
      if (mounted) setState(() => _isLoading = false);
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

    _messages.add(_ChatMessage(
      id: 'temp_${DateTime.now().millisecondsSinceEpoch}',
      role: 'user',
      content: content,
      createdAt: DateTime.now(),
    ));
    _scrollToBottom();

    final aiMsgIndex = _messages.length;
    _messages.add(_ChatMessage(
      id: 'temp_ai_${DateTime.now().millisecondsSinceEpoch}',
      role: 'assistant',
      content: '',
      createdAt: DateTime.now(),
      isStreaming: true,
    ));
    _scrollToBottom();

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
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      child: Row(
        children: [
          GestureDetector(
            onTap: () => context.pop(),
            child: Icon(Icons.arrow_back_ios, color: AppTheme.primaryColor.withOpacity(0.7), size: 20),
          ),
          const SizedBox(width: 8),
          // 角色头像
          Container(
            width: 32,
            height: 32,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              gradient: RadialGradient(
                colors: [
                  AppTheme.spiritGlow.withOpacity(0.4),
                  AppTheme.spiritGlow.withOpacity(0.1),
                ],
              ),
            ),
            child: const Icon(Icons.auto_awesome, color: AppTheme.spiritGlow, size: 16),
          ),
          const SizedBox(width: 10),
          Text(
            _characterName ?? '聊天',
            style: const TextStyle(
              color: AppTheme.primaryColor,
              fontSize: 16,
              fontWeight: FontWeight.w600,
            ),
          ),
          const Spacer(),
          GestureDetector(
            onTap: _showMoreOptions,
            child: Icon(Icons.more_horiz, color: AppTheme.primaryColor.withOpacity(0.5)),
          ),
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
            Icon(Icons.chat_bubble_outline, size: 48, color: AppTheme.primaryColor.withOpacity(0.2)),
            const SizedBox(height: 16),
            Text(
              '开始和 ${_characterName ?? 'TA'} 聊天吧',
              style: TextStyle(color: AppTheme.primaryColor.withOpacity(0.4), fontSize: 14),
            ),
          ],
        ),
      );
    }

    return ListView.builder(
      controller: _scrollController,
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      itemCount: _messages.length,
      itemBuilder: (context, index) => _buildMessageBubble(_messages[index]),
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
          if (!isUser) ...[
            Container(
              width: 32,
              height: 32,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                gradient: RadialGradient(
                  colors: [
                    AppTheme.spiritGlow.withOpacity(0.3),
                    AppTheme.spiritGlow.withOpacity(0.05),
                  ],
                ),
              ),
              child: const Icon(Icons.auto_awesome, color: AppTheme.spiritGlow, size: 14),
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
                color: isUser
                    ? AppTheme.primaryColor.withOpacity(0.15)
                    : AppTheme.cardColor,
                borderRadius: BorderRadius.only(
                  topLeft: const Radius.circular(18),
                  topRight: const Radius.circular(18),
                  bottomLeft: Radius.circular(isUser ? 18 : 4),
                  bottomRight: Radius.circular(isUser ? 4 : 18),
                ),
                border: Border.all(
                  color: isUser
                      ? AppTheme.primaryColor.withOpacity(0.2)
                      : AppTheme.primaryColor.withOpacity(0.08),
                  width: 0.5,
                ),
              ),
              child: Text(
                message.content.isEmpty && message.isStreaming
                    ? '...'
                    : message.content,
                style: TextStyle(
                  color: AppTheme.primaryColor.withOpacity(isUser ? 0.9 : 0.85),
                  fontSize: 15,
                  height: 1.5,
                ),
              ),
            ),
          ),
          if (isUser) const SizedBox(width: 8),
        ],
      ),
    );
  }

  Widget _buildInputBar() {
    return Container(
      padding: EdgeInsets.fromLTRB(16, 12, 16, 12),
      decoration: BoxDecoration(
        color: AppTheme.surfaceColor.withOpacity(0.95),
        border: Border(
          top: BorderSide(
            color: AppTheme.primaryColor.withOpacity(0.1),
            width: 0.5,
          ),
        ),
      ),
      child: Row(
        children: [
          Expanded(
            child: TextField(
              controller: _messageController,
              style: const TextStyle(color: AppTheme.primaryColor),
              decoration: InputDecoration(
                hintText: '输入消息...',
                hintStyle: TextStyle(color: AppTheme.primaryColor.withOpacity(0.3)),
                filled: true,
                fillColor: AppTheme.cardColor,
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(24),
                  borderSide: BorderSide.none,
                ),
                contentPadding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
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
                    ? AppTheme.primaryColor.withOpacity(0.2)
                    : AppTheme.spiritGlow.withOpacity(0.3),
                shape: BoxShape.circle,
                border: Border.all(
                  color: _isSending
                      ? AppTheme.primaryColor.withOpacity(0.1)
                      : AppTheme.spiritGlow.withOpacity(0.5),
                  width: 1,
                ),
              ),
              child: Icon(
                Icons.send,
                color: _isSending
                    ? AppTheme.primaryColor.withOpacity(0.3)
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
    final characterId = ref.read(authStateProvider).selectedCharacterId ?? widget.characterId;
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
              leading: Icon(Icons.psychology, color: AppTheme.primaryColor.withOpacity(0.7)),
              title: Text('查看记忆', style: TextStyle(color: AppTheme.primaryColor)),
              onTap: () {
                Navigator.pop(context);
                context.push('/memory/$characterId');
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
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        title: const Text('确认清空'),
        content: const Text('清空后无法恢复，确定要清空所有对话吗？'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: Text('取消', style: TextStyle(color: AppTheme.primaryColor.withOpacity(0.5))),
          ),
          TextButton(
            onPressed: () async {
              Navigator.pop(context);
              try {
                await apiClient.clearChatHistory(widget.characterId);
                if (mounted) setState(() => _messages.clear());
              } catch (e) {
                if (mounted) {
                  ScaffoldMessenger.of(context).showSnackBar(
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
