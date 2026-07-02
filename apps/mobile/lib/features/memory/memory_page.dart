import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/api/api_client.dart';
import '../../core/theme/app_theme.dart';

class MemoryPage extends ConsumerStatefulWidget {
  final String characterId;
  const MemoryPage({super.key, required this.characterId});

  @override
  ConsumerState<MemoryPage> createState() => _MemoryPageState();
}

class _MemoryPageState extends ConsumerState<MemoryPage> {
  List<Map<String, dynamic>> _memories = [];
  List<Map<String, dynamic>> _categories = [];
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadMemories();
  }

  Future<void> _loadMemories() async {
    setState(() => _isLoading = true);
    try {
      final response = await apiClient.getMemories(widget.characterId);
      final data = response.data;
      if (mounted) {
        setState(() {
          _memories = List<Map<String, dynamic>>.from(data['memories'] ?? []);
          _categories = List<Map<String, dynamic>>.from(data['categories'] ?? []);
          _isLoading = false;
        });
      }
    } catch (e) {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.transparent,
      body: SafeArea(
        child: Column(
          children: [
            // 顶栏
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
              child: Row(
                children: [
                  GestureDetector(
                    onTap: () => context.pop(),
                    child: Icon(Icons.arrow_back_ios,
                        color: AppTheme.primaryColor.withValues(alpha: 0.7),
                        size: 20),
                  ),
                  const SizedBox(width: 8),
                  Text(
                    '本姑娘都记着呢',
                    style: TextStyle(
                      color: AppTheme.primaryColor.withValues(alpha: 0.8),
                      fontSize: 18,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ],
              ),
            ),
            // 内容
            Expanded(
              child: _isLoading
                  ? const Center(child: CircularProgressIndicator())
                  : ListView(
                      padding: const EdgeInsets.symmetric(horizontal: 16),
                      children: [
                        const SizedBox(height: 8),
                        // 1. 统计卡
                        _buildStatsCard(),
                        const SizedBox(height: 20),
                        // 2. 记忆时间轴
                        _buildTimelineSection(),
                        const SizedBox(height: 20),
                        // 3. 记忆分类网格
                        _buildMemoryGrid(),
                        const SizedBox(height: 60),
                      ],
                    ),
            ),
          ],
        ),
      ),
    );
  }

  // 统计卡
  Widget _buildStatsCard() {
    final totalMemories = _memories.length;

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [
            AppTheme.cardColor,
            AppTheme.cardColor.withValues(alpha: 0.8),
          ],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: AppTheme.primaryColor.withValues(alpha: 0.1),
          width: 0.5,
        ),
      ),
      child: Column(
        children: [
          // 头部
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                '共同经历',
                style: TextStyle(
                  color: AppTheme.primaryColor.withValues(alpha: 0.8),
                  fontSize: 14,
                  fontWeight: FontWeight.w600,
                ),
              ),
              Text(
                '$totalMemories 件',
                style: TextStyle(
                  color: AppTheme.spiritGlow,
                  fontSize: 14,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          // 统计网格
          Row(
            children: [
              _buildStatItem('47', '相处天数'),
              _buildStatItem('${_countByCategory('emotion')}', '斗嘴次数'),
              _buildStatItem('${_countByCategory('daily')}', '深夜陪伴'),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildStatItem(String value, String label) {
    return Expanded(
      child: Column(
        children: [
          Text(
            value,
            style: const TextStyle(
              color: AppTheme.primaryColor,
              fontSize: 24,
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            label,
            style: TextStyle(
              color: AppTheme.primaryColor.withValues(alpha: 0.4),
              fontSize: 11,
            ),
          ),
        ],
      ),
    );
  }

  int _countByCategory(String category) {
    try {
      final cat = _categories.firstWhere((c) => c['category'] == category,
          orElse: () => {'count': 0});
      return cat['count'] ?? 0;
    } catch (_) {
      return 0;
    }
  }

  // 记忆时间轴
  Widget _buildTimelineSection() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(
              '记忆时间轴',
              style: TextStyle(
                color: AppTheme.primaryColor.withValues(alpha: 0.8),
                fontSize: 14,
                fontWeight: FontWeight.w600,
              ),
            ),
            Text(
              '全部 ›',
              style: TextStyle(
                color: AppTheme.primaryColor.withValues(alpha: 0.4),
                fontSize: 12,
              ),
            ),
          ],
        ),
        const SizedBox(height: 12),
        if (_memories.isEmpty)
          Container(
            padding: const EdgeInsets.all(24),
            child: Center(
              child: Column(
                children: [
                  Icon(Icons.psychology,
                      size: 36,
                      color: AppTheme.primaryColor.withValues(alpha: 0.2)),
                  const SizedBox(height: 8),
                  Text(
                    '还没有记忆，多聊聊吧',
                    style: TextStyle(
                      color: AppTheme.primaryColor.withValues(alpha: 0.3),
                      fontSize: 13,
                    ),
                  ),
                ],
              ),
            ),
          )
        else
          ..._memories.take(5).toList().asMap().entries.map((entry) => _buildTimelineItem(entry.key, entry.value)),
      ],
    );
  }

  // 时间轴圆点颜色
  static const _dotColors = [
    Color(0xFF8B5CF6), // 紫色
    Color(0xFFEC4899), // 粉色
    Color(0xFF06B6D4), // 青色
    Color(0xFFF59E0B), // 黄色
    Color(0xFF10B981), // 绿色
  ];

  Widget _buildTimelineItem(int index, Map<String, dynamic> memory) {
    final emotionTags = List<String>.from(memory['emotion_tags'] ?? []);
    final tag = emotionTags.isNotEmpty ? emotionTags.first : '';
    final date = memory['created_at'] ?? '';
    final dateStr = _formatDate(date);
    final dotColor = _dotColors[index % _dotColors.length];
    final totalItems = _memories.length > 5 ? 5 : _memories.length;
    final isLast = index == totalItems - 1;

    return Padding(
      padding: const EdgeInsets.only(bottom: 16),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // 时间轴线
          Column(
            children: [
              Container(
                width: 10,
                height: 10,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: dotColor,
                  boxShadow: [
                    BoxShadow(
                      color: dotColor.withValues(alpha: 0.4),
                      blurRadius: 8,
                    ),
                  ],
                ),
              ),
              if (!isLast)
                Container(
                  width: 1,
                  height: 50,
                  decoration: BoxDecoration(
                    gradient: LinearGradient(
                      begin: Alignment.topCenter,
                      end: Alignment.bottomCenter,
                      colors: [
                        dotColor.withValues(alpha: 0.3),
                        dotColor.withValues(alpha: 0.05),
                      ],
                    ),
                  ),
                ),
            ],
          ),
          const SizedBox(width: 12),
          // 内容
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  dateStr,
                  style: TextStyle(
                    color: AppTheme.primaryColor.withValues(alpha: 0.4),
                    fontSize: 11,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  memory['content'] ?? '',
                  style: TextStyle(
                    color: AppTheme.primaryColor.withValues(alpha: 0.85),
                    fontSize: 13,
                    height: 1.4,
                  ),
                ),
                if (tag.isNotEmpty) ...[
                  const SizedBox(height: 6),
                  Container(
                    padding:
                        const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                    decoration: BoxDecoration(
                      color: AppTheme.primaryColor.withValues(alpha: 0.05),
                      borderRadius: BorderRadius.circular(10),
                      border: Border.all(
                        color: AppTheme.primaryColor.withValues(alpha: 0.1),
                        width: 0.5,
                      ),
                    ),
                    child: Text(
                      tag,
                      style: TextStyle(
                        color: AppTheme.primaryColor.withValues(alpha: 0.5),
                        fontSize: 10,
                      ),
                    ),
                  ),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }

  // 记忆分类网格
  Widget _buildMemoryGrid() {
    final gridItems = [
      {'icon': '🌙', 'title': '深夜emo', 'desc': '失眠、焦虑、突然难过...', 'category': 'emotion'},
      {'icon': '😤', 'title': '职场生存', 'desc': '加班、甩锅、想辞职...', 'category': 'daily'},
      {'icon': '🏠', 'title': '一个人的日子', 'desc': '搬家、生病、一个人过节...', 'category': 'fact'},
      {'icon': '✨', 'title': '小确幸', 'desc': '做饭成功、涨薪、遇到好人...', 'category': 'event'},
    ];

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          '记忆分类',
          style: TextStyle(
            color: AppTheme.primaryColor.withValues(alpha: 0.8),
            fontSize: 14,
            fontWeight: FontWeight.w600,
          ),
        ),
        const SizedBox(height: 12),
        GridView.builder(
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
            crossAxisCount: 2,
            childAspectRatio: 1.6,
            crossAxisSpacing: 10,
            mainAxisSpacing: 10,
          ),
          itemCount: gridItems.length,
          itemBuilder: (context, index) {
            final item = gridItems[index];
            final count = _countByCategory(item['category']!);
            return Container(
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: AppTheme.cardColor,
                borderRadius: BorderRadius.circular(14),
                border: Border.all(
                  color: AppTheme.primaryColor.withValues(alpha: 0.08),
                  width: 0.5,
                ),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(item['icon']!, style: const TextStyle(fontSize: 20)),
                  const SizedBox(height: 6),
                  Text(
                    item['title']!,
                    style: TextStyle(
                      color: AppTheme.primaryColor.withValues(alpha: 0.9),
                      fontSize: 13,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    item['desc']!,
                    style: TextStyle(
                      color: AppTheme.primaryColor.withValues(alpha: 0.4),
                      fontSize: 10,
                    ),
                  ),
                  const Spacer(),
                  Text(
                    '$count 件',
                    style: TextStyle(
                      color: AppTheme.spiritGlow.withValues(alpha: 0.7),
                      fontSize: 11,
                    ),
                  ),
                ],
              ),
            );
          },
        ),
      ],
    );
  }

  String _formatDate(String dateStr) {
    try {
      final date = DateTime.parse(dateStr);
      final month = date.month;
      final day = date.day;
      final hour = date.hour.toString().padLeft(2, '0');
      final minute = date.minute.toString().padLeft(2, '0');
      return '$month月$day日 · $hour:$minute';
    } catch (_) {
      return dateStr;
    }
  }
}
