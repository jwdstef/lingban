import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/api/api_client.dart';
import '../../core/theme/app_theme.dart';
import '../auth/providers/auth_provider.dart';

class HomePage extends ConsumerStatefulWidget {
  const HomePage({super.key});

  @override
  ConsumerState<HomePage> createState() => _HomePageState();
}

class _HomePageState extends ConsumerState<HomePage>
    with SingleTickerProviderStateMixin {
  late AnimationController _animController;
  int _currentEmotion = 0;

  // 缓存 API Future，避免每次 rebuild 都重新请求
  late Future<List<Map<String, dynamic>>> _charactersFuture;
  late Future<Map<String, dynamic>> _relationFuture;
  String? _cachedCharacterId;

  static const _emotions = [
    {'name': '平静', 'face': '✦', 'color': AppTheme.emotionCalm},
    {'name': '开心', 'face': '✧', 'color': AppTheme.emotionHappy},
    {'name': '担心', 'face': '◈', 'color': AppTheme.emotionWorried},
    {'name': '兴奋', 'face': '✺', 'color': AppTheme.emotionExcited},
    {'name': '思考', 'face': '◇', 'color': AppTheme.emotionThinking},
  ];

  @override
  void initState() {
    super.initState();
    _animController = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 4),
    )..repeat(reverse: true);
  }

  @override
  void dispose() {
    _animController.dispose();
    super.dispose();
  }

  /// 确保 Future 只在角色变化时重新创建
  void _ensureFutures(String characterId) {
    if (_cachedCharacterId != characterId) {
      _cachedCharacterId = characterId;
      _charactersFuture = _fetchCharacters();
      _relationFuture = _fetchRelation(characterId);
    }
  }

  Future<List<Map<String, dynamic>>> _fetchCharacters() async {
    final response = await apiClient.getCharacters();
    return List<Map<String, dynamic>>.from(response.data);
  }

  Future<Map<String, dynamic>> _fetchRelation(String characterId) async {
    final response = await apiClient.getRelation(characterId);
    return Map<String, dynamic>.from(response.data);
  }

  @override
  Widget build(BuildContext context) {
    final authState = ref.watch(authStateProvider);
    final characterId = authState.selectedCharacterId;

    if (characterId == null) {
      return const Scaffold(
        body: Center(child: Text('未选择角色')),
      );
    }

    // 只在角色变化时重新创建 Future
    _ensureFutures(characterId);

    final emotion = _emotions[_currentEmotion];

    return Stack(
      children: [
        // 背景光斑
        Positioned(
          top: -60,
          right: -40,
          child: Container(
            width: 200,
            height: 200,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              gradient: RadialGradient(
                colors: [
                  AppTheme.spiritGlow.withOpacity(0.08),
                  Colors.transparent,
                ],
                stops: const [0.4, 1.0],
              ),
            ),
          ),
        ),
        Positioned(
          bottom: 100,
          left: -60,
          child: Container(
            width: 160,
            height: 160,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              gradient: RadialGradient(
                colors: [
                  AppTheme.emotionThinking.withOpacity(0.06),
                  Colors.transparent,
                ],
                stops: const [0.4, 1.0],
              ),
            ),
          ),
        ),
        // 内容
        SafeArea(
          child: Column(
            children: [
              // 顶部栏
              _buildTopBar(context, authState),
              // 灵体展示区域
              Expanded(
                child: _buildCharacterDisplay(context, characterId, emotion),
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildTopBar(BuildContext context, AuthState authState) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 8),
      child: Row(
        children: [
          // 设置按钮
          GestureDetector(
            onTap: () => context.push('/settings'),
            child: Icon(
              Icons.settings_outlined,
              color: AppTheme.primaryColor.withOpacity(0.7),
              size: 24,
            ),
          ),
          const Spacer(),
          // 关系等级
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
            decoration: BoxDecoration(
              color: AppTheme.primaryColor.withOpacity(0.1),
              borderRadius: BorderRadius.circular(20),
              border: Border.all(
                color: AppTheme.primaryColor.withOpacity(0.2),
                width: 0.5,
              ),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Icon(Icons.favorite, color: AppTheme.spiritGlow, size: 14),
                const SizedBox(width: 6),
                FutureBuilder<Map<String, dynamic>>(
                  future: _relationFuture,
                  builder: (context, snapshot) {
                    if (snapshot.hasData) {
                      final data = snapshot.data!;
                      return Text(
                        'Lv.${data['level']} ${data['label']}',
                        style: const TextStyle(
                          color: AppTheme.primaryColor,
                          fontSize: 12,
                          fontWeight: FontWeight.w500,
                        ),
                      );
                    }
                    return const Text(
                      'Lv.1 陌生',
                      style: TextStyle(
                        color: AppTheme.primaryColor,
                        fontSize: 12,
                      ),
                    );
                  },
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildCharacterDisplay(
    BuildContext context,
    String characterId,
    Map<String, dynamic> emotion,
  ) {
    return FutureBuilder<List<Map<String, dynamic>>>(
      future: _charactersFuture,
      builder: (context, snapshot) {
        if (!snapshot.hasData) {
          return const Center(child: CircularProgressIndicator());
        }

        final characters = snapshot.data!;
        final character = characters.firstWhere(
          (c) => c['id'] == characterId,
          orElse: () => {},
        );

        if (character.isEmpty) {
          return const Center(child: Text('角色不存在'));
        }

        final name = character['name'] ?? '';
        final emotionColor = emotion['color'] as Color;

        return Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              // 灵体 - 光环 + 粒子 + 核心
              GestureDetector(
                onTap: () {
                  setState(() {
                    _currentEmotion = (_currentEmotion + 1) % _emotions.length;
                  });
                },
                child: SizedBox(
                  width: 200,
                  height: 200,
                  child: AnimatedBuilder(
                    animation: _animController,
                    builder: (context, child) {
                      final scale = 0.95 + _animController.value * 0.05;
                      return Transform.scale(
                        scale: scale,
                        child: Stack(
                          alignment: Alignment.center,
                          children: [
                            // 外圈光环 ring3
                            Container(
                              width: 200,
                              height: 200,
                              decoration: BoxDecoration(
                                shape: BoxShape.circle,
                                border: Border.all(
                                  color: emotionColor.withOpacity(0.1),
                                  width: 1,
                                ),
                              ),
                            ),
                            // 中圈光环 ring2
                            Container(
                              width: 160,
                              height: 160,
                              decoration: BoxDecoration(
                                shape: BoxShape.circle,
                                border: Border.all(
                                  color: emotionColor.withOpacity(0.2),
                                  width: 1.5,
                                ),
                              ),
                            ),
                            // 内圈光环 ring1
                            Container(
                              width: 120,
                              height: 120,
                              decoration: BoxDecoration(
                                shape: BoxShape.circle,
                                border: Border.all(
                                  color: emotionColor.withOpacity(0.3),
                                  width: 2,
                                ),
                              ),
                            ),
                            // 核心光球
                            Container(
                              width: 80,
                              height: 80,
                              decoration: BoxDecoration(
                                shape: BoxShape.circle,
                                gradient: RadialGradient(
                                  colors: [
                                    emotionColor.withOpacity(0.8),
                                    emotionColor.withOpacity(0.3),
                                    emotionColor.withOpacity(0.05),
                                  ],
                                  stops: const [0.3, 0.7, 1.0],
                                ),
                                boxShadow: [
                                  BoxShadow(
                                    color: emotionColor.withOpacity(0.4),
                                    blurRadius: 40,
                                    spreadRadius: 10,
                                  ),
                                ],
                              ),
                              child: Center(
                                child: Text(
                                  emotion['face'] as String,
                                  style: TextStyle(
                                    fontSize: 28,
                                    color: emotionColor,
                                    fontWeight: FontWeight.bold,
                                  ),
                                ),
                              ),
                            ),
                            // 粒子
                            ...List.generate(6, (i) {
                              final angle = (i * 60.0) * math.pi / 180;
                              final radius = 70.0 + _animController.value * 10;
                              return Positioned(
                                left: 100 + math.cos(angle) * radius - 3,
                                top: 100 + math.sin(angle) * radius - 3,
                                child: Container(
                                  width: 6,
                                  height: 6,
                                  decoration: BoxDecoration(
                                    shape: BoxShape.circle,
                                    color: emotionColor.withOpacity(
                                      0.3 + _animController.value * 0.4,
                                    ),
                                  ),
                                ),
                              );
                            }),
                          ],
                        ),
                      );
                    },
                  ),
                ),
              ),

              const SizedBox(height: 32),

              // 角色名
              Text(
                name,
                style: const TextStyle(
                  fontSize: 28,
                  fontWeight: FontWeight.bold,
                  color: AppTheme.primaryColor,
                  letterSpacing: 8,
                ),
              ),

              const SizedBox(height: 12),

              // 情绪状态
              Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Container(
                    width: 8,
                    height: 8,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      color: emotionColor,
                      boxShadow: [
                        BoxShadow(
                          color: emotionColor.withOpacity(0.5),
                          blurRadius: 10,
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(width: 8),
                  Text(
                    emotion['name'] as String,
                    style: TextStyle(
                      fontSize: 14,
                      color: AppTheme.primaryColor.withOpacity(0.8),
                    ),
                  ),
                  const SizedBox(width: 8),
                  Text(
                    '· 点击灵体切换情绪',
                    style: TextStyle(
                      fontSize: 12,
                      color: AppTheme.primaryColor.withOpacity(0.4),
                    ),
                  ),
                ],
              ),

              const SizedBox(height: 32),

              // 银色消息卡 - 主动关怀
              _buildSilverMessageCard(context, characterId),

              const SizedBox(height: 20),

              // 她正在惦记的事
              _buildThinkingOfSection(),

              const SizedBox(height: 24),

              // 呼叫按钮
              _buildCallButton(context, characterId),
            ],
          ),
        );
      },
    );
  }

  Widget _buildSilverMessageCard(BuildContext context, String characterId) {
    return GestureDetector(
      onTap: () => context.push('/chat/$characterId'),
      child: Container(
        margin: const EdgeInsets.symmetric(horizontal: 32),
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          gradient: LinearGradient(
            colors: [
              AppTheme.primaryColor.withOpacity(0.08),
              AppTheme.primaryColor.withOpacity(0.03),
            ],
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
          ),
          borderRadius: BorderRadius.circular(16),
          border: Border.all(
            color: AppTheme.primaryColor.withOpacity(0.15),
            width: 0.5,
          ),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // 头部
            Row(
              children: [
                Text(
                  '✦',
                  style: TextStyle(
                    fontSize: 14,
                    color: AppTheme.spiritGlow,
                  ),
                ),
                const SizedBox(width: 8),
                Text(
                  'TA 刚刚想起你',
                  style: TextStyle(
                    fontSize: 12,
                    color: AppTheme.primaryColor.withOpacity(0.7),
                    fontWeight: FontWeight.w500,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 10),
            // 内容
            Text(
              '你上次说最近睡得晚，今天好点了吗？别硬撑，只是顺手问问。',
              style: TextStyle(
                fontSize: 14,
                color: AppTheme.primaryColor.withOpacity(0.9),
                height: 1.5,
              ),
            ),
            const SizedBox(height: 10),
            // 来源
            Row(
              children: [
                Container(
                  width: 6,
                  height: 6,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: AppTheme.spiritGlow.withOpacity(0.6),
                  ),
                ),
                const SizedBox(width: 6),
                Text(
                  '来自 3 天前的对话 · 作息',
                  style: TextStyle(
                    fontSize: 11,
                    color: AppTheme.primaryColor.withOpacity(0.4),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildThinkingOfSection() {
    final items = ['最近睡得晚', '想吃火锅', '工作压力大', '周末想休息'];

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 32),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // 标题
          Row(
            children: [
              Container(
                width: 6,
                height: 6,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: AppTheme.spiritGlow,
                ),
              ),
              const SizedBox(width: 8),
              Text(
                'TA 正在惦记的事',
                style: TextStyle(
                  fontSize: 13,
                  color: AppTheme.primaryColor.withOpacity(0.6),
                  fontWeight: FontWeight.w500,
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          // 列表
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: items.map((item) {
              return Container(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                decoration: BoxDecoration(
                  color: AppTheme.primaryColor.withOpacity(0.05),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(
                    color: AppTheme.primaryColor.withOpacity(0.1),
                    width: 0.5,
                  ),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Container(
                      width: 4,
                      height: 4,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        color: AppTheme.primaryColor.withOpacity(0.4),
                      ),
                    ),
                    const SizedBox(width: 6),
                    Text(
                      item,
                      style: TextStyle(
                        fontSize: 12,
                        color: AppTheme.primaryColor.withOpacity(0.7),
                      ),
                    ),
                  ],
                ),
              );
            }).toList(),
          ),
        ],
      ),
    );
  }

  Widget _buildCallButton(BuildContext context, String characterId) {
    return GestureDetector(
      onTap: () => context.push('/chat/$characterId'),
      child: Container(
        width: 56,
        height: 56,
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          gradient: LinearGradient(
            colors: [
              AppTheme.primaryColor.withOpacity(0.2),
              AppTheme.primaryColor.withOpacity(0.1),
            ],
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
          ),
          border: Border.all(
            color: AppTheme.primaryColor.withOpacity(0.3),
            width: 1,
          ),
          boxShadow: [
            BoxShadow(
              color: AppTheme.primaryColor.withOpacity(0.15),
              blurRadius: 20,
              spreadRadius: 5,
            ),
          ],
        ),
        child: Icon(
          Icons.chat_bubble_outline,
          color: AppTheme.primaryColor,
          size: 24,
        ),
      ),
    );
  }
}
