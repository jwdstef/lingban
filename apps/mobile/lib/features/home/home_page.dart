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
  late Future<List<Map<String, dynamic>>> _careMessagesFuture;
  late Future<List<Map<String, dynamic>>> _thinkingItemsFuture;
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
      duration: const Duration(seconds: 8),
    )..repeat();
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
      _careMessagesFuture = _fetchLatestCareMessages(characterId);
      _thinkingItemsFuture = _fetchThinkingItems(characterId);
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

  Future<List<Map<String, dynamic>>> _fetchLatestCareMessages(
    String characterId,
  ) async {
    try {
      final response =
          await apiClient.getCareMessages(limit: 1, characterId: characterId);
      final data = Map<String, dynamic>.from(response.data);
      return List<Map<String, dynamic>>.from(data['messages'] ?? []);
    } catch (_) {
      return [];
    }
  }

  String _formatTriggerType(String triggerType) {
    switch (triggerType) {
      case 'time_morning':
        return '早安问候';
      case 'time_night':
        return '晚安问候';
      case 'silence':
        return '久未联系';
      case 'emotion':
        return '情绪关怀';
      default:
        return '主动关怀';
    }
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
        AnimatedBuilder(
          animation: _animController,
          builder: (context, child) {
            final t = _animController.value * math.pi * 2;
            return Stack(
              children: [
                Positioned(
                  top: -60 + math.sin(t) * 16,
                  right: -40 + math.cos(t * 0.8) * 18,
                  child: Transform.scale(
                    scale: 1 + math.sin(t * 0.7) * 0.08,
                    child: _buildBackgroundOrb(
                      size: 210,
                      color: AppTheme.spiritGlow.withValues(alpha: 0.12),
                    ),
                  ),
                ),
                Positioned(
                  top: 190 + math.sin(t * 0.9 + 1.7) * 14,
                  right: -44 + math.cos(t * 0.7 + 0.8) * 16,
                  child: Transform.scale(
                    scale: 1 + math.cos(t * 0.65) * 0.07,
                    child: _buildBackgroundOrb(
                      size: 156,
                      color: AppTheme.accentColor.withValues(alpha: 0.08),
                    ),
                  ),
                ),
                Positioned(
                  bottom: 96 + math.cos(t * 0.75) * 12,
                  left: -62 + math.sin(t * 0.8) * 14,
                  child: _buildBackgroundOrb(
                    size: 165,
                    color: AppTheme.emotionThinking.withValues(alpha: 0.07),
                  ),
                ),
              ],
            );
          },
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
              color: AppTheme.primaryColor.withValues(alpha: 0.7),
              size: 24,
            ),
          ),
          const Spacer(),
          // 关系等级
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
            decoration: BoxDecoration(
              color: AppTheme.primaryColor.withValues(alpha: 0.1),
              borderRadius: BorderRadius.circular(20),
              border: Border.all(
                color: AppTheme.primaryColor.withValues(alpha: 0.2),
                width: 0.5,
              ),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Icon(Icons.favorite,
                    color: AppTheme.spiritGlow, size: 14),
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

  Widget _buildBackgroundOrb({
    required double size,
    required Color color,
  }) {
    return Stack(
      alignment: Alignment.center,
      children: [
        Container(
          width: size,
          height: size,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            color: color.withValues(alpha: 0.07),
          ),
        ),
        Container(
          width: size * 0.72,
          height: size * 0.72,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            color: color.withValues(alpha: 0.08),
          ),
        ),
        Container(
          width: size * 0.42,
          height: size * 0.42,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            color: color.withValues(alpha: 0.09),
          ),
        ),
      ],
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
          child: SingleChildScrollView(
            physics: const NeverScrollableScrollPhysics(),
            padding: const EdgeInsets.only(top: 4, bottom: 8),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                _buildSpiritEntity(
                  emotionColor: emotionColor,
                  face: emotion['face'] as String,
                ),

                const SizedBox(height: 18),

                // 角色名
                Text(
                  name,
                  style: const TextStyle(
                    fontSize: 24,
                    fontWeight: FontWeight.bold,
                    color: AppTheme.primaryColor,
                    letterSpacing: 3,
                  ),
                ),

                const SizedBox(height: 10),

                // 情绪状态
                AnimatedBuilder(
                  animation: _animController,
                  builder: (context, child) {
                    final t = _animController.value * math.pi * 2;
                    final dotScale = 1 + math.sin(t * 4) * 0.18;
                    return Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 14, vertical: 6),
                      decoration: BoxDecoration(
                        color: AppTheme.spiritGlow.withValues(alpha: 0.1),
                        borderRadius: BorderRadius.circular(18),
                        border: Border.all(
                          color: AppTheme.spiritGlow.withValues(alpha: 0.2),
                          width: 0.5,
                        ),
                      ),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Transform.scale(
                            scale: dotScale,
                            child: Container(
                              width: 7,
                              height: 7,
                              decoration: BoxDecoration(
                                shape: BoxShape.circle,
                                color: emotionColor,
                                boxShadow: [
                                  BoxShadow(
                                    color: emotionColor.withValues(alpha: 0.65),
                                    blurRadius: 9,
                                  ),
                                ],
                              ),
                            ),
                          ),
                          const SizedBox(width: 7),
                          Text(
                            emotion['name'] as String,
                            style: TextStyle(
                              fontSize: 12,
                              color: emotionColor.withValues(alpha: 0.95),
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                          const SizedBox(width: 6),
                          Text(
                            '· 点击灵体切换情绪',
                            style: TextStyle(
                              fontSize: 10,
                              color:
                                  AppTheme.textSecondary.withValues(alpha: 0.7),
                            ),
                          ),
                        ],
                      ),
                    );
                  },
                ),

                const SizedBox(height: 20),

                // 银色消息卡 - 主动关怀
                _buildSilverMessageCard(context, characterId, name),

                const SizedBox(height: 12),

                // 她正在惦记的事
                _buildThinkingOfSection(name),

                const SizedBox(height: 14),

                // 呼叫按钮
                _buildCallButton(context, characterId),
              ],
            ),
          ),
        );
      },
    );
  }

  Widget _buildSpiritEntity({
    required Color emotionColor,
    required String face,
  }) {
    return GestureDetector(
      onTap: () {
        setState(() {
          _currentEmotion = (_currentEmotion + 1) % _emotions.length;
        });
      },
      child: SizedBox(
        width: 160,
        height: 160,
        child: AnimatedBuilder(
          animation: _animController,
          builder: (context, child) {
            final t = _animController.value * math.pi * 2;
            final pulse = 1 + math.sin(t * 2) * 0.035;
            final faceOffset = math.sin(t * 2.6) * 4;

            return Stack(
              alignment: Alignment.center,
              children: [
                _buildFloatingParticle(
                  t: t,
                  baseX: 22,
                  baseY: 16,
                  color: emotionColor,
                  phase: 0,
                ),
                _buildFloatingParticle(
                  t: t,
                  baseX: 128,
                  baseY: 28,
                  color: AppTheme.accentColor,
                  phase: 1.1,
                ),
                _buildFloatingParticle(
                  t: t,
                  baseX: 28,
                  baseY: 124,
                  color: emotionColor,
                  phase: 0.6,
                ),
                _buildFloatingParticle(
                  t: t,
                  baseX: 136,
                  baseY: 118,
                  color: AppTheme.emotionThinking,
                  phase: 1.8,
                  size: 2.4,
                ),
                _buildFloatingParticle(
                  t: t,
                  baseX: 12,
                  baseY: 68,
                  color: AppTheme.accentColor,
                  phase: 2.4,
                  size: 2.4,
                ),
                _buildFloatingParticle(
                  t: t,
                  baseX: 122,
                  baseY: 12,
                  color: AppTheme.spiritGlow,
                  phase: 2.9,
                  size: 2.2,
                ),
                Transform.rotate(
                  angle: t * 0.32,
                  child: _buildSpiritRing(
                    size: 145,
                    color: emotionColor.withValues(alpha: 0.18),
                    markerColor: AppTheme.spiritGlow,
                  ),
                ),
                Transform.rotate(
                  angle: -t * 0.46,
                  child: _buildSpiritRing(
                    size: 125,
                    color: AppTheme.accentColor.withValues(alpha: 0.13),
                    markerColor: AppTheme.accentColor,
                  ),
                ),
                Transform.rotate(
                  angle: t * 0.24,
                  child: CustomPaint(
                    size: const Size.square(110),
                    painter: _DashedRingPainter(
                      color: emotionColor.withValues(alpha: 0.16),
                    ),
                  ),
                ),
                Transform.scale(
                  scale: pulse,
                  child: Stack(
                    alignment: Alignment.center,
                    children: [
                      _buildOrbGlow(emotionColor, 144, 0.24),
                      _buildOrbGlow(emotionColor, 108, 0.28),
                      Container(
                        width: 82,
                        height: 82,
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          gradient: RadialGradient(
                            center: const Alignment(-0.38, -0.38),
                            colors: [
                              emotionColor.withValues(alpha: 0.96),
                              emotionColor.withValues(alpha: 0.78),
                              emotionColor.withValues(alpha: 0.54),
                            ],
                            stops: const [0.0, 0.58, 1.0],
                          ),
                        ),
                        child: Transform.translate(
                          offset: Offset(0, faceOffset),
                          child: Center(
                            child: Text(
                              face,
                              style: TextStyle(
                                fontSize: 31,
                                color: Colors.white.withValues(alpha: 0.92),
                                fontWeight: FontWeight.w700,
                                shadows: [
                                  Shadow(
                                    color: Colors.white.withValues(alpha: 0.55),
                                    blurRadius: 10,
                                  ),
                                ],
                              ),
                            ),
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            );
          },
        ),
      ),
    );
  }

  Widget _buildSpiritRing({
    required double size,
    required Color color,
    required Color markerColor,
  }) {
    return SizedBox(
      width: size,
      height: size,
      child: Stack(
        alignment: Alignment.topCenter,
        children: [
          Container(
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              border: Border.all(color: color, width: 1),
            ),
          ),
          Transform.translate(
            offset: const Offset(0, -2),
            child: Container(
              width: 5,
              height: 5,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: markerColor,
                boxShadow: [
                  BoxShadow(
                    color: markerColor.withValues(alpha: 0.55),
                    blurRadius: 10,
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildOrbGlow(Color color, double size, double alpha) {
    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        color: color.withValues(alpha: alpha * 0.32),
      ),
    );
  }

  Widget _buildFloatingParticle({
    required double t,
    required double baseX,
    required double baseY,
    required Color color,
    required double phase,
    double size = 3,
  }) {
    final x = baseX + math.sin(t * 1.4 + phase) * 12;
    final y = baseY + math.cos(t * 1.1 + phase) * 18;
    final opacity = 0.35 + (math.sin(t * 1.8 + phase) + 1) * 0.28;

    return Positioned(
      left: x,
      top: y,
      child: Container(
        width: size,
        height: size,
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          color: color.withValues(alpha: opacity),
          boxShadow: [
            BoxShadow(
              color: color.withValues(alpha: opacity * 0.8),
              blurRadius: 7,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildSilverMessageCard(
    BuildContext context,
    String characterId,
    String characterName,
  ) {
    return FutureBuilder<List<Map<String, dynamic>>>(
      future: _careMessagesFuture,
      builder: (context, snapshot) {
        final latest =
            (snapshot.data?.isNotEmpty ?? false) ? snapshot.data!.first : null;
        final latestContent = latest?['content'] as String?;
        final latestTrigger = latest?['trigger_type'] as String?;

        return GestureDetector(
          onTap: () async {
            final messageId = latest?['id'] as String?;
            if (messageId != null) {
              try {
                await apiClient.markCareMessageClicked(messageId);
              } catch (_) {
                // Opening chat should not depend on analytics/writeback success.
              }
            }
            if (context.mounted) {
              final uri = Uri(
                path: '/chat/$characterId',
                queryParameters: {
                  if (messageId != null) 'careMessageId': messageId,
                },
              );
              context.push(uri.toString());
            }
          },
          child: Container(
            margin: const EdgeInsets.symmetric(horizontal: 32),
            padding: const EdgeInsets.fromLTRB(16, 12, 16, 12),
            decoration: BoxDecoration(
              gradient: LinearGradient(
                colors: [
                  AppTheme.primaryColor.withValues(alpha: 0.08),
                  AppTheme.primaryColor.withValues(alpha: 0.03),
                ],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              ),
              borderRadius: BorderRadius.circular(14),
              border: Border.all(
                color: AppTheme.primaryColor.withValues(alpha: 0.15),
                width: 0.5,
              ),
              boxShadow: [
                BoxShadow(
                  color: AppTheme.spiritGlow.withValues(alpha: 0.1),
                  blurRadius: 20,
                  offset: const Offset(0, 8),
                ),
              ],
            ),
            child: Stack(
              clipBehavior: Clip.none,
              children: [
                Positioned(
                  top: -16,
                  left: -16,
                  right: -16,
                  child: Container(
                    height: 2,
                    decoration: BoxDecoration(
                      gradient: LinearGradient(
                        colors: [
                          AppTheme.spiritGlow.withValues(alpha: 0.75),
                          AppTheme.accentColor.withValues(alpha: 0.65),
                          AppTheme.emotionThinking.withValues(alpha: 0.62),
                        ],
                      ),
                    ),
                  ),
                ),
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // 头部
                    Row(
                      children: [
                        const Text(
                          '✦',
                          style: TextStyle(
                            fontSize: 14,
                            color: AppTheme.spiritGlow,
                          ),
                        ),
                        const SizedBox(width: 8),
                        Text(
                          '$characterName刚刚想起你',
                          style: TextStyle(
                            fontSize: 12,
                            color: AppTheme.primaryColor.withValues(alpha: 0.7),
                            fontWeight: FontWeight.w500,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    // 内容
                    Text(
                      latestContent ?? '和我说说今天发生了什么？',
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(
                        fontSize: 13,
                        color: AppTheme.primaryColor.withValues(alpha: 0.9),
                        height: 1.45,
                      ),
                    ),
                    const SizedBox(height: 8),
                    // 来源
                    Row(
                      children: [
                        Container(
                          width: 6,
                          height: 6,
                          decoration: BoxDecoration(
                            shape: BoxShape.circle,
                            color: AppTheme.spiritGlow.withValues(alpha: 0.6),
                          ),
                        ),
                        const SizedBox(width: 6),
                        Text(
                          latestTrigger != null
                              ? '来自主动关怀 · ${_formatTriggerType(latestTrigger)}'
                              : '来自最近的对话',
                          style: TextStyle(
                            fontSize: 11,
                            color: AppTheme.primaryColor.withValues(alpha: 0.4),
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  Widget _buildThinkingOfSection(String characterName) {
    final title = characterName == '银月' ? '她正在惦记的事' : '$characterName 正在惦记的事';

    return FutureBuilder<List<Map<String, dynamic>>>(
      future: _thinkingItemsFuture,
      builder: (context, snapshot) {
        if (!snapshot.hasData || snapshot.data!.isEmpty) {
          return const SizedBox.shrink();
        }

        final items = snapshot.data!;

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
                    decoration: const BoxDecoration(
                      shape: BoxShape.circle,
                      color: AppTheme.spiritGlow,
                    ),
                  ),
                  const SizedBox(width: 8),
                  Text(
                    title,
                    style: TextStyle(
                      fontSize: 11,
                      color: AppTheme.primaryColor.withValues(alpha: 0.6),
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 8),
              // 列表
              Wrap(
                spacing: 6,
                runSpacing: 6,
                children: items.map((item) {
                  return Container(
                    padding:
                        const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                    decoration: BoxDecoration(
                      color: AppTheme.primaryColor.withValues(alpha: 0.05),
                      borderRadius: BorderRadius.circular(16),
                      border: Border.all(
                        color: AppTheme.primaryColor.withValues(alpha: 0.1),
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
                            color: AppTheme.primaryColor.withValues(alpha: 0.4),
                          ),
                        ),
                        const SizedBox(width: 6),
                        ConstrainedBox(
                          constraints: const BoxConstraints(maxWidth: 250),
                          child: Text(
                            _compactThinkingText(item['content'] ?? ''),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: TextStyle(
                              fontSize: 11,
                              color:
                                  AppTheme.primaryColor.withValues(alpha: 0.7),
                            ),
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
      },
    );
  }

  Future<List<Map<String, dynamic>>> _fetchThinkingItems(
    String characterId,
  ) async {
    // 从记忆系统中获取真实的惦记事项
    try {
      final response = await apiClient.getMemories(characterId);
      final data = response.data;
      final memories = List<Map<String, dynamic>>.from(data['memories'] ?? []);

      // 取最近的重要记忆作为惦记事项（最多4条）
      return memories
          .where((m) => (m['importance'] ?? 0) >= 5)
          .take(4)
          .map((m) => {'content': m['content'] ?? ''})
          .toList();
    } catch (_) {
      return [];
    }
  }

  String _compactThinkingText(String content) {
    final text = content.trim();
    if (text.length <= 22) return text;
    return '${text.substring(0, 22)}...';
  }

  Widget _buildCallButton(BuildContext context, String characterId) {
    return GestureDetector(
      onTap: () => context.push('/chat/$characterId'),
      child: AnimatedBuilder(
        animation: _animController,
        builder: (context, child) {
          final t = _animController.value * math.pi * 2;
          final pulse = (math.sin(t * 2) + 1) / 2;
          return SizedBox(
            width: 72,
            height: 72,
            child: Stack(
              alignment: Alignment.center,
              children: [
                Transform.scale(
                  scale: 1 + pulse * 0.28,
                  child: Container(
                    width: 60,
                    height: 60,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(
                        colors: [
                          AppTheme.spiritGlow.withValues(
                            alpha: 0.22 * (1 - pulse),
                          ),
                          AppTheme.accentColor.withValues(
                            alpha: 0.16 * (1 - pulse),
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
                Container(
                  width: 60,
                  height: 60,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    gradient: const LinearGradient(
                      colors: [Color(0xFF7C5CFF), Color(0xFFF472B6)],
                      begin: Alignment.topLeft,
                      end: Alignment.bottomRight,
                    ),
                    boxShadow: [
                      BoxShadow(
                        color: AppTheme.spiritGlow.withValues(alpha: 0.4),
                        blurRadius: 30,
                      ),
                      BoxShadow(
                        color: AppTheme.spiritGlow.withValues(alpha: 0.16),
                        blurRadius: 60,
                        spreadRadius: 8,
                      ),
                    ],
                  ),
                  child: const Icon(
                    Icons.chat_bubble_outline,
                    color: Colors.white,
                    size: 25,
                  ),
                ),
              ],
            ),
          );
        },
      ),
    );
  }
}

class _DashedRingPainter extends CustomPainter {
  final Color color;

  const _DashedRingPainter({required this.color});

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final radius = size.width / 2;
    final paint = Paint()
      ..color = color
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.1
      ..strokeCap = StrokeCap.round;

    const dashCount = 28;
    const visibleFraction = 0.45;
    for (var i = 0; i < dashCount; i++) {
      final start = (math.pi * 2 / dashCount) * i;
      const sweep = (math.pi * 2 / dashCount) * visibleFraction;
      canvas.drawArc(
        Rect.fromCircle(center: center, radius: radius),
        start,
        sweep,
        false,
        paint,
      );
    }
  }

  @override
  bool shouldRepaint(covariant _DashedRingPainter oldDelegate) {
    return oldDelegate.color != color;
  }
}
