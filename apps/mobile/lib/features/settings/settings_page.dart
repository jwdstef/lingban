import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/api/api_client.dart';
import '../../core/theme/app_theme.dart';
import '../auth/providers/auth_provider.dart';

class SettingsPage extends ConsumerStatefulWidget {
  const SettingsPage({super.key});

  @override
  ConsumerState<SettingsPage> createState() => _SettingsPageState();
}

class _SettingsPageState extends ConsumerState<SettingsPage> {
  List<Map<String, dynamic>> _characters = [];
  bool _loadingCharacters = true;

  @override
  void initState() {
    super.initState();
    _loadCharacters();
  }

  Future<void> _loadCharacters() async {
    try {
      final response = await apiClient.getCharacters();
      final list = List<Map<String, dynamic>>.from(response.data);
      if (mounted) setState(() {
        _characters = list;
        _loadingCharacters = false;
      });
    } catch (e) {
      if (mounted) setState(() => _loadingCharacters = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final authState = ref.watch(authStateProvider);
    final selectedId = authState.selectedCharacterId ?? '';

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
                  const Text(
                    '设置',
                    style: TextStyle(
                      color: AppTheme.primaryColor,
                      fontSize: 18,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ],
              ),
            ),
            // 内容
            Expanded(
              child: ListView(
                padding: const EdgeInsets.symmetric(horizontal: 16),
                children: [
                  const SizedBox(height: 8),
                  // 1. 角色选择网格
                  _buildCharacterSection(selectedId),
                  const SizedBox(height: 20),
                  // 2. 当前角色资料卡
                  _buildProfileCard(selectedId),
                  const SizedBox(height: 20),
                  // 3. 伙伴设置
                  _buildGroupTitle('伙伴设置'),
                  const SizedBox(height: 8),
                  _buildPartnerSettings(),
                  const SizedBox(height: 20),
                  // 4. 隐私与安全
                  _buildGroupTitle('隐私与安全'),
                  const SizedBox(height: 8),
                  _buildPrivacySettings(selectedId),
                  const SizedBox(height: 20),
                  // 5. 关于
                  _buildGroupTitle('关于'),
                  const SizedBox(height: 8),
                  _buildAboutSettings(),
                  const SizedBox(height: 20),
                  // 6. 危险操作
                  _buildDangerSection(selectedId),
                  const SizedBox(height: 60),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  // 角色选择网格
  Widget _buildCharacterSection(String selectedId) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(
              '选择你的伙伴',
              style: TextStyle(
                color: AppTheme.primaryColor.withValues(alpha: 0.8),
                fontSize: 14,
                fontWeight: FontWeight.w600,
              ),
            ),
            Text(
              '更多 ›',
              style: TextStyle(
                color: AppTheme.primaryColor.withValues(alpha: 0.4),
                fontSize: 12,
              ),
            ),
          ],
        ),
        const SizedBox(height: 12),
        GridView.builder(
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
            crossAxisCount: 4,
            childAspectRatio: 0.72,
            crossAxisSpacing: 8,
          ),
          itemCount: _characters.length + 1, // +1 for custom
          itemBuilder: (context, index) {
            if (index == _characters.length) {
              return _buildCharacterCard(
                name: '自定义',
                desc: '创造专属\n你的伙伴',
                tag: '即将推出',
                icon: '+',
                color: Colors.grey,
                isActive: false,
                onTap: () {},
              );
            }
            final char = _characters[index];
            final isActive = char['id'] == selectedId;
            final color = Color(char['color'] ?? 0xFF34D399);
            return _buildCharacterCard(
              name: char['name'] ?? '',
              desc: _getCharDesc(char['id'] ?? ''),
              tag: isActive ? '当前选择' : (char['source'] ?? ''),
              icon: _getCharIcon(char['id'] ?? ''),
              color: color,
              isActive: isActive,
              onTap: () => _selectCharacter(char['id']),
            );
          },
        ),
      ],
    );
  }

  Widget _buildCharacterCard({
    required String name,
    required String desc,
    required String tag,
    required String icon,
    required Color color,
    required bool isActive,
    required VoidCallback onTap,
  }) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 10),
        decoration: BoxDecoration(
          color: AppTheme.cardColor,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
            color: isActive
                ? AppTheme.spiritGlow.withValues(alpha: 0.4)
                : AppTheme.primaryColor.withValues(alpha: 0.08),
            width: isActive ? 1.5 : 0.5,
          ),
        ),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Container(
              width: 36,
              height: 36,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                gradient: RadialGradient(
                  colors: [
                    color.withValues(alpha: 0.6),
                    color.withValues(alpha: 0.1),
                  ],
                ),
              ),
              child: Center(
                child: Text(
                  icon,
                  style: TextStyle(color: color, fontSize: 16),
                ),
              ),
            ),
            const SizedBox(height: 6),
            Text(
              name,
              style: TextStyle(
                color: AppTheme.primaryColor.withValues(alpha: 0.9),
                fontSize: 12,
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: 2),
            Text(
              desc,
              textAlign: TextAlign.center,
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(
                color: AppTheme.primaryColor.withValues(alpha: 0.4),
                fontSize: 9,
                height: 1.3,
              ),
            ),
            const SizedBox(height: 4),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
              decoration: BoxDecoration(
                color: isActive
                    ? AppTheme.spiritGlow.withValues(alpha: 0.15)
                    : AppTheme.primaryColor.withValues(alpha: 0.05),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Text(
                tag,
                style: TextStyle(
                  color: isActive
                      ? AppTheme.spiritGlow
                      : AppTheme.primaryColor.withValues(alpha: 0.4),
                  fontSize: 9,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  // 当前角色资料卡
  Widget _buildProfileCard(String selectedId) {
    final character = _characters.isNotEmpty
        ? _characters.where((c) => c['id'] == selectedId).toList()
        : <Map<String, dynamic>>[];
    final name = character.isNotEmpty ? character.first['name'] ?? '灵伴' : '灵伴';

    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppTheme.cardColor,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: AppTheme.primaryColor.withValues(alpha: 0.08),
          width: 0.5,
        ),
      ),
      child: Row(
        children: [
          Container(
            width: 44,
            height: 44,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              gradient: RadialGradient(
                colors: [
                  AppTheme.spiritGlow.withValues(alpha: 0.5),
                  AppTheme.spiritGlow.withValues(alpha: 0.1),
                ],
              ),
              boxShadow: [
                BoxShadow(
                  color: AppTheme.spiritGlow.withValues(alpha: 0.3),
                  blurRadius: 15,
                ),
              ],
            ),
            child: const Center(
              child: Text('✦', style: TextStyle(color: AppTheme.spiritGlow, fontSize: 18)),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  name,
                  style: const TextStyle(
                    color: AppTheme.primaryColor,
                    fontSize: 15,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  '陪伴你第 47 天 · 羁绊等级：老友',
                  style: TextStyle(
                    color: AppTheme.primaryColor.withValues(alpha: 0.4),
                    fontSize: 11,
                  ),
                ),
              ],
            ),
          ),
          Icon(Icons.chevron_right,
              color: AppTheme.primaryColor.withValues(alpha: 0.3), size: 20),
        ],
      ),
    );
  }

  Widget _buildGroupTitle(String title) {
    return Text(
      title,
      style: TextStyle(
        color: AppTheme.primaryColor.withValues(alpha: 0.4),
        fontSize: 13,
        fontWeight: FontWeight.w500,
      ),
    );
  }

  Widget _buildPartnerSettings() {
    return Container(
      decoration: BoxDecoration(
        color: AppTheme.cardColor,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: AppTheme.primaryColor.withValues(alpha: 0.08),
          width: 0.5,
        ),
      ),
      child: Column(
        children: [
          _buildSettingTile(
            icon: Icons.tune,
            iconColor: Colors.purple,
            title: '性格调整',
            subtitle: '傲娇度、毒舌度、关心度',
            value: '默认',
          ),
          _buildDivider(),
          _buildSettingTile(
            icon: Icons.chat,
            iconColor: Colors.pink,
            title: '主动关怀频率',
            subtitle: '伙伴主动找你的频率',
            value: '适中',
          ),
          _buildDivider(),
          _buildSettingTile(
            icon: Icons.dark_mode,
            iconColor: Colors.cyan,
            title: '夜间模式',
            subtitle: '22:00 后自动切换',
            trailing: Switch(
              value: true,
              onChanged: (v) {},
              activeColor: AppTheme.spiritGlow,
            ),
          ),
          _buildDivider(),
          _buildSettingTile(
            icon: Icons.notifications,
            iconColor: Colors.orange,
            title: '提醒通知',
            subtitle: '喝水、休息、睡觉提醒',
            trailing: Switch(
              value: true,
              onChanged: (v) {},
              activeColor: AppTheme.spiritGlow,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildPrivacySettings(String selectedId) {
    return Container(
      decoration: BoxDecoration(
        color: AppTheme.cardColor,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: AppTheme.primaryColor.withValues(alpha: 0.08),
          width: 0.5,
        ),
      ),
      child: Column(
        children: [
          _buildSettingTile(
            icon: Icons.lock,
            iconColor: Colors.green,
            title: '数据加密',
            subtitle: '所有对话和记忆端到端加密',
            value: '已开启',
          ),
          _buildDivider(),
          _buildSettingTile(
            icon: Icons.download,
            iconColor: Colors.purple,
            title: '数据导出',
            subtitle: '导出你的所有记忆数据',
          ),
          _buildDivider(),
          _buildSettingTile(
            icon: Icons.delete_outline,
            iconColor: Colors.pink,
            title: '清除记忆',
            subtitle: '清除伙伴的所有记忆',
            onTap: () => _confirmClearMemories(selectedId),
          ),
        ],
      ),
    );
  }

  Widget _buildAboutSettings() {
    return Container(
      decoration: BoxDecoration(
        color: AppTheme.cardColor,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: AppTheme.primaryColor.withValues(alpha: 0.08),
          width: 0.5,
        ),
      ),
      child: Column(
        children: [
          _buildSettingTile(
            icon: Icons.info_outline,
            iconColor: Colors.cyan,
            title: '关于灵伴',
            subtitle: '版本 1.0.0',
          ),
          _buildDivider(),
          _buildSettingTile(
            icon: Icons.star_outline,
            iconColor: Colors.orange,
            title: '给个好评',
            subtitle: '喜欢的话，给个好评吧',
          ),
        ],
      ),
    );
  }

  Widget _buildDangerSection(String selectedId) {
    return Container(
      decoration: BoxDecoration(
        color: AppTheme.cardColor,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: Colors.redAccent.withValues(alpha: 0.15),
          width: 0.5,
        ),
      ),
      child: _buildSettingTile(
        icon: Icons.link_off,
        iconColor: Colors.redAccent,
        title: '解除绑定',
        subtitle: '解除与伙伴的羁绊（慎重）',
        onTap: () => _confirmUnbind(selectedId),
      ),
    );
  }

  Widget _buildSettingTile({
    required IconData icon,
    Color? iconColor,
    required String title,
    String? subtitle,
    String? value,
    Widget? trailing,
    VoidCallback? onTap,
  }) {
    return ListTile(
      leading: Container(
        width: 32,
        height: 32,
        decoration: BoxDecoration(
          color: (iconColor ?? Colors.grey).withValues(alpha: 0.15),
          borderRadius: BorderRadius.circular(8),
        ),
        child: Icon(icon, color: iconColor ?? Colors.grey, size: 16),
      ),
      title: Text(title,
          style: const TextStyle(color: AppTheme.primaryColor, fontSize: 14)),
      subtitle: subtitle != null
          ? Text(subtitle,
              style: TextStyle(
                  color: AppTheme.primaryColor.withValues(alpha: 0.4),
                  fontSize: 11))
          : null,
      trailing: trailing ??
          (value != null
              ? Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(value,
                        style: TextStyle(
                            color: AppTheme.primaryColor.withValues(alpha: 0.5),
                            fontSize: 12)),
                    const SizedBox(width: 4),
                    Icon(Icons.chevron_right,
                        color: AppTheme.primaryColor.withValues(alpha: 0.3),
                        size: 18),
                  ],
                )
              : Icon(Icons.chevron_right,
                  color: AppTheme.primaryColor.withValues(alpha: 0.3),
                  size: 18)),
      onTap: onTap,
      contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 2),
    );
  }

  Widget _buildDivider() {
    return Divider(
        height: 1,
        color: AppTheme.primaryColor.withValues(alpha: 0.05));
  }

  void _confirmClearMemories(String characterId) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: AppTheme.surfaceColor,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        title: const Text('清除记忆'),
        content: const Text('确定要清除伙伴的所有记忆吗？此操作不可恢复。'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: Text('取消',
                style: TextStyle(
                    color: AppTheme.primaryColor.withValues(alpha: 0.5))),
          ),
          TextButton(
            onPressed: () async {
              Navigator.pop(context);
              try {
                await apiClient.clearAllMemories(characterId);
                if (context.mounted) {
                  ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(content: Text('已清除所有记忆')));
                }
              } catch (e) {
                if (context.mounted) {
                  ScaffoldMessenger.of(context).showSnackBar(
                      SnackBar(content: Text('清除失败: $e')));
                }
              }
            },
            child: const Text('确认清除',
                style: TextStyle(color: Colors.redAccent)),
          ),
        ],
      ),
    );
  }

  void _confirmUnbind(String characterId) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: AppTheme.surfaceColor,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        title: const Text('解除绑定'),
        content: const Text('解除后所有记忆和关系将清零，确定要解除吗？'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: Text('取消',
                style: TextStyle(
                    color: AppTheme.primaryColor.withValues(alpha: 0.5))),
          ),
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('确认解除',
                style: TextStyle(color: Colors.redAccent)),
          ),
        ],
      ),
    );
  }

  Future<void> _selectCharacter(String characterId) async {
    final authNotifier = ref.read(authProvider.notifier);
    try {
      await authNotifier.selectCharacter(characterId);
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text('切换失败: $e')));
      }
    }
  }

  String _getCharDesc(String id) {
    switch (id) {
      case 'yinyue':
        return '傲娇毒舌\n外冷内热';
      case 'babata':
        return '沉稳睿智\n亦师亦友';
      case 'heihaung':
        return '贱萌搞笑\n仗义忠诚';
      default:
        return '专属伙伴';
    }
  }

  String _getCharIcon(String id) {
    switch (id) {
      case 'yinyue':
        return '✦';
      case 'babata':
        return '◈';
      case 'heihuang':
        return '🐕';
      default:
        return '✧';
    }
  }
}
