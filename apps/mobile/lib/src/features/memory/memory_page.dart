import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';

/// 记忆管理页面
class MemoryPage extends StatelessWidget {
  const MemoryPage({super.key});

  @override
  Widget build(BuildContext context) {
    // 模拟记忆数据
    final memories = [
      _MemoryItem(
        category: '日常',
        content: '用户今天加班到很晚，看起来很疲惫',
        time: '今天 22:30',
        icon: Icons.work_outline,
      ),
      _MemoryItem(
        category: '情绪',
        content: '用户因为项目进度感到焦虑',
        time: '今天 20:15',
        icon: Icons.sentiment_dissatisfied_outlined,
      ),
      _MemoryItem(
        category: '偏好',
        content: '用户喜欢深夜聊天，通常在22点后活跃',
        time: '持续观察',
        icon: Icons.nightlight_outlined,
      ),
      _MemoryItem(
        category: '重要事件',
        content: '用户提到下周有一个重要的项目汇报',
        time: '昨天 19:00',
        icon: Icons.event_outlined,
      ),
    ];

    return Scaffold(
      appBar: AppBar(
        title: const Text('记忆库'),
        actions: [
          IconButton(
            icon: const Icon(Icons.filter_list),
            onPressed: () {},
          ),
        ],
      ),
      body: Column(
        children: [
          // 记忆统计
          Padding(
            padding: const EdgeInsets.all(16),
            child: Row(
              children: [
                _MemoryStat(
                  label: '总记忆',
                  value: '128',
                  icon: Icons.memory,
                  color: const Color(0xFF8B5CF6),
                ),
                const SizedBox(width: 12),
                _MemoryStat(
                  label: '本周新增',
                  value: '12',
                  icon: Icons.trending_up,
                  color: const Color(0xFF10B981),
                ),
                const SizedBox(width: 12),
                _MemoryStat(
                  label: '重要记忆',
                  value: '5',
                  icon: Icons.star,
                  color: const Color(0xFFF59E0B),
                ),
              ],
            ),
          ),

          // 记忆列表
          Expanded(
            child: ListView.builder(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              itemCount: memories.length,
              itemBuilder: (context, index) {
                final memory = memories[index];
                return _MemoryCard(memory: memory)
                    .animate()
                    .fadeIn(delay: (index * 100).ms)
                    .slideX(begin: 0.05, end: 0);
              },
            ),
          ),
        ],
      ),
    );
  }
}

class _MemoryItem {
  final String category;
  final String content;
  final String time;
  final IconData icon;

  const _MemoryItem({
    required this.category,
    required this.content,
    required this.time,
    required this.icon,
  });
}

class _MemoryStat extends StatelessWidget {
  final String label;
  final String value;
  final IconData icon;
  final Color color;

  const _MemoryStat({
    required this.label,
    required this.value,
    required this.icon,
    required this.color,
  });

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: const Color(0xFF1A1A2E),
          borderRadius: BorderRadius.circular(16),
        ),
        child: Column(
          children: [
            Icon(icon, color: color, size: 24),
            const SizedBox(height: 8),
            Text(
              value,
              style: TextStyle(
                fontSize: 20,
                fontWeight: FontWeight.bold,
                color: color,
              ),
            ),
            const SizedBox(height: 4),
            Text(
              label,
              style: TextStyle(
                fontSize: 12,
                color: Colors.grey[500],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _MemoryCard extends StatelessWidget {
  final _MemoryItem memory;

  const _MemoryCard({required this.memory});

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xFF1A1A2E),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Colors.white.withOpacity(0.05)),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            padding: const EdgeInsets.all(8),
            decoration: BoxDecoration(
              color: const Color(0xFF8B5CF6).withOpacity(0.15),
              borderRadius: BorderRadius.circular(10),
            ),
            child: Icon(
              memory.icon,
              color: const Color(0xFF8B5CF6),
              size: 20,
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Text(
                      memory.category,
                      style: const TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.w600,
                        color: Color(0xFF8B5CF6),
                      ),
                    ),
                    const Spacer(),
                    Text(
                      memory.time,
                      style: TextStyle(
                        fontSize: 11,
                        color: Colors.grey[600],
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 6),
                Text(
                  memory.content,
                  style: TextStyle(
                    fontSize: 14,
                    color: Colors.grey[300],
                    height: 1.4,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
