import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:go_router/go_router.dart';
import '../../core/constants/app_constants.dart';

/// 引导页 - 角色选择
class OnboardingPage extends StatefulWidget {
  const OnboardingPage({super.key});

  @override
  State<OnboardingPage> createState() => _OnboardingPageState();
}

class _OnboardingPageState extends State<OnboardingPage> {
  int? _selectedIndex;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            children: [
              const SizedBox(height: 48),

              // 标题
              Text(
                '选择你的灵伴',
                style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                      fontWeight: FontWeight.bold,
                    ),
              )
                  .animate()
                  .fadeIn(duration: 600.ms)
                  .slideY(begin: -0.2, end: 0),
              const SizedBox(height: 8),
              Text(
                '每个角色都有独立的性格和记忆\n选择一个最契合你的伙伴',
                textAlign: TextAlign.center,
                style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                      color: Colors.grey,
                    ),
              )
                  .animate()
                  .fadeIn(delay: 200.ms, duration: 600.ms),
              const SizedBox(height: 40),

              // 角色卡片列表
              Expanded(
                child: ListView.separated(
                  itemCount: AppConstants.characters.length,
                  separatorBuilder: (_, __) => const SizedBox(height: 16),
                  itemBuilder: (context, index) {
                    final character = AppConstants.characters[index];
                    final isSelected = _selectedIndex == index;

                    return _CharacterCard(
                      character: character,
                      isSelected: isSelected,
                      onTap: () => setState(() => _selectedIndex = index),
                    )
                        .animate()
                        .fadeIn(
                          delay: (400 + index * 150).ms,
                          duration: 500.ms,
                        )
                        .slideX(begin: 0.1, end: 0);
                  },
                ),
              ),

              const SizedBox(height: 24),

              // 确认按钮
              SizedBox(
                width: double.infinity,
                child: ElevatedButton(
                  onPressed: _selectedIndex != null
                      ? () => context.go('/home')
                      : null,
                  child: const Text('开始陪伴之旅', style: TextStyle(fontSize: 16)),
                ),
              )
                  .animate()
                  .fadeIn(delay: 900.ms, duration: 500.ms)
                  .slideY(begin: 0.2, end: 0),
              const SizedBox(height: 24),
            ],
          ),
        ),
      ),
    );
  }
}

class _CharacterCard extends StatelessWidget {
  final CharacterPreset character;
  final bool isSelected;
  final VoidCallback onTap;

  const _CharacterCard({
    required this.character,
    required this.isSelected,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 300),
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(
          color: isSelected
              ? Color(character.color).withOpacity(0.15)
              : const Color(0xFF1A1A2E),
          borderRadius: BorderRadius.circular(20),
          border: Border.all(
            color: isSelected
                ? Color(character.color)
                : Colors.white.withOpacity(0.1),
            width: isSelected ? 2 : 1,
          ),
        ),
        child: Row(
          children: [
            // 角色头像占位
            Container(
              width: 64,
              height: 64,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: Color(character.color).withOpacity(0.3),
              ),
              child: Center(
                child: Text(
                  character.name[0],
                  style: TextStyle(
                    fontSize: 28,
                    fontWeight: FontWeight.bold,
                    color: Color(character.color),
                  ),
                ),
              ),
            ),
            const SizedBox(width: 16),

            // 角色信息
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Text(
                        character.name,
                        style: const TextStyle(
                          fontSize: 20,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      const SizedBox(width: 8),
                      Text(
                        '《${character.source}》',
                        style: TextStyle(
                          fontSize: 12,
                          color: Colors.grey[500],
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 4),
                  Text(
                    character.description,
                    style: TextStyle(
                      fontSize: 14,
                      color: Colors.grey[400],
                    ),
                  ),
                  const SizedBox(height: 8),
                  Wrap(
                    spacing: 8,
                    children: character.tags.map((tag) {
                      return Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 10,
                          vertical: 4,
                        ),
                        decoration: BoxDecoration(
                          color: Color(character.color).withOpacity(0.2),
                          borderRadius: BorderRadius.circular(12),
                        ),
                        child: Text(
                          tag,
                          style: TextStyle(
                            fontSize: 12,
                            color: Color(character.color),
                          ),
                        ),
                      );
                    }).toList(),
                  ),
                ],
              ),
            ),

            // 选中标记
            if (isSelected)
              Icon(
                Icons.check_circle,
                color: Color(character.color),
                size: 28,
              ),
          ],
        ),
      ),
    );
  }
}
