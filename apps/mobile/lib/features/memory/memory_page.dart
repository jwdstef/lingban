import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api/api_client.dart';
import '../../core/theme/app_theme.dart';

class MemoryPage extends ConsumerStatefulWidget {
  final String characterId;

  const MemoryPage({super.key, required this.characterId});

  @override
  ConsumerState<MemoryPage> createState() => _MemoryPageState();
}

class _MemoryPageState extends ConsumerState<MemoryPage> {
  String? _selectedCategory;
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
      final response = await apiClient.getMemories(
        widget.characterId,
        category: _selectedCategory,
      );
      final data = response.data;

      if (mounted) {
        setState(() {
          _memories = List<Map<String, dynamic>>.from(data['memories'] ?? []);
          _categories = List<Map<String, dynamic>>.from(data['categories'] ?? []);
          _isLoading = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() => _isLoading = false);
      }
    }
  }

  Future<void> _deleteMemory(String memoryId) async {
    try {
      await apiClient.deleteMemory(widget.characterId, memoryId);
      _loadMemories();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('删除失败: $e')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.backgroundColor,
      appBar: AppBar(
        title: const Text('TA 记住的'),
      ),
      body: Column(
        children: [
          // 分类筛选
          _buildCategoryFilter(),

          // 记忆列表
          Expanded(
            child: _isLoading
                ? const Center(child: CircularProgressIndicator())
                : _buildMemoryList(),
          ),
        ],
      ),
    );
  }

  Widget _buildCategoryFilter() {
    return Container(
      height: 56,
      padding: const EdgeInsets.symmetric(horizontal: 16),
      child: ListView(
        scrollDirection: Axis.horizontal,
        children: [
          _buildCategoryChip(null, '全部'),
          ..._categories.map((cat) => _buildCategoryChip(
            cat['category'],
            '${_getCategoryLabel(cat['category'])} (${cat['count']})',
          )),
        ],
      ),
    );
  }

  Widget _buildCategoryChip(String? category, String label) {
    final isSelected = _selectedCategory == category;

    return Padding(
      padding: const EdgeInsets.only(right: 8, top: 12, bottom: 12),
      child: GestureDetector(
        onTap: () {
          setState(() => _selectedCategory = category);
          _loadMemories();
        },
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
          decoration: BoxDecoration(
            color: isSelected ? AppTheme.primaryColor : AppTheme.cardColor,
            borderRadius: BorderRadius.circular(20),
          ),
          child: Text(
            label,
            style: TextStyle(
              color: isSelected ? Colors.white : Colors.white70,
              fontSize: 13,
              fontWeight: isSelected ? FontWeight.w600 : FontWeight.normal,
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildMemoryList() {
    if (_memories.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.psychology,
              size: 64,
              color: Colors.white.withOpacity(0.3),
            ),
            const SizedBox(height: 16),
            Text(
              '还没有记忆',
              style: TextStyle(
                color: Colors.white.withOpacity(0.5),
                fontSize: 16,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              '和 TA 多聊聊，TA 会记住你的',
              style: TextStyle(
                color: Colors.white.withOpacity(0.3),
                fontSize: 14,
              ),
            ),
          ],
        ),
      );
    }

    return ListView.builder(
      padding: const EdgeInsets.all(16),
      itemCount: _memories.length,
      itemBuilder: (context, index) {
        final memory = _memories[index];
        return _buildMemoryCard(memory);
      },
    );
  }

  Widget _buildMemoryCard(Map<String, dynamic> memory) {
    final category = memory['category'] ?? 'daily';
    final importance = memory['importance'] ?? 5;
    final emotionTags = List<String>.from(memory['emotion_tags'] ?? []);

    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // 顶部：分类 + 重要度
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  decoration: BoxDecoration(
                    color: _getCategoryColor(category).withOpacity(0.2),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Text(
                    _getCategoryLabel(category),
                    style: TextStyle(
                      color: _getCategoryColor(category),
                      fontSize: 11,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ),
                const SizedBox(width: 8),
                // 重要度指示器
                Row(
                  children: List.generate(
                    5,
                    (i) => Icon(
                      Icons.star,
                      size: 12,
                      color: i < (importance / 2)
                          ? Colors.amber
                          : Colors.white.withOpacity(0.2),
                    ),
                  ),
                ),
                const Spacer(),
                // 删除按钮
                IconButton(
                  icon: Icon(
                    Icons.delete_outline,
                    size: 18,
                    color: Colors.white.withOpacity(0.3),
                  ),
                  onPressed: () => _confirmDelete(memory['id']),
                  padding: EdgeInsets.zero,
                  constraints: const BoxConstraints(),
                ),
              ],
            ),
            const SizedBox(height: 12),
            // 内容
            Text(
              memory['content'] ?? '',
              style: const TextStyle(
                color: Colors.white,
                fontSize: 15,
                height: 1.5,
              ),
            ),
            // 情感标签
            if (emotionTags.isNotEmpty) ...[
              const SizedBox(height: 12),
              Wrap(
                spacing: 6,
                children: emotionTags.map((tag) {
                  return Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                    decoration: BoxDecoration(
                      color: Colors.white.withOpacity(0.1),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Text(
                      tag,
                      style: TextStyle(
                        color: Colors.white.withOpacity(0.6),
                        fontSize: 11,
                      ),
                    ),
                  );
                }).toList(),
              ),
            ],
          ],
        ),
      ),
    );
  }

  void _confirmDelete(String memoryId) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: AppTheme.surfaceColor,
        title: const Text('删除记忆'),
        content: const Text('确定要删除这条记忆吗？删除后 TA 将不再记得这件事。'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('取消'),
          ),
          TextButton(
            onPressed: () {
              Navigator.pop(context);
              _deleteMemory(memoryId);
            },
            child: const Text('删除', style: TextStyle(color: Colors.redAccent)),
          ),
        ],
      ),
    );
  }

  String _getCategoryLabel(String category) {
    const labels = {
      'daily': '日常',
      'emotion': '情绪',
      'preference': '偏好',
      'event': '事件',
      'person': '人物',
      'fact': '事实',
    };
    return labels[category] ?? category;
  }

  Color _getCategoryColor(String category) {
    const colors = {
      'daily': Colors.blue,
      'emotion': Colors.pink,
      'preference': Colors.green,
      'event': Colors.orange,
      'person': Colors.purple,
      'fact': Colors.teal,
    };
    return colors[category] ?? Colors.grey;
  }
}
