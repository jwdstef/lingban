import 'package:flutter/material.dart';

/// 设置页面
class SettingsPage extends StatelessWidget {
  const SettingsPage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('设置'),
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          // 角色信息卡片
          Container(
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
              color: const Color(0xFF1A1A2E),
              borderRadius: BorderRadius.circular(16),
            ),
            child: Row(
              children: [
                Container(
                  width: 56,
                  height: 56,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: const Color(0xFFC0C0C0).withOpacity(0.2),
                  ),
                  child: const Center(
                    child: Text(
                      '银',
                      style: TextStyle(
                        fontSize: 24,
                        fontWeight: FontWeight.bold,
                        color: Color(0xFFC0C0C0),
                      ),
                    ),
                  ),
                ),
                const SizedBox(width: 16),
                const Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        '银月',
                        style: TextStyle(
                          fontSize: 18,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      SizedBox(height: 4),
                      Text(
                        '《凡人修仙传》 · Lv.3 熟悉',
                        style: TextStyle(color: Colors.grey, fontSize: 13),
                      ),
                    ],
                  ),
                ),
                const Icon(Icons.chevron_right, color: Colors.grey),
              ],
            ),
          ),

          const SizedBox(height: 24),
          _SectionTitle(title: '角色设置'),
          _SettingsTile(
            icon: Icons.swap_horiz,
            title: '切换角色',
            subtitle: '银月 / 巴巴塔 / 黑皇',
            onTap: () {},
          ),
          _SettingsTile(
            icon: Icons.tune,
            title: '主动性强度',
            subtitle: '中等',
            onTap: () {},
          ),

          const SizedBox(height: 24),
          _SectionTitle(title: '通知设置'),
          _SettingsTile(
            icon: Icons.notifications_outlined,
            title: '推送通知',
            trailing: Switch(
              value: true,
              onChanged: (v) {},
              activeColor: const Color(0xFF8B5CF6),
            ),
          ),
          _SettingsTile(
            icon: Icons.phone_outlined,
            title: '语音通话通知',
            trailing: Switch(
              value: true,
              onChanged: (v) {},
              activeColor: const Color(0xFF8B5CF6),
            ),
          ),
          _SettingsTile(
            icon: Icons.do_not_disturb_outlined,
            title: '免打扰时段',
            subtitle: '23:00 - 08:00',
            onTap: () {},
          ),

          const SizedBox(height: 24),
          _SectionTitle(title: '隐私与安全'),
          _SettingsTile(
            icon: Icons.memory_outlined,
            title: '记忆管理',
            subtitle: '查看、编辑或删除记忆',
            onTap: () {},
          ),
          _SettingsTile(
            icon: Icons.lock_outline,
            title: '隐私设置',
            onTap: () {},
          ),
          _SettingsTile(
            icon: Icons.data_usage,
            title: '数据与存储',
            onTap: () {},
          ),

          const SizedBox(height: 24),
          _SectionTitle(title: '订阅'),
          _SettingsTile(
            icon: Icons.diamond_outlined,
            title: '订阅管理',
            subtitle: '免费版',
            onTap: () {},
          ),

          const SizedBox(height: 48),
          Text(
            '灵伴 v1.0.0',
            style: TextStyle(color: Colors.grey[600], fontSize: 12),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 24),
        ],
      ),
    );
  }
}

class _SectionTitle extends StatelessWidget {
  final String title;
  const _SectionTitle({required this.title});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8, left: 4),
      child: Text(
        title,
        style: TextStyle(
          fontSize: 13,
          fontWeight: FontWeight.w600,
          color: Colors.grey[500],
        ),
      ),
    );
  }
}

class _SettingsTile extends StatelessWidget {
  final IconData icon;
  final String title;
  final String? subtitle;
  final Widget? trailing;
  final VoidCallback? onTap;

  const _SettingsTile({
    required this.icon,
    required this.title,
    this.subtitle,
    this.trailing,
    this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(bottom: 2),
      child: ListTile(
        leading: Icon(icon, color: const Color(0xFF8B5CF6), size: 22),
        title: Text(title, style: const TextStyle(fontSize: 15)),
        subtitle: subtitle != null
            ? Text(
                subtitle!,
                style: TextStyle(fontSize: 12, color: Colors.grey[500]),
              )
            : null,
        trailing: trailing ?? const Icon(Icons.chevron_right, color: Colors.grey),
        onTap: onTap,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      ),
    );
  }
}
