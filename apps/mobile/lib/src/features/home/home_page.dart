import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:go_router/go_router.dart';

/// 首页 - 角色灵体展示 + 快捷操作
class HomePage extends StatelessWidget {
  const HomePage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: Column(
          children: [
            // 顶部状态栏
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  // 情绪状态
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 14,
                      vertical: 8,
                    ),
                    decoration: BoxDecoration(
                      color: const Color(0xFF1A1A2E),
                      borderRadius: BorderRadius.circular(20),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        const Icon(Icons.wb_sunny_outlined, size: 16, color: Colors.amber),
                        const SizedBox(width: 6),
                        Text(
                          '心情不错',
                          style: TextStyle(
                            fontSize: 13,
                            color: Colors.grey[300],
                          ),
                        ),
                      ],
                    ),
                  ),

                  // 关系等级
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 14,
                      vertical: 8,
                    ),
                    decoration: BoxDecoration(
                      color: const Color(0xFF1A1A2E),
                      borderRadius: BorderRadius.circular(20),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(Icons.favorite, size: 14, color: Colors.purple[300]),
                        const SizedBox(width: 4),
                        Text(
                          'Lv.3 熟悉',
                          style: TextStyle(
                            fontSize: 13,
                            color: Colors.purple[300],
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),

            // 灵体展示区域
            Expanded(
              child: Center(
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    // 灵体动画占位
                    Container(
                      width: 200,
                      height: 200,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        gradient: RadialGradient(
                          colors: [
                            const Color(0xFFC0C0C0).withOpacity(0.3),
                            const Color(0xFFC0C0C0).withOpacity(0.05),
                            Colors.transparent,
                          ],
                        ),
                      ),
                      child: Center(
                        child: Container(
                          width: 120,
                          height: 120,
                          decoration: BoxDecoration(
                            shape: BoxShape.circle,
                            gradient: RadialGradient(
                              colors: [
                                const Color(0xFFC0C0C0).withOpacity(0.6),
                                const Color(0xFF8B5CF6).withOpacity(0.3),
                              ],
                            ),
                            boxShadow: [
                              BoxShadow(
                                color: const Color(0xFF8B5CF6).withOpacity(0.4),
                                blurRadius: 40,
                                spreadRadius: 10,
                              ),
                            ],
                          ),
                        ),
                      ),
                    )
                        .animate(onPlay: (c) => c.repeat())
                        .scale(
                          begin: const Offset(0.95, 0.95),
                          end: const Offset(1.05, 1.05),
                          duration: 3000.ms,
                        )
                        .then()
                        .scale(
                          begin: const Offset(1.05, 1.05),
                          end: const Offset(0.95, 0.95),
                          duration: 3000.ms,
                        ),

                    const SizedBox(height: 24),

                    // 角色名
                    const Text(
                      '银月',
                      style: TextStyle(
                        fontSize: 24,
                        fontWeight: FontWeight.bold,
                        color: Color(0xFFC0C0C0),
                      ),
                    ).animate().fadeIn(delay: 300.ms),

                    const SizedBox(height: 8),

                    // 角色语录
                    Text(
                      '"哼，你终于来了。本姑娘等了好久了。"',
                      style: TextStyle(
                        fontSize: 14,
                        color: Colors.grey[400],
                        fontStyle: FontStyle.italic,
                      ),
                      textAlign: TextAlign.center,
                    )
                        .animate()
                        .fadeIn(delay: 600.ms),
                  ],
                ),
              ),
            ),

            // 底部操作区
            Padding(
              padding: const EdgeInsets.all(24),
              child: Column(
                children: [
                  // 聊天按钮
                  SizedBox(
                    width: double.infinity,
                    child: ElevatedButton.icon(
                      onPressed: () => context.push('/chat/yinyue'),
                      icon: const Icon(Icons.chat_bubble),
                      label: const Text('找银月聊天'),
                      style: ElevatedButton.styleFrom(
                        padding: const EdgeInsets.symmetric(vertical: 16),
                      ),
                    ),
                  ).animate().fadeIn(delay: 800.ms).slideY(begin: 0.2, end: 0),

                  const SizedBox(height: 12),

                  // 语音通话按钮
                  SizedBox(
                    width: double.infinity,
                    child: OutlinedButton.icon(
                      onPressed: () {
                        // TODO: 语音通话
                      },
                      icon: const Icon(Icons.phone),
                      label: const Text('语音通话'),
                      style: OutlinedButton.styleFrom(
                        padding: const EdgeInsets.symmetric(vertical: 16),
                        side: BorderSide(
                          color: Colors.white.withOpacity(0.2),
                        ),
                      ),
                    ),
                  ).animate().fadeIn(delay: 1000.ms).slideY(begin: 0.2, end: 0),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
