import 'package:flutter/material.dart';

import '../../core/theme/app_theme.dart';

class AboutPage extends StatelessWidget {
  const AboutPage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.transparent,
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.fromLTRB(16, 8, 16, 28),
          children: [
            const _BackHeader(title: '关于灵伴'),
            const SizedBox(height: 18),
            Container(
              padding: const EdgeInsets.all(18),
              decoration: BoxDecoration(
                color: AppTheme.cardColor,
                borderRadius: BorderRadius.circular(16),
                border: Border.all(
                  color: AppTheme.primaryColor.withValues(alpha: 0.08),
                  width: 0.6,
                ),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Container(
                        width: 48,
                        height: 48,
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          gradient: RadialGradient(
                            colors: [
                              AppTheme.spiritGlow.withValues(alpha: 0.58),
                              AppTheme.spiritGlow.withValues(alpha: 0.12),
                            ],
                          ),
                        ),
                        child: const Icon(
                          Icons.auto_awesome,
                          color: AppTheme.spiritGlow,
                        ),
                      ),
                      const SizedBox(width: 12),
                      const Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              '灵伴 AI Companion',
                              style: TextStyle(
                                color: AppTheme.textPrimary,
                                fontSize: 18,
                                fontWeight: FontWeight.w700,
                              ),
                            ),
                            SizedBox(height: 3),
                            Text(
                              '版本 1.0.0 · MVP 内测',
                              style: TextStyle(
                                color: AppTheme.textSecondary,
                                fontSize: 12,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 18),
                  const Text(
                    '我是 AI，会努力成为一个稳定、真诚、记得住你的陪伴者，但我不能替代真实的人际关系、专业心理咨询或紧急救助服务。',
                    style: TextStyle(
                      color: AppTheme.textPrimary,
                      fontSize: 14,
                      height: 1.55,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),
            const _InfoSection(
              title: '我们正在验证什么',
              items: [
                '长期记忆能否让陪伴更具体。',
                '主动关怀能否在不打扰的前提下带来被惦记的感觉。',
                '角色人格能否保持稳定一致。',
              ],
            ),
            const SizedBox(height: 12),
            const _InfoSection(
              title: '健康使用原则',
              items: [
                '产品不会用连续打卡奖励强化依赖。',
                '当互动过长时，AI 会温和提醒你回到现实生活。',
                '遇到危机状态，请优先联系身边的人或专业热线。',
              ],
            ),
            const SizedBox(height: 12),
            Text(
              '心理危机支持：全国 24 小时心理危机干预热线 400-161-9995；北京心理危机研究与干预中心 010-82951332。',
              style: TextStyle(
                color: AppTheme.primaryColor.withValues(alpha: 0.48),
                fontSize: 12,
                height: 1.5,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class LegalPage extends StatelessWidget {
  final LegalDocument document;

  const LegalPage({super.key, required this.document});

  @override
  Widget build(BuildContext context) {
    final isPrivacy = document == LegalDocument.privacy;
    return Scaffold(
      backgroundColor: Colors.transparent,
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.fromLTRB(16, 8, 16, 28),
          children: [
            _BackHeader(title: isPrivacy ? '隐私政策' : '用户协议'),
            const SizedBox(height: 18),
            _LegalIntro(isPrivacy: isPrivacy),
            const SizedBox(height: 14),
            ..._sections(isPrivacy).map(
              (section) => Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: _InfoSection(
                  title: section.title,
                  items: section.items,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  List<_LegalSectionData> _sections(bool isPrivacy) {
    if (isPrivacy) {
      return const [
        _LegalSectionData(
          title: '我们收集的数据',
          items: [
            '账号资料、角色选择、设置偏好。',
            '对话、语音转写、记忆、情绪日记和主动关怀记录。',
            '推送 token 的状态和投递结果，不导出原始 token。',
          ],
        ),
        _LegalSectionData(
          title: '你的控制权',
          items: [
            '你可以查看、编辑、删除记忆。',
            '你可以关闭后续记忆提取。',
            '你可以导出个人数据，或申请删除账号。',
          ],
        ),
        _LegalSectionData(
          title: '安全边界',
          items: [
            '导出的数据不包含密码哈希和原始推送 token。',
            '账号删除申请会进入 30 天等待期。',
            '生产环境需要继续完成加密、审计和法务审核。',
          ],
        ),
      ];
    }

    return const [
      _LegalSectionData(
        title: '服务定位',
        items: [
          '灵伴提供 AI 情感陪伴，不提供医疗诊断。',
          'AI 的回复可能出错，请不要把它作为唯一决策依据。',
          '遇到紧急情况，请立即联系现实中的可信任人员或专业机构。',
        ],
      ),
      _LegalSectionData(
        title: '使用边界',
        items: [
          '请不要要求 AI 生成违法、伤害自己或伤害他人的内容。',
          '请尊重他人隐私，不上传未经授权的敏感信息。',
          '平台会在必要时进行安全干预和风险记录。',
        ],
      ),
      _LegalSectionData(
        title: '订阅与变更',
        items: [
          'MVP 内测阶段暂未接入真实支付。',
          '正式订阅能力上线前，会在 App 内明确展示价格和权益。',
          '服务条款更新时，将以显著方式告知用户。',
        ],
      ),
    ];
  }
}

enum LegalDocument { privacy, terms }

class _LegalIntro extends StatelessWidget {
  final bool isPrivacy;

  const _LegalIntro({required this.isPrivacy});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppTheme.cardColor,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: AppTheme.primaryColor.withValues(alpha: 0.08),
          width: 0.6,
        ),
      ),
      child: Text(
        isPrivacy
            ? '这份说明帮助你理解灵伴如何处理数据，以及你可以怎样控制自己的记忆和账号。'
            : '这份协议说明灵伴的服务边界、使用规则和当前内测阶段的限制。',
        style: const TextStyle(
          color: AppTheme.textPrimary,
          fontSize: 14,
          height: 1.55,
        ),
      ),
    );
  }
}

class _InfoSection extends StatelessWidget {
  final String title;
  final List<String> items;

  const _InfoSection({required this.title, required this.items});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppTheme.cardColor,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: AppTheme.primaryColor.withValues(alpha: 0.08),
          width: 0.6,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title,
            style: const TextStyle(
              color: AppTheme.textPrimary,
              fontSize: 15,
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(height: 12),
          ...items.map(
            (item) => Padding(
              padding: const EdgeInsets.only(bottom: 10),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Container(
                    width: 5,
                    height: 5,
                    margin: const EdgeInsets.only(top: 8),
                    decoration: BoxDecoration(
                      color: AppTheme.spiritGlow.withValues(alpha: 0.78),
                      shape: BoxShape.circle,
                    ),
                  ),
                  const SizedBox(width: 9),
                  Expanded(
                    child: Text(
                      item,
                      style: const TextStyle(
                        color: AppTheme.textSecondary,
                        fontSize: 13,
                        height: 1.45,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _BackHeader extends StatelessWidget {
  final String title;

  const _BackHeader({required this.title});

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        IconButton(
          onPressed: () => Navigator.of(context).maybePop(),
          icon: const Icon(Icons.arrow_back_ios_new, size: 18),
          color: AppTheme.primaryColor.withValues(alpha: 0.76),
          tooltip: '返回',
        ),
        const SizedBox(width: 2),
        Text(
          title,
          style: const TextStyle(
            color: AppTheme.primaryColor,
            fontSize: 18,
            fontWeight: FontWeight.w600,
          ),
        ),
      ],
    );
  }
}

class _LegalSectionData {
  final String title;
  final List<String> items;

  const _LegalSectionData({required this.title, required this.items});
}
