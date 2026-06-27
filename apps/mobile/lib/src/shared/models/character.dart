import 'package:equatable/equatable.dart';

/// 角色模型
class Character extends Equatable {
  final String id;
  final String name;
  final String source;
  final String description;
  final String avatarUrl;
  final int color;
  final CharacterPersonality personality;
  final RelationshipLevel relationship;

  const Character({
    required this.id,
    required this.name,
    required this.source,
    required this.description,
    required this.avatarUrl,
    required this.color,
    required this.personality,
    required this.relationship,
  });

  factory Character.fromJson(Map<String, dynamic> json) {
    return Character(
      id: json['id'] as String,
      name: json['name'] as String,
      source: json['source'] as String,
      description: json['description'] as String,
      avatarUrl: json['avatar_url'] as String? ?? '',
      color: json['color'] as int? ?? 0xFF8B5CF6,
      personality: CharacterPersonality.fromJson(
        json['personality'] as Map<String, dynamic>? ?? {},
      ),
      relationship: RelationshipLevel.fromJson(
        json['relationship'] as Map<String, dynamic>? ?? {},
      ),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'name': name,
      'source': source,
      'description': description,
      'avatar_url': avatarUrl,
      'color': color,
      'personality': personality.toJson(),
      'relationship': relationship.toJson(),
    };
  }

  @override
  List<Object?> get props => [id, name, source];
}

/// 角色人格参数
class CharacterPersonality extends Equatable {
  final int tsundere; // 傲娇度 0-100
  final int sharpTongued; // 毒舌度
  final int gentle; // 温柔度
  final int active; // 活跃度
  final int mature; // 成熟度
  final String selfReference; // 自称
  final String userReference; // 称呼用户
  final List<String> catchphrases; // 口癖

  const CharacterPersonality({
    this.tsundere = 0,
    this.sharpTongued = 0,
    this.gentle = 0,
    this.active = 0,
    this.mature = 0,
    this.selfReference = '',
    this.userReference = '',
    this.catchphrases = const [],
  });

  factory CharacterPersonality.fromJson(Map<String, dynamic> json) {
    return CharacterPersonality(
      tsundere: json['tsundere'] as int? ?? 0,
      sharpTongued: json['sharp_tongued'] as int? ?? 0,
      gentle: json['gentle'] as int? ?? 0,
      active: json['active'] as int? ?? 0,
      mature: json['mature'] as int? ?? 0,
      selfReference: json['self_reference'] as String? ?? '',
      userReference: json['user_reference'] as String? ?? '',
      catchphrases: (json['catchphrases'] as List<dynamic>?)
              ?.cast<String>() ??
          [],
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'tsundere': tsundere,
      'sharp_tongued': sharpTongued,
      'gentle': gentle,
      'active': active,
      'mature': mature,
      'self_reference': selfReference,
      'user_reference': userReference,
      'catchphrases': catchphrases,
    };
  }

  @override
  List<Object?> get props => [
        tsundere,
        sharpTongued,
        gentle,
        active,
        mature,
        selfReference,
        userReference,
      ];
}

/// 关系等级
class RelationshipLevel extends Equatable {
  final int level;
  final String label;
  final int intimacy; // 亲密度 0-1000

  const RelationshipLevel({
    this.level = 1,
    this.label = '陌生',
    this.intimacy = 0,
  });

  factory RelationshipLevel.fromJson(Map<String, dynamic> json) {
    return RelationshipLevel(
      level: json['level'] as int? ?? 1,
      label: json['label'] as String? ?? '陌生',
      intimacy: json['intimacy'] as int? ?? 0,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'level': level,
      'label': label,
      'intimacy': intimacy,
    };
  }

  @override
  List<Object?> get props => [level, label, intimacy];
}
