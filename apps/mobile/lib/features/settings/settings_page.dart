import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:flutter/services.dart';

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
  Map<String, dynamic> _settings = {};
  bool _exportingData = false;

  @override
  void initState() {
    super.initState();
    _loadCharacters();
    _loadSettings();
  }

  Future<void> _loadCharacters() async {
    try {
      final response = await apiClient.getCharacters();
      final list = List<Map<String, dynamic>>.from(response.data);
      if (mounted) {
        setState(() {
          _characters = list;
        });
      }
    } catch (e) {
      // ignore
    }
  }

  Future<void> _loadSettings() async {
    try {
      final response = await apiClient.getSettings();
      if (mounted) {
        setState(() {
          _settings = Map<String, dynamic>.from(response.data);
        });
      }
    } catch (_) {
      // keep defaults rendered locally
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
            crossAxisCount: 2,
            childAspectRatio: 1.4,
            crossAxisSpacing: 12,
            mainAxisSpacing: 12,
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
        padding: const EdgeInsets.symmetric(vertical: 10, horizontal: 12),
        decoration: BoxDecoration(
          color: AppTheme.cardColor,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(
            color: isActive
                ? AppTheme.spiritGlow.withValues(alpha: 0.4)
                : AppTheme.primaryColor.withValues(alpha: 0.08),
            width: isActive ? 1.5 : 0.5,
          ),
        ),
        child: Stack(
          children: [
            // Active 勾选标记
            if (isActive)
              Positioned(
                top: 0,
                right: 0,
                child: Container(
                  width: 20,
                  height: 20,
                  decoration: const BoxDecoration(
                    color: AppTheme.spiritGlow,
                    shape: BoxShape.circle,
                  ),
                  child: const Icon(Icons.check, size: 14, color: Colors.black),
                ),
              ),
            // 卡片内容
            Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Container(
                  width: 44,
                  height: 44,
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
                      style: TextStyle(color: color, fontSize: 20),
                    ),
                  ),
                ),
                const SizedBox(height: 6),
                Text(
                  name,
                  style: TextStyle(
                    color: AppTheme.primaryColor.withValues(alpha: 0.9),
                    fontSize: 13,
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
                    fontSize: 10,
                    height: 1.2,
                  ),
                ),
              ],
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
              child: Text('✦',
                  style: TextStyle(color: AppTheme.spiritGlow, fontSize: 18)),
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

  String get _careFrequencyLabel {
    switch (_settings['proactive_level'] ?? 'medium') {
      case 'off':
        return '关闭';
      case 'quiet':
      case 'low':
        return '安静';
      case 'high':
        return '积极';
      case 'medium':
      default:
        return '适中';
    }
  }

  Future<void> _showFrequencySheet() async {
    final current = (_settings['proactive_level'] ?? 'medium') as String;
    final options = [
      {'key': 'quiet', 'label': '安静', 'desc': '每天最多 1 次'},
      {'key': 'medium', 'label': '适中', 'desc': '每天最多 2 次'},
      {'key': 'high', 'label': '积极', 'desc': '每天最多 3 次'},
      {'key': 'off', 'label': '关闭', 'desc': '不主动打扰'},
    ];

    await showModalBottomSheet<void>(
      context: context,
      backgroundColor: AppTheme.surfaceColor,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(18)),
      ),
      builder: (sheetContext) {
        return SafeArea(
          child: Padding(
            padding: const EdgeInsets.fromLTRB(16, 16, 16, 20),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: options.map((option) {
                final key = option['key']!;
                final isActive = key == current;
                return ListTile(
                  leading: Icon(
                    isActive
                        ? Icons.radio_button_checked
                        : Icons.radio_button_off,
                    color: isActive
                        ? AppTheme.spiritGlow
                        : AppTheme.primaryColor.withValues(alpha: 0.35),
                  ),
                  title: Text(
                    option['label']!,
                    style: const TextStyle(color: AppTheme.primaryColor),
                  ),
                  subtitle: Text(
                    option['desc']!,
                    style: TextStyle(
                      color: AppTheme.primaryColor.withValues(alpha: 0.45),
                    ),
                  ),
                  onTap: () async {
                    Navigator.of(sheetContext).pop();
                    await _updateFrequency(key);
                  },
                );
              }).toList(),
            ),
          ),
        );
      },
    );
  }

  Future<void> _updateFrequency(String level) async {
    try {
      final response = await apiClient.updateCareFrequency(level);
      if (!mounted) return;
      setState(() {
        _settings = Map<String, dynamic>.from(response.data['settings']);
      });
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('保存失败，请稍后再试')),
        );
      }
    }
  }

  Future<void> _updateDnd(bool enabled) async {
    try {
      final response = await apiClient.updateCareDnd(
        enabled: enabled,
        start: (_settings['dnd_start'] ?? '23:00') as String,
        end: (_settings['dnd_end'] ?? '08:00') as String,
      );
      if (!mounted) return;
      setState(() {
        _settings = Map<String, dynamic>.from(response.data['settings']);
      });
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('保存失败，请稍后再试')),
        );
      }
    }
  }

  Future<void> _updatePushEnabled(bool enabled) async {
    try {
      final response = await apiClient.updateSettings({
        'push_enabled': enabled,
      });
      if (!mounted) return;
      setState(() {
        _settings = Map<String, dynamic>.from(response.data['settings']);
      });
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('保存失败，请稍后再试')),
        );
      }
    }
  }

  Future<void> _updateMemoryEnabled(bool enabled) async {
    try {
      final response = await apiClient.updateMemoryEnabled(enabled);
      if (!mounted) return;
      setState(() {
        _settings = Map<String, dynamic>.from(response.data['settings']);
      });
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('保存失败，请稍后再试')),
        );
      }
    }
  }

  Future<void> _exportData() async {
    if (_exportingData) return;
    setState(() {
      _exportingData = true;
    });
    try {
      final response = await apiClient.exportUserData();
      final data = Map<String, dynamic>.from(response.data);
      final jsonText = const JsonEncoder.withIndent('  ').convert(data);
      await Clipboard.setData(ClipboardData(text: jsonText));
      if (!mounted) return;
      _showExportSheet(data);
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('导出失败: $e')),
        );
      }
    } finally {
      if (mounted) {
        setState(() {
          _exportingData = false;
        });
      }
    }
  }

  void _showExportSheet(Map<String, dynamic> data) {
    int count(String key) {
      final value = data[key];
      return value is List ? value.length : 0;
    }

    showModalBottomSheet<void>(
      context: context,
      backgroundColor: AppTheme.surfaceColor,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(18)),
      ),
      builder: (sheetContext) {
        final exportedAt = data['exported_at']?.toString() ?? '刚刚';
        return SafeArea(
          child: Padding(
            padding: const EdgeInsets.fromLTRB(16, 18, 16, 22),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  '数据已导出',
                  style: TextStyle(
                    color: AppTheme.primaryColor,
                    fontSize: 18,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                const SizedBox(height: 8),
                Text(
                  '完整 JSON 已复制到剪贴板。导出时间：$exportedAt',
                  style: TextStyle(
                    color: AppTheme.primaryColor.withValues(alpha: 0.56),
                    fontSize: 12,
                    height: 1.45,
                  ),
                ),
                const SizedBox(height: 16),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: [
                    _buildExportChip('对话', count('chat_messages')),
                    _buildExportChip('记忆', count('memories')),
                    _buildExportChip('情绪', count('emotion_diary')),
                    _buildExportChip('关怀', count('proactive_messages')),
                    _buildExportChip('推送', count('push_deliveries')),
                  ],
                ),
                const SizedBox(height: 18),
                SizedBox(
                  width: double.infinity,
                  child: ElevatedButton(
                    onPressed: () => Navigator.pop(sheetContext),
                    child: const Text('知道了'),
                  ),
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  Widget _buildExportChip(String label, int count) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: AppTheme.primaryColor.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(999),
      ),
      child: Text(
        '$label $count',
        style: TextStyle(
          color: AppTheme.primaryColor.withValues(alpha: 0.76),
          fontSize: 12,
        ),
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
            value: _careFrequencyLabel,
            onTap: _showFrequencySheet,
          ),
          _buildDivider(),
          _buildSettingTile(
            icon: Icons.dark_mode,
            iconColor: Colors.cyan,
            title: '夜间模式',
            subtitle:
                '${_settings['dnd_start'] ?? '23:00'} - ${_settings['dnd_end'] ?? '08:00'}',
            trailing: Switch(
              value: (_settings['dnd_enabled'] ?? true) as bool,
              onChanged: _updateDnd,
              activeThumbColor: AppTheme.spiritGlow,
            ),
          ),
          _buildDivider(),
          _buildSettingTile(
            icon: Icons.notifications,
            iconColor: Colors.orange,
            title: '提醒通知',
            subtitle: '喝水、休息、睡觉提醒',
            trailing: Switch(
              value: (_settings['push_enabled'] ?? true) as bool,
              onChanged: _updatePushEnabled,
              activeThumbColor: AppTheme.spiritGlow,
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
            icon: Icons.psychology_alt_outlined,
            iconColor: Colors.green,
            title: '长期记忆',
            subtitle: '允许 AI 从后续对话中提取重要记忆',
            trailing: Switch(
              value: (_settings['memory_enabled'] ?? true) as bool,
              onChanged: _updateMemoryEnabled,
              activeThumbColor: AppTheme.spiritGlow,
            ),
          ),
          _buildDivider(),
          _buildSettingTile(
            icon: Icons.download,
            iconColor: Colors.purple,
            title: '数据导出',
            subtitle: '复制账号、对话、记忆和情绪数据 JSON',
            value: _exportingData ? '导出中' : null,
            onTap: _exportData,
          ),
          _buildDivider(),
          _buildSettingTile(
            icon: Icons.lock_outline,
            iconColor: Colors.cyan,
            title: '数据保护',
            subtitle: '导出不包含密码哈希和原始推送 token',
            value: '已启用',
          ),
          _buildDivider(),
          _buildSettingTile(
            icon: Icons.privacy_tip_outlined,
            iconColor: Colors.lightBlueAccent,
            title: '隐私政策',
            subtitle: '查看数据收集范围和你的控制权',
            onTap: () => context.push('/privacy'),
          ),
          _buildDivider(),
          _buildSettingTile(
            icon: Icons.description_outlined,
            iconColor: Colors.amber,
            title: '用户协议',
            subtitle: '查看服务定位和使用边界',
            onTap: () => context.push('/terms'),
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
            onTap: () => context.push('/about'),
          ),
          _buildDivider(),
          _buildSettingTile(
            icon: Icons.workspace_premium_outlined,
            iconColor: Colors.purpleAccent,
            title: '订阅管理',
            subtitle: '查看免费/进阶/专业版权益',
            onTap: () => context.push('/subscription'),
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
      child: Column(
        children: [
          _buildSettingTile(
            icon: Icons.link_off,
            iconColor: Colors.redAccent,
            title: '解除绑定',
            subtitle: '解除与伙伴的羁绊（慎重）',
            onTap: () => _confirmUnbind(selectedId),
          ),
          _buildDivider(),
          _buildSettingTile(
            icon: Icons.person_remove_alt_1_outlined,
            iconColor: Colors.redAccent,
            title: '删除账号',
            subtitle: '申请删除账号，30 天后永久清理',
            onTap: _confirmDeleteAccount,
          ),
        ],
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
        height: 1, color: AppTheme.primaryColor.withValues(alpha: 0.05));
  }

  void _confirmDeleteAccount() {
    final confirmController = TextEditingController();
    final reasonController = TextEditingController();

    showDialog(
      context: context,
      builder: (dialogContext) => AlertDialog(
        backgroundColor: AppTheme.surfaceColor,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        title: const Text('删除账号'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Text('账号会先进入 30 天删除等待期，期间推送会被关闭。确认请输入 DELETE。'),
            const SizedBox(height: 12),
            TextField(
              controller: confirmController,
              decoration: const InputDecoration(hintText: '输入 DELETE'),
            ),
            const SizedBox(height: 10),
            TextField(
              controller: reasonController,
              maxLines: 2,
              decoration: const InputDecoration(hintText: '原因（可选）'),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(dialogContext),
            child: Text(
              '取消',
              style: TextStyle(
                color: AppTheme.primaryColor.withValues(alpha: 0.5),
              ),
            ),
          ),
          TextButton(
            onPressed: () async {
              if (confirmController.text.trim() != 'DELETE') {
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(content: Text('请输入 DELETE 以确认删除账号')),
                );
                return;
              }
              Navigator.pop(dialogContext);
              await _deleteAccount(reasonController.text);
            },
            child: const Text(
              '确认删除',
              style: TextStyle(color: Colors.redAccent),
            ),
          ),
        ],
      ),
    ).whenComplete(() {
      confirmController.dispose();
      reasonController.dispose();
    });
  }

  Future<void> _deleteAccount(String reason) async {
    try {
      await apiClient.deleteAccount(confirm: 'DELETE', reason: reason);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('账号已进入 30 天删除等待期')),
      );
      _loadSettings();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('删除申请失败: $e')),
        );
      }
    }
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
                  ScaffoldMessenger.of(context)
                      .showSnackBar(const SnackBar(content: Text('已清除所有记忆')));
                }
              } catch (e) {
                if (context.mounted) {
                  ScaffoldMessenger.of(context)
                      .showSnackBar(SnackBar(content: Text('清除失败: $e')));
                }
              }
            },
            child:
                const Text('确认清除', style: TextStyle(color: Colors.redAccent)),
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
            onPressed: () async {
              Navigator.pop(context);
              await _unbindCharacter(characterId);
            },
            child:
                const Text('确认解除', style: TextStyle(color: Colors.redAccent)),
          ),
        ],
      ),
    );
  }

  Future<void> _unbindCharacter(String characterId) async {
    try {
      // 清空记忆和对话历史
      await apiClient.clearAllMemories(characterId);
      await apiClient.clearChatHistory(characterId);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('已解除绑定')),
        );
        // 刷新页面
        setState(() {});
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('解除失败: $e')),
        );
      }
    }
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
      case 'heihaung':
        return '🐕';
      default:
        return '✧';
    }
  }
}
