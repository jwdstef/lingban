class AppConstants {
  AppConstants._();

  // API
  static const String baseUrl = 'http://localhost:8000';
  static const String apiPrefix = '/api/v1';
  static const String wsUrl = 'ws://localhost:8000/ws';

  // Characters
  static const List<CharacterPreset> characters = [
    CharacterPreset(
      id: 'yinyue',
      name: '银月',
      source: '凡人修仙传',
      description: '傲娇毒舌，外冷内热的修仙伙伴',
      tags: ['傲娇', '毒舌', '外冷内热'],
      color: 0xFFC0C0C0, // 银色
    ),
    CharacterPreset(
      id: 'babata',
      name: '巴巴塔',
      source: '吞噬星空',
      description: '沉稳睿智，亦师亦友的宇宙向导',
      tags: ['沉稳', '睿智', '亦师亦友'],
      color: 0xFF4169E1, // 皇家蓝
    ),
    CharacterPreset(
      id: 'heihaung',
      name: '黑皇',
      source: '遮天',
      description: '贱萌搞笑，仗义直率的欢乐担当',
      tags: ['贱萌', '搞笑', '仗义'],
      color: 0xFF2F2F2F, // 黑色
    ),
  ];
}

class CharacterPreset {
  final String id;
  final String name;
  final String source;
  final String description;
  final List<String> tags;
  final int color;

  const CharacterPreset({
    required this.id,
    required this.name,
    required this.source,
    required this.description,
    required this.tags,
    required this.color,
  });
}
