import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/theme/app_theme.dart';
import '../auth/providers/auth_provider.dart';

class SettingsPage extends ConsumerWidget {
  const SettingsPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final authState = ref.watch(authStateProvider);

    return Scaffold(
      backgroundColor: AppTheme.backgroundColor,
      appBar: AppBar(
        title: const Text('设置'),
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          // 用户信息
          _buildUserInfo(context, ref, authState),

          const SizedBox(height: 24),

          // 通知设置
          _buildSectionTitle('通知设置'),
          const SizedBox(height: 8),
          _buildNotificationSettings(context),

          const SizedBox(height: 24),

          // 隐私设置
          _buildSectionTitle('隐私'),
          const SizedBox(height: 8),
          _buildPrivacySettings(context, authState),

          const SizedBox(height: 24),

          // 关于
          _buildSectionTitle('关于'),
          const SizedBox(height: 8),
          _buildAboutSection(context),

          const SizedBox(height: 32),

          // 退出登录
          _buildLogoutButton(context, ref),
        ],
      ),
    );
  }

  Widget _buildUserInfo(BuildContext context, WidgetRef ref, AuthState authState) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          children: [
            Container(
              width: 56,
              height: 56,
              decoration: BoxDecoration(
                gradient: const LinearGradient(
                  colors: [AppTheme.primaryColor, AppTheme.accentColor],
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                ),
                borderRadius: BorderRadius.circular(16),
              ),
              child: const Icon(Icons.person, color: Colors.white, size: 28),
            ),
            const SizedBox(width: 16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    authState.nickname ?? '灵伴用户',
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 16,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    'ID: ${authState.userId?.substring(0, 8) ?? '---'}...',
                    style: TextStyle(
                      color: Colors.white.withOpacity(0.5),
                      fontSize: 12,
                    ),
                  ),
                ],
              ),
            ),
            Icon(
              Icons.chevron_right,
              color: Colors.white.withOpacity(0.3),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildSectionTitle(String title) {
    return Text(
      title,
      style: TextStyle(
        color: Colors.white.withOpacity(0.5),
        fontSize: 13,
        fontWeight: FontWeight.w500,
      ),
    );
  }

  Widget _buildNotificationSettings(BuildContext context) {
    return Card(
      child: Column(
        children: [
          _buildSettingTile(
            icon: Icons.notifications_active_outlined,
            title: '主动关怀',
            subtitle: '允许 TA 主动发消息给你',
            trailing: Switch(
              value: true,
              onChanged: (v) {},
              activeColor: AppTheme.primaryColor,
            ),
          ),
          const Divider(height: 1, color: Colors.white10),
          _buildSettingTile(
            icon: Icons.do_not_disturb_outlined,
            title: '免打扰时段',
            subtitle: '23:00 - 08:00',
            trailing: Icon(
              Icons.chevron_right,
              color: Colors.white.withOpacity(0.3),
            ),
            onTap: () {},
          ),
        ],
      ),
    );
  }

  Widget _buildPrivacySettings(BuildContext context, AuthState authState) {
    final characterId = authState.selectedCharacterId;

    return Card(
      child: Column(
        children: [
          _buildSettingTile(
            icon: Icons.psychology,
            title: '查看记忆',
            subtitle: 'TA 记住的关于你的事',
            trailing: Icon(
              Icons.chevron_right,
              color: Colors.white.withOpacity(0.3),
            ),
            onTap: characterId != null
                ? () => context.push('/memory/$characterId')
                : null,
          ),
          const Divider(height: 1, color: Colors.white10),
          _buildSettingTile(
            icon: Icons.delete_outline,
            title: '清空所有记忆',
            subtitle: '删除 TA 记住的所有事',
            trailing: Icon(
              Icons.chevron_right,
              color: Colors.white.withOpacity(0.3),
            ),
            onTap: () => _confirmClearMemories(context, characterId),
          ),
        ],
      ),
    );
  }

  Widget _buildAboutSection(BuildContext context) {
    return Card(
      child: Column(
        children: [
          _buildSettingTile(
            icon: Icons.info_outline,
            title: '关于灵伴',
            subtitle: '版本 1.0.0',
            trailing: Icon(
              Icons.chevron_right,
              color: Colors.white.withOpacity(0.3),
            ),
            onTap: () {},
          ),
          const Divider(height: 1, color: Colors.white10),
          _buildSettingTile(
            icon: Icons.feedback_outlined,
            title: '意见反馈',
            subtitle: '',
            trailing: Icon(
              Icons.chevron_right,
              color: Colors.white.withOpacity(0.3),
            ),
            onTap: () {},
          ),
        ],
      ),
    );
  }

  Widget _buildLogoutButton(BuildContext context, WidgetRef ref) {
    return SizedBox(
      width: double.infinity,
      child: OutlinedButton(
        onPressed: () => _confirmLogout(context, ref),
        style: OutlinedButton.styleFrom(
          foregroundColor: Colors.redAccent,
          side: const BorderSide(color: Colors.redAccent, width: 0.5),
          padding: const EdgeInsets.symmetric(vertical: 14),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
          ),
        ),
        child: const Text('退出登录'),
      ),
    );
  }

  Widget _buildSettingTile({
    required IconData icon,
    required String title,
    String? subtitle,
    Widget? trailing,
    VoidCallback? onTap,
  }) {
    return ListTile(
      leading: Icon(icon, color: Colors.white70, size: 22),
      title: Text(title, style: const TextStyle(color: Colors.white, fontSize: 15)),
      subtitle: subtitle != null && subtitle.isNotEmpty
          ? Text(
              subtitle,
              style: TextStyle(
                color: Colors.white.withOpacity(0.4),
                fontSize: 12,
              ),
            )
          : null,
      trailing: trailing,
      onTap: onTap,
      contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
    );
  }

  void _confirmClearMemories(BuildContext context, String? characterId) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: AppTheme.surfaceColor,
        title: const Text('确认清空'),
        content: const Text('清空后无法恢复，TA 将忘记所有关于你的记忆。确定要清空吗？'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('取消'),
          ),
          TextButton(
            onPressed: () {
              Navigator.pop(context);
              // TODO: 调用清空记忆 API
            },
            child: const Text('确认清空', style: TextStyle(color: Colors.redAccent)),
          ),
        ],
      ),
    );
  }

  void _confirmLogout(BuildContext context, WidgetRef ref) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: AppTheme.surfaceColor,
        title: const Text('退出登录'),
        content: const Text('退出后需要重新登录才能使用。'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('取消'),
          ),
          TextButton(
            onPressed: () {
              Navigator.pop(context);
              ref.read(authProvider.notifier).logout();
              context.go('/onboarding');
            },
            child: const Text('确认退出', style: TextStyle(color: Colors.redAccent)),
          ),
        ],
      ),
    );
  }
}
