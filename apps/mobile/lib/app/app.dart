import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../core/theme/app_theme.dart';
import '../features/auth/providers/auth_provider.dart';
import '../features/onboarding/onboarding_page.dart';
import '../features/home/home_page.dart';
import '../features/chat/chat_page.dart';
import '../features/memory/memory_page.dart';
import '../features/settings/settings_page.dart';
import '../features/shell/app_shell.dart';

// GoRouter 只创建一次，避免每次 auth 状态变化都重建路由栈
final _rootNavigatorKey = GlobalKey<NavigatorState>();

GoRouter _createRouter(Ref ref) {
  return GoRouter(
    navigatorKey: _rootNavigatorKey,
    initialLocation: '/onboarding',
    redirect: (context, state) {
      final authState = ref.read(authProvider);
      final isAuthenticated = authState.isAuthenticated;
      final isOnboarding = state.matchedLocation == '/onboarding';

      if (!isAuthenticated && !isOnboarding) {
        return '/onboarding';
      }
      if (isAuthenticated && isOnboarding) {
        return '/home';
      }
      return null;
    },
    routes: [
      GoRoute(
        path: '/onboarding',
        builder: (context, state) => const OnboardingPage(),
      ),
      ShellRoute(
        builder: (context, state, child) => AppShell(child: child),
        routes: [
          GoRoute(
            path: '/home',
            builder: (context, state) => const HomePage(),
          ),
          GoRoute(
            path: '/chat/:characterId',
            builder: (context, state) {
              final characterId = state.pathParameters['characterId']!;
              return ChatPage(characterId: characterId);
            },
          ),
          GoRoute(
            path: '/memory/:characterId',
            builder: (context, state) {
              final characterId = state.pathParameters['characterId']!;
              return MemoryPage(characterId: characterId);
            },
          ),
          GoRoute(
            path: '/settings',
            builder: (context, state) => const SettingsPage(),
          ),
        ],
      ),
    ],
  );
}

class LingbanApp extends ConsumerStatefulWidget {
  const LingbanApp({super.key});

  @override
  ConsumerState<LingbanApp> createState() => _LingbanAppState();
}

class _LingbanAppState extends ConsumerState<LingbanApp> {
  late final GoRouter _router;

  @override
  void initState() {
    super.initState();
    _router = _createRouter(ref);
    // 监听 auth 状态变化，触发 GoRouter redirect 重新评估
    ref.listen(authProvider, (_, __) {
      _router.go(_router.routerDelegate.currentConfiguration.uri.toString());
    });
  }

  @override
  void dispose() {
    _router.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp.router(
      title: '灵伴',
      theme: AppTheme.darkTheme,
      routerConfig: _router,
      debugShowCheckedModeBanner: false,
    );
  }
}
