import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/api/api_client.dart';
import '../../core/theme/app_theme.dart';
import '../auth/providers/auth_provider.dart';

class OnboardingPage extends ConsumerStatefulWidget {
  const OnboardingPage({super.key});

  @override
  ConsumerState<OnboardingPage> createState() => _OnboardingPageState();
}

class _OnboardingPageState extends ConsumerState<OnboardingPage> {
  final _pageController = PageController();
  int _currentPage = 0;

  @override
  void dispose() {
    _pageController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Stack(
        children: [
          Container(
            decoration: const BoxDecoration(
              gradient: LinearGradient(
                begin: Alignment.topCenter,
                end: Alignment.bottomCenter,
                colors: [Color(0xFF0F0F1A), Color(0xFF0A0A0F)],
              ),
            ),
          ),
          Column(
            children: [
              const SizedBox(height: 60),
              _buildHeader(),
              Expanded(
                child: PageView(
                  controller: _pageController,
                  onPageChanged: (page) => setState(() => _currentPage = page),
                  children: [
                    _buildWelcomePage(),
                    _buildAuthPage(),
                    _buildCharacterSelectPage(),
                  ],
                ),
              ),
              _buildBottomBar(),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildHeader() {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 24),
      child: Column(
        children: [
          Container(
            width: 80,
            height: 80,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              gradient: RadialGradient(
                colors: [
                  AppTheme.spiritGlow.withOpacity(0.6),
                  AppTheme.spiritGlow.withOpacity(0.1),
                  Colors.transparent,
                ],
                stops: const [0.3, 0.7, 1.0],
              ),
            ),
            child: const Icon(Icons.auto_awesome, size: 36, color: AppTheme.spiritGlow),
          ),
          const SizedBox(height: 16),
          const Text(
            '灵伴',
            style: TextStyle(
              fontSize: 28,
              fontWeight: FontWeight.bold,
              color: AppTheme.primaryColor,
              letterSpacing: 8,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            '被 AI 惦记的感觉',
            style: TextStyle(
              fontSize: 16,
              color: AppTheme.primaryColor.withOpacity(0.6),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildWelcomePage() {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 32),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          _buildFeatureItem(
            icon: Icons.chat_bubble_outline,
            title: '专属 AI 伙伴',
            description: '傲娇银月、睿智巴巴塔、贱萌黑皇，选择你的灵伴',
          ),
          const SizedBox(height: 32),
          _buildFeatureItem(
            icon: Icons.favorite_outline,
            title: '长期记忆',
            description: '记住你们的每一次对话，越聊越懂你',
          ),
          const SizedBox(height: 32),
          _buildFeatureItem(
            icon: Icons.notifications_active_outlined,
            title: '主动关怀',
            description: '不只是等你说话，TA 会主动找你聊天',
          ),
        ],
      ),
    );
  }

  Widget _buildFeatureItem({
    required IconData icon,
    required String title,
    required String description,
  }) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Container(
          width: 48,
          height: 48,
          decoration: BoxDecoration(
            color: AppTheme.spiritGlow.withOpacity(0.1),
            borderRadius: BorderRadius.circular(12),
            border: Border.all(
              color: AppTheme.spiritGlow.withOpacity(0.2),
              width: 0.5,
            ),
          ),
          child: Icon(icon, color: AppTheme.spiritGlow, size: 24),
        ),
        const SizedBox(width: 16),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                title,
                style: const TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.w600,
                  color: AppTheme.primaryColor,
                ),
              ),
              const SizedBox(height: 4),
              Text(
                description,
                style: TextStyle(
                  fontSize: 14,
                  color: AppTheme.primaryColor.withOpacity(0.5),
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }

  // 登录/注册页面
  Widget _buildAuthPage() {
    return const _AuthForm();
  }

  Widget _buildCharacterSelectPage() {
    final authState = ref.watch(authStateProvider);
    if (!authState.isAuthenticated) {
      return Center(
        child: Text(
          '请先登录',
          style: TextStyle(color: AppTheme.primaryColor.withOpacity(0.5)),
        ),
      );
    }

    return FutureBuilder(
      future: apiClient.getCharacters(),
      builder: (context, snapshot) {
        if (snapshot.connectionState == ConnectionState.waiting) {
          return const Center(child: CircularProgressIndicator());
        }
        if (snapshot.hasError) {
          return Center(
            child: Text(
              '加载失败: ${snapshot.error}',
              style: const TextStyle(color: Colors.red),
            ),
          );
        }

        final characters = List<Map<String, dynamic>>.from(snapshot.data?.data ?? []);

        return Padding(
          padding: const EdgeInsets.symmetric(horizontal: 24),
          child: Column(
            children: [
              const SizedBox(height: 24),
              const Text(
                '选择你的灵伴',
                style: TextStyle(
                  fontSize: 20,
                  fontWeight: FontWeight.w600,
                  color: AppTheme.primaryColor,
                ),
              ),
              const SizedBox(height: 8),
              Text(
                'TA 会陪你聊天，记住你的一切',
                style: TextStyle(
                  fontSize: 14,
                  color: AppTheme.primaryColor.withOpacity(0.5),
                ),
              ),
              const SizedBox(height: 24),
              Expanded(
                child: ListView.builder(
                  itemCount: characters.length,
                  itemBuilder: (context, index) =>
                      _buildCharacterCard(characters[index]),
                ),
              ),
            ],
          ),
        );
      },
    );
  }

  Widget _buildCharacterCard(Map<String, dynamic> char) {
    final color = Color(char['color'] ?? 0xFF34D399);

    return GestureDetector(
      onTap: () => _onCharacterSelected(char['id']),
      child: Container(
        margin: const EdgeInsets.only(bottom: 16),
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: AppTheme.cardColor,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(
            color: AppTheme.primaryColor.withOpacity(0.1),
            width: 0.5,
          ),
        ),
        child: Row(
          children: [
            Container(
              width: 56,
              height: 56,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                gradient: RadialGradient(
                  colors: [color.withOpacity(0.4), color.withOpacity(0.1)],
                ),
                border: Border.all(color: color.withOpacity(0.3), width: 1),
              ),
              child: Icon(Icons.auto_awesome, color: color, size: 24),
            ),
            const SizedBox(width: 16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    char['name'] ?? '',
                    style: const TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.w600,
                      color: AppTheme.primaryColor,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    '来自《${char['source'] ?? ''}》',
                    style: TextStyle(
                      fontSize: 12,
                      color: AppTheme.primaryColor.withOpacity(0.4),
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    char['description'] ?? '',
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                      fontSize: 13,
                      color: AppTheme.primaryColor.withOpacity(0.6),
                    ),
                  ),
                ],
              ),
            ),
            Icon(
              Icons.chevron_right,
              color: AppTheme.primaryColor.withOpacity(0.3),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildBottomBar() {
    return Padding(
      padding: const EdgeInsets.fromLTRB(24, 16, 24, 32),
      child: Row(
        children: [
          // 指示器
          Row(
            children: List.generate(3, (index) {
              final isActive = index == _currentPage;
              return Container(
                width: isActive ? 24 : 8,
                height: 8,
                margin: const EdgeInsets.only(right: 4),
                decoration: BoxDecoration(
                  color: isActive
                      ? AppTheme.spiritGlow
                      : AppTheme.primaryColor.withOpacity(0.2),
                  borderRadius: BorderRadius.circular(4),
                ),
              );
            }),
          ),
          const Spacer(),
          // 按钮
          if (_currentPage < 2)
            ElevatedButton(
              onPressed: () {
                _pageController.nextPage(
                  duration: const Duration(milliseconds: 300),
                  curve: Curves.easeInOut,
                );
              },
              style: ElevatedButton.styleFrom(
                backgroundColor: AppTheme.spiritGlow,
                foregroundColor: Colors.black,
              ),
              child: const Text('开始'),
            )
          else
            ElevatedButton(
              onPressed: () => _pageController.previousPage(
                duration: const Duration(milliseconds: 300),
                curve: Curves.easeInOut,
              ),
              style: ElevatedButton.styleFrom(
                backgroundColor: AppTheme.primaryColor.withOpacity(0.1),
                foregroundColor: AppTheme.primaryColor,
              ),
              child: const Text('返回'),
            ),
        ],
      ),
    );
  }

  Future<void> _onCharacterSelected(String characterId) async {
    final authNotifier = ref.read(authProvider.notifier);
    try {
      await authNotifier.selectCharacter(characterId);
      if (mounted) context.go('/home');
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('选择失败: $e')),
        );
      }
    }
  }
}

// 登录/注册表单
class _AuthForm extends ConsumerStatefulWidget {
  const _AuthForm();

  @override
  ConsumerState<_AuthForm> createState() => _AuthFormState();
}

class _AuthFormState extends ConsumerState<_AuthForm> {
  final _phoneController = TextEditingController();
  final _passwordController = TextEditingController();
  final _nicknameController = TextEditingController();
  bool _isLogin = true;
  bool _isLoading = false;

  @override
  void dispose() {
    _phoneController.dispose();
    _passwordController.dispose();
    _nicknameController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.symmetric(horizontal: 32),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const SizedBox(height: 40),
          // 切换标签
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              _buildTab('登录', _isLogin),
              const SizedBox(width: 24),
              _buildTab('注册', !_isLogin),
            ],
          ),
          const SizedBox(height: 32),
          // 手机号
          TextField(
            controller: _phoneController,
            keyboardType: TextInputType.phone,
            style: const TextStyle(color: AppTheme.primaryColor),
            decoration: InputDecoration(
              hintText: '手机号',
              hintStyle: TextStyle(color: AppTheme.primaryColor.withOpacity(0.3)),
              prefixIcon: Icon(Icons.phone_outlined, color: AppTheme.primaryColor.withOpacity(0.5)),
              filled: true,
              fillColor: AppTheme.cardColor,
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(12),
                borderSide: BorderSide.none,
              ),
            ),
          ),
          const SizedBox(height: 16),
          // 昵称（注册时显示）
          if (!_isLogin) ...[
            TextField(
              controller: _nicknameController,
              style: const TextStyle(color: AppTheme.primaryColor),
              decoration: InputDecoration(
                hintText: '昵称',
                hintStyle: TextStyle(color: AppTheme.primaryColor.withOpacity(0.3)),
                prefixIcon: Icon(Icons.person_outline, color: AppTheme.primaryColor.withOpacity(0.5)),
                filled: true,
                fillColor: AppTheme.cardColor,
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(12),
                  borderSide: BorderSide.none,
                ),
              ),
            ),
            const SizedBox(height: 16),
          ],
          // 密码
          TextField(
            controller: _passwordController,
            obscureText: true,
            style: const TextStyle(color: AppTheme.primaryColor),
            decoration: InputDecoration(
              hintText: '密码',
              hintStyle: TextStyle(color: AppTheme.primaryColor.withOpacity(0.3)),
              prefixIcon: Icon(Icons.lock_outline, color: AppTheme.primaryColor.withOpacity(0.5)),
              filled: true,
              fillColor: AppTheme.cardColor,
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(12),
                borderSide: BorderSide.none,
              ),
            ),
          ),
          const SizedBox(height: 24),
          // 提交按钮
          SizedBox(
            width: double.infinity,
            height: 48,
            child: ElevatedButton(
              onPressed: _isLoading ? null : _submit,
              style: ElevatedButton.styleFrom(
                backgroundColor: AppTheme.spiritGlow,
                foregroundColor: Colors.black,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(24),
                ),
              ),
              child: _isLoading
                  ? const SizedBox(
                      width: 20,
                      height: 20,
                      child: CircularProgressIndicator(strokeWidth: 2, color: Colors.black),
                    )
                  : Text(_isLogin ? '登录' : '注册'),
            ),
          ),
          const SizedBox(height: 16),
          TextButton(
            onPressed: () => setState(() => _isLogin = !_isLogin),
            child: Text(
              _isLogin ? '没有账号？去注册' : '已有账号？去登录',
              style: TextStyle(
                color: AppTheme.primaryColor.withOpacity(0.5),
                fontSize: 13,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildTab(String label, bool isActive) {
    return GestureDetector(
      onTap: () => setState(() => _isLogin = label == '登录'),
      child: Column(
        children: [
          Text(
            label,
            style: TextStyle(
              fontSize: 18,
              fontWeight: isActive ? FontWeight.w600 : FontWeight.normal,
              color: isActive
                  ? AppTheme.primaryColor
                  : AppTheme.primaryColor.withOpacity(0.4),
            ),
          ),
          const SizedBox(height: 4),
          Container(
            width: 24,
            height: 2,
            decoration: BoxDecoration(
              color: isActive ? AppTheme.spiritGlow : Colors.transparent,
              borderRadius: BorderRadius.circular(1),
            ),
          ),
        ],
      ),
    );
  }

  Future<void> _submit() async {
    final phone = _phoneController.text.trim();
    final password = _passwordController.text.trim();
    final nickname = _nicknameController.text.trim();

    if (phone.isEmpty || password.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('请填写手机号和密码')),
      );
      return;
    }
    if (!_isLogin && nickname.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('请填写昵称')),
      );
      return;
    }

    setState(() => _isLoading = true);
    final authNotifier = ref.read(authProvider.notifier);

    bool success;
    if (_isLogin) {
      success = await authNotifier.login(phone: phone, password: password);
    } else {
      success = await authNotifier.register(
        phone: phone,
        password: password,
        nickname: nickname,
      );
    }

    if (mounted) {
      setState(() => _isLoading = false);
      if (!success) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(_isLogin ? '登录失败，请检查账号密码' : '注册失败，请重试')),
        );
      }
    }
  }
}
