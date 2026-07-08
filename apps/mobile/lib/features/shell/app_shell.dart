import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/theme/app_theme.dart';
import '../auth/providers/auth_provider.dart';

class AppShell extends ConsumerWidget {
  final Widget child;

  const AppShell({super.key, required this.child});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final location = GoRouterState.of(context).matchedLocation;
    final authState = ref.watch(authStateProvider);
    final characterId = authState.selectedCharacterId ?? '';

    return Scaffold(
      body: Stack(
        children: [
          // 背景渐变
          Container(
            decoration: const BoxDecoration(
              gradient: LinearGradient(
                begin: Alignment.topCenter,
                end: Alignment.bottomCenter,
                colors: [
                  Color(0xFF0F0B1E),
                  Color(0xFF080515),
                ],
              ),
            ),
          ),
          // 内容 - 底部留出导航栏空间
          Padding(
            padding: const EdgeInsets.only(bottom: 68),
            child: child,
          ),
          // 底部导航
          Positioned(
            left: 0,
            right: 0,
            bottom: 0,
            child: _buildBottomNav(context, location, characterId),
          ),
        ],
      ),
    );
  }

  Widget _buildBottomNav(
    BuildContext context,
    String location,
    String characterId,
  ) {
    final items = [
      {
        'path': '/home',
        'icon': Icons.home_outlined,
        'label': '首页',
        'route': '/home',
      },
      {
        'path': '/chat',
        'icon': Icons.chat_bubble_outline,
        'label': '聊天',
        'route': characterId.isNotEmpty ? '/chat/$characterId' : '/home',
      },
      {
        'path': '/memory',
        'icon': Icons.access_time,
        'label': '记忆',
        'route': characterId.isNotEmpty ? '/memory/$characterId' : '/home',
      },
      {
        'path': '/emotion',
        'icon': Icons.mood_outlined,
        'label': '情绪',
        'route': '/emotion',
      },
      {
        'path': '/settings',
        'icon': Icons.settings_outlined,
        'label': '设置',
        'route': '/settings',
      },
    ];

    return Container(
      padding: EdgeInsets.only(
        bottom: MediaQuery.of(context).padding.bottom,
        top: 8,
      ),
      decoration: BoxDecoration(
        color: AppTheme.surfaceColor.withValues(alpha: 0.95),
        border: Border(
          top: BorderSide(
            color: AppTheme.primaryColor.withValues(alpha: 0.1),
            width: 0.5,
          ),
        ),
      ),
      child: Row(
        children: items.map((item) {
          final path = item['path'] as String;
          final isSettingsChild = path == '/settings' &&
              const ['/subscription', '/about', '/privacy', '/terms']
                  .contains(location);
          final isActive = location.startsWith(path) || isSettingsChild;
          return Expanded(
            child: GestureDetector(
              onTap: () => context.go(item['route'] as String),
              behavior: HitTestBehavior.opaque,
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(
                    item['icon'] as IconData,
                    size: 22,
                    color: isActive
                        ? AppTheme.primaryColor
                        : Colors.white.withValues(alpha: 0.4),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    item['label'] as String,
                    style: TextStyle(
                      fontSize: 11,
                      color: isActive
                          ? AppTheme.primaryColor
                          : Colors.white.withValues(alpha: 0.4),
                      fontWeight:
                          isActive ? FontWeight.w600 : FontWeight.normal,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Container(
                    width: 4,
                    height: 4,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      color:
                          isActive ? AppTheme.primaryColor : Colors.transparent,
                    ),
                  ),
                ],
              ),
            ),
          );
        }).toList(),
      ),
    );
  }
}
