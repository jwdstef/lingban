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
  static const _categoryOptions = [
    {'key': 'daily', 'label': '日常'},
    {'key': 'emotion', 'label': '情绪'},
    {'key': 'preference', 'label': '偏好'},
    {'key': 'event', 'label': '事件'},
    {'key': 'person', 'label': '人物'},
    {'key': 'fact', 'label': '事实'},
  ];

  final TextEditingController _searchController = TextEditingController();
  List<Map<String, dynamic>> _memories = [];
  List<Map<String, dynamic>> _categories = [];
  bool _isLoading = true;
  String? _selectedCategory;

  @override
  void initState() {
    super.initState();
    _loadMemories();
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  Future<void> _loadMemories() async {
    setState(() => _isLoading = true);
    try {
      final query = _searchController.text.trim();
      final response = await apiClient.getMemories(
        widget.characterId,
        category: _selectedCategory,
        query: query.isEmpty ? null : query,
      );
      final data = response.data;
      if (mounted) {
        setState(() {
          _memories = List<Map<String, dynamic>>.from(data['memories'] ?? []);
          _categories =
              List<Map<String, dynamic>>.from(data['categories'] ?? []);
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
                        _buildSearchBar(),
                        const SizedBox(height: 12),
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
  Widget _buildSearchBar() {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
      decoration: BoxDecoration(
        color: AppTheme.cardColor,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(
          color: AppTheme.primaryColor.withValues(alpha: 0.1),
          width: 0.5,
        ),
      ),
      child: Row(
        children: [
          Icon(
            Icons.search,
            size: 20,
            color: AppTheme.primaryColor.withValues(alpha: 0.45),
          ),
          const SizedBox(width: 8),
          Expanded(
            child: TextField(
              controller: _searchController,
              textInputAction: TextInputAction.search,
              onChanged: (_) => setState(() {}),
              onSubmitted: (_) => _loadMemories(),
              style: const TextStyle(
                color: AppTheme.primaryColor,
                fontSize: 14,
              ),
              decoration: InputDecoration(
                border: InputBorder.none,
                hintText: '搜索记忆',
                hintStyle: TextStyle(
                  color: AppTheme.primaryColor.withValues(alpha: 0.35),
                  fontSize: 14,
                ),
              ),
            ),
          ),
          if (_searchController.text.isNotEmpty)
            GestureDetector(
              onTap: () {
                _searchController.clear();
                _loadMemories();
              },
              child: Icon(
                Icons.close,
                size: 18,
                color: AppTheme.primaryColor.withValues(alpha: 0.45),
              ),
            )
          else
            GestureDetector(
              onTap: _loadMemories,
              child: const Icon(
                Icons.arrow_forward,
                size: 18,
                color: AppTheme.spiritGlow,
              ),
            ),
        ],
      ),
    );
  }

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
                style: const TextStyle(
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
          ..._memories
              .take(5)
              .toList()
              .asMap()
              .entries
              .map((entry) => _buildTimelineItem(entry.key, entry.value)),
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

  String _categoryLabel(String category) {
    return _categoryOptions.firstWhere(
      (item) => item['key'] == category,
      orElse: () => {'key': category, 'label': category},
    )['label']!;
  }

  String _tagsText(Map<String, dynamic> memory) {
    final tags = List<String>.from(memory['emotion_tags'] ?? []);
    return tags.join(', ');
  }

  Future<void> _deleteMemory(Map<String, dynamic> memory) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogContext) {
        return AlertDialog(
          backgroundColor: AppTheme.cardColor,
          title: const Text(
            '删除这条记忆？',
            style: TextStyle(color: AppTheme.primaryColor),
          ),
          content: Text(
            memory['content'] ?? '',
            style: TextStyle(
              color: AppTheme.primaryColor.withValues(alpha: 0.75),
              height: 1.4,
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(dialogContext).pop(false),
              child: Text(
                '取消',
                style: TextStyle(
                  color: AppTheme.primaryColor.withValues(alpha: 0.55),
                ),
              ),
            ),
            TextButton.icon(
              onPressed: () => Navigator.of(dialogContext).pop(true),
              icon: const Icon(Icons.delete_outline, size: 18),
              label: const Text('删除'),
              style: TextButton.styleFrom(foregroundColor: Colors.redAccent),
            ),
          ],
        );
      },
    );

    if (confirmed != true) return;

    try {
      await apiClient.deleteMemory(widget.characterId, memory['id'] as String);
      await _loadMemories();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('记忆已删除')),
        );
      }
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('删除失败，请稍后再试')),
        );
      }
    }
  }

  Future<void> _showEditMemorySheet(Map<String, dynamic> memory) async {
    final contentController =
        TextEditingController(text: memory['content'] as String? ?? '');
    final tagsController = TextEditingController(text: _tagsText(memory));
    var selectedCategory = memory['category'] as String? ?? 'daily';
    var importance = ((memory['importance'] as num?)?.toDouble() ?? 5)
        .clamp(1, 10)
        .toDouble();
    var isSaving = false;

    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: AppTheme.surfaceColor,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (sheetContext) {
        return StatefulBuilder(
          builder: (sheetContext, setSheetState) {
            final bottomInset = MediaQuery.of(sheetContext).viewInsets.bottom;
            return Padding(
              padding: EdgeInsets.fromLTRB(20, 18, 20, 20 + bottomInset),
              child: SingleChildScrollView(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        const Icon(Icons.edit_outlined,
                            color: AppTheme.spiritGlow, size: 20),
                        const SizedBox(width: 8),
                        const Text(
                          '编辑记忆',
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
                            color:
                                AppTheme.primaryColor.withValues(alpha: 0.55),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 14),
                    TextField(
                      controller: contentController,
                      minLines: 3,
                      maxLines: 5,
                      style: const TextStyle(
                        color: AppTheme.primaryColor,
                        height: 1.4,
                      ),
                      decoration: _sheetInputDecoration('记忆内容'),
                    ),
                    const SizedBox(height: 12),
                    DropdownButtonFormField<String>(
                      initialValue: selectedCategory,
                      dropdownColor: AppTheme.cardColor,
                      style: const TextStyle(color: AppTheme.primaryColor),
                      decoration: _sheetInputDecoration('分类'),
                      items: _categoryOptions.map((item) {
                        return DropdownMenuItem<String>(
                          value: item['key'],
                          child: Text(item['label']!),
                        );
                      }).toList(),
                      onChanged: (value) {
                        if (value != null) {
                          setSheetState(() => selectedCategory = value);
                        }
                      },
                    ),
                    const SizedBox(height: 12),
                    TextField(
                      controller: tagsController,
                      style: const TextStyle(color: AppTheme.primaryColor),
                      decoration: _sheetInputDecoration('情绪标签，逗号分隔'),
                    ),
                    const SizedBox(height: 14),
                    Text(
                      '重要度 ${importance.round()}',
                      style: TextStyle(
                        color: AppTheme.primaryColor.withValues(alpha: 0.75),
                        fontSize: 13,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    Slider(
                      value: importance,
                      min: 1,
                      max: 10,
                      divisions: 9,
                      activeColor: AppTheme.spiritGlow,
                      inactiveColor:
                          AppTheme.primaryColor.withValues(alpha: 0.15),
                      label: importance.round().toString(),
                      onChanged: (value) {
                        setSheetState(() => importance = value);
                      },
                    ),
                    const SizedBox(height: 8),
                    SizedBox(
                      width: double.infinity,
                      child: FilledButton.icon(
                        onPressed: isSaving
                            ? null
                            : () async {
                                final content = contentController.text.trim();
                                if (content.isEmpty) {
                                  ScaffoldMessenger.of(context).showSnackBar(
                                    const SnackBar(
                                      content: Text('记忆内容不能为空'),
                                    ),
                                  );
                                  return;
                                }

                                setSheetState(() => isSaving = true);
                                final tags = tagsController.text
                                    .split(RegExp(r'[,，]'))
                                    .map((tag) => tag.trim())
                                    .where((tag) => tag.isNotEmpty)
                                    .toList();
                                try {
                                  await apiClient.updateMemory(
                                    widget.characterId,
                                    memory['id'] as String,
                                    {
                                      'content': content,
                                      'category': selectedCategory,
                                      'importance': importance.round(),
                                      'emotion_tags': tags,
                                    },
                                  );
                                  if (!mounted || !sheetContext.mounted) return;
                                  Navigator.of(sheetContext).pop();
                                  await _loadMemories();
                                  if (!mounted) return;
                                  ScaffoldMessenger.of(context).showSnackBar(
                                    const SnackBar(content: Text('记忆已更新')),
                                  );
                                } catch (_) {
                                  if (mounted) {
                                    ScaffoldMessenger.of(context).showSnackBar(
                                      const SnackBar(
                                        content: Text('保存失败，请稍后再试'),
                                      ),
                                    );
                                  }
                                } finally {
                                  if (mounted && sheetContext.mounted) {
                                    setSheetState(() => isSaving = false);
                                  }
                                }
                              },
                        icon: isSaving
                            ? const SizedBox(
                                width: 16,
                                height: 16,
                                child:
                                    CircularProgressIndicator(strokeWidth: 2),
                              )
                            : const Icon(Icons.check),
                        label: Text(isSaving ? '保存中' : '保存'),
                      ),
                    ),
                  ],
                ),
              ),
            );
          },
        );
      },
    );

    contentController.dispose();
    tagsController.dispose();
  }

  InputDecoration _sheetInputDecoration(String label) {
    return InputDecoration(
      labelText: label,
      labelStyle: TextStyle(
        color: AppTheme.primaryColor.withValues(alpha: 0.45),
      ),
      filled: true,
      fillColor: AppTheme.cardColor,
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(12),
        borderSide: BorderSide(
          color: AppTheme.primaryColor.withValues(alpha: 0.1),
        ),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(12),
        borderSide: const BorderSide(color: AppTheme.spiritGlow),
      ),
    );
  }

  Widget _buildTimelineItem(int index, Map<String, dynamic> memory) {
    final emotionTags = List<String>.from(memory['emotion_tags'] ?? []);
    final category = memory['category'] as String? ?? '';
    final tag =
        emotionTags.isNotEmpty ? emotionTags.first : _categoryLabel(category);
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
                Row(
                  children: [
                    Expanded(
                      child: Text(
                        dateStr,
                        style: TextStyle(
                          color: AppTheme.primaryColor.withValues(alpha: 0.4),
                          fontSize: 11,
                        ),
                      ),
                    ),
                    GestureDetector(
                      onTap: () => _showEditMemorySheet(memory),
                      child: Icon(
                        Icons.edit_outlined,
                        size: 16,
                        color: AppTheme.primaryColor.withValues(alpha: 0.45),
                      ),
                    ),
                    const SizedBox(width: 12),
                    GestureDetector(
                      onTap: () => _deleteMemory(memory),
                      child: Icon(
                        Icons.delete_outline,
                        size: 16,
                        color: Colors.redAccent.withValues(alpha: 0.75),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 4),
                GestureDetector(
                  onTap: () => _showEditMemorySheet(memory),
                  child: Text(
                    memory['content'] ?? '',
                    style: TextStyle(
                      color: AppTheme.primaryColor.withValues(alpha: 0.85),
                      fontSize: 13,
                      height: 1.4,
                    ),
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
      {
        'icon': Icons.nightlight_round,
        'color': AppTheme.spiritGlow,
        'title': '深夜emo',
        'desc': '失眠、焦虑、突然难过...',
        'category': 'emotion',
      },
      {
        'icon': Icons.work_outline,
        'color': AppTheme.accentColor,
        'title': '职场生存',
        'desc': '加班、甩锅、想辞职...',
        'category': 'daily',
      },
      {
        'icon': Icons.home_outlined,
        'color': AppTheme.emotionThinking,
        'title': '一个人的日子',
        'desc': '搬家、生病、一个人过节...',
        'category': 'fact',
      },
      {
        'icon': Icons.auto_awesome,
        'color': AppTheme.emotionHappy,
        'title': '小确幸',
        'desc': '做饭成功、涨薪、遇到好人...',
        'category': 'event',
      },
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
            final count = _countByCategory(item['category'] as String);
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
                  Icon(
                    item['icon'] as IconData,
                    color: item['color'] as Color,
                    size: 20,
                  ),
                  const SizedBox(height: 6),
                  Text(
                    item['title'] as String,
                    style: TextStyle(
                      color: AppTheme.primaryColor.withValues(alpha: 0.9),
                      fontSize: 13,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    item['desc'] as String,
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
