import 'package:equatable/equatable.dart';

/// 聊天消息模型
class ChatMessage extends Equatable {
  final String id;
  final String content;
  final MessageType type;
  final bool isUser;
  final String characterId;
  final DateTime createdAt;
  final MessageStatus status;

  const ChatMessage({
    required this.id,
    required this.content,
    this.type = MessageType.text,
    required this.isUser,
    required this.characterId,
    required this.createdAt,
    this.status = MessageStatus.sent,
  });

  factory ChatMessage.fromJson(Map<String, dynamic> json) {
    return ChatMessage(
      id: json['id'] as String,
      content: json['content'] as String,
      type: MessageType.values.firstWhere(
        (e) => e.name == json['type'],
        orElse: () => MessageType.text,
      ),
      isUser: json['is_user'] as bool,
      characterId: json['character_id'] as String,
      createdAt: DateTime.parse(json['created_at'] as String),
      status: MessageStatus.values.firstWhere(
        (e) => e.name == json['status'],
        orElse: () => MessageStatus.sent,
      ),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'content': content,
      'type': type.name,
      'is_user': isUser,
      'character_id': characterId,
      'created_at': createdAt.toIso8601String(),
      'status': status.name,
    };
  }

  ChatMessage copyWith({
    String? content,
    MessageStatus? status,
  }) {
    return ChatMessage(
      id: id,
      content: content ?? this.content,
      type: type,
      isUser: isUser,
      characterId: characterId,
      createdAt: createdAt,
      status: status ?? this.status,
    );
  }

  @override
  List<Object?> get props => [id, content, type, isUser, characterId];
}

enum MessageType {
  text,
  voice,
  image,
  emoji,
  system,
}

enum MessageStatus {
  sending,
  sent,
  delivered,
  error,
}
