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

class LingbanApp extends ConsumerWidget {
  const LingbanApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final authState = ref.watch(authStateProvider);

    final router = GoRouter(
      initialLocation: authState.isAuthenticated ? '/home' : '/onboarding',
      redirect: (context, state) {
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
    );

    return MaterialApp.router(
      title: '灵伴',
      theme: AppTheme.darkTheme,
      routerConfig: router,
      debugShowCheckedModeBanner: false,
    );
  }
}
