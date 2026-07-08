import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../core/api/api_client.dart';
import '../../core/theme/app_theme.dart';

typedef SubscriptionLoader = Future<Map<String, dynamic>> Function();
typedef SubscriptionCreator = Future<Map<String, dynamic>> Function(String plan);
typedef WechatPaymentLauncher = Future<WechatPaymentLaunchResult> Function(
  Map<String, dynamic> paymentParams,
);

class WechatPaymentLaunchResult {
  final bool launched;
  final String message;

  const WechatPaymentLaunchResult({
    required this.launched,
    required this.message,
  });
}

class WechatPaymentBridge {
  static const MethodChannel _channel = MethodChannel('lingban/wechat_pay');

  static Future<WechatPaymentLaunchResult> launch(
    Map<String, dynamic> paymentParams,
  ) async {
    try {
      final launched = await _channel.invokeMethod<bool>(
            'requestPayment',
            paymentParams,
          ) ??
          false;
      return WechatPaymentLaunchResult(
        launched: launched,
        message: launched
            ? '支付请求已提交，请完成微信支付后返回刷新订阅状态。'
            : '微信支付未完成，请稍后查看订阅状态。',
      );
    } on MissingPluginException {
      return const WechatPaymentLaunchResult(
        launched: false,
        message: '已创建支付订单，当前客户端暂不支持拉起微信支付。',
      );
    } on PlatformException catch (error) {
      if (error.code == 'wechat_pay_sdk_not_configured') {
        return const WechatPaymentLaunchResult(
          launched: false,
          message: '已创建支付订单，当前客户端暂不支持拉起微信支付。',
        );
      }
      return const WechatPaymentLaunchResult(
        launched: false,
        message: '微信支付拉起失败，请稍后重试。',
      );
    } catch (_) {
      return const WechatPaymentLaunchResult(
        launched: false,
        message: '微信支付拉起失败，请稍后重试。',
      );
    }
  }
}

class SubscriptionPage extends StatefulWidget {
  final SubscriptionLoader? loadSubscription;
  final SubscriptionCreator? createSubscription;
  final WechatPaymentLauncher? launchWechatPayment;

  const SubscriptionPage({
    super.key,
    this.loadSubscription,
    this.createSubscription,
    this.launchWechatPayment,
  });

  @override
  State<SubscriptionPage> createState() => _SubscriptionPageState();
}

class _SubscriptionPageState extends State<SubscriptionPage> {
  Map<String, dynamic>? _subscription;
  bool _isLoading = true;
  bool _hasError = false;
  String? _pendingPlan;
  String? _paymentMessage;
  bool _paymentIsError = false;

  @override
  void initState() {
    super.initState();
    _loadSubscription();
  }

  Future<void> _loadSubscription() async {
    try {
      final subscription = await _loadSubscriptionData();
      if (!mounted) return;
      setState(() {
        _subscription = subscription;
        _isLoading = false;
        _hasError = false;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _isLoading = false;
        _hasError = true;
      });
    }
  }

  Future<Map<String, dynamic>> _loadSubscriptionData() async {
    if (widget.loadSubscription != null) {
      return widget.loadSubscription!();
    }
    final response = await apiClient.getSubscription();
    return Map<String, dynamic>.from(response.data ?? {});
  }

  Future<Map<String, dynamic>> _createSubscription(String plan) async {
    if (widget.createSubscription != null) {
      return widget.createSubscription!(plan);
    }
    final response = await apiClient.createSubscription(plan);
    return Map<String, dynamic>.from(response.data ?? {});
  }

  Future<void> _startCheckout(String plan) async {
    setState(() {
      _pendingPlan = plan;
      _paymentMessage = null;
      _paymentIsError = false;
    });

    try {
      final order = await _createSubscription(plan);
      final paymentParams = Map<String, dynamic>.from(
        (order['payment_params'] as Map?) ?? {},
      );
      if (paymentParams.isEmpty) {
        throw StateError('Missing WeChat payment params');
      }
      final launcher = widget.launchWechatPayment ?? WechatPaymentBridge.launch;
      final result = await launcher(paymentParams);
      if (!mounted) return;
      setState(() {
        _paymentMessage = result.message;
        _paymentIsError = !result.launched;
      });
      await _loadSubscription();
    } on DioException catch (error) {
      if (!mounted) return;
      setState(() {
        _paymentMessage = _paymentErrorMessage(error);
        _paymentIsError = true;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _paymentMessage = '支付请求失败，请稍后重试。';
        _paymentIsError = true;
      });
    } finally {
      if (mounted) {
        setState(() {
          _pendingPlan = null;
        });
      }
    }
  }

  String _paymentErrorMessage(DioException error) {
    final statusCode = error.response?.statusCode;
    final data = error.response?.data;
    final detail = data is Map ? data['detail'] : null;
    final code = detail is Map ? detail['code'] : null;
    if (statusCode == 503 || code == 'payment_provider_not_configured') {
      return '支付通道暂未配置，升级入口暂时不可用。';
    }
    if (statusCode == 502 || code == 'payment_provider_error') {
      return '支付服务暂时不可用，请稍后重试。';
    }
    return '支付请求失败，请稍后重试。';
  }

  @override
  Widget build(BuildContext context) {
    final currentPlan = (_subscription?['plan'] as String?) ?? 'free';

    return Scaffold(
      backgroundColor: Colors.transparent,
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.fromLTRB(16, 8, 16, 28),
          children: [
            const _SettingsBackHeader(title: '订阅管理'),
            const SizedBox(height: 18),
            _CurrentPlanBanner(
              subscription: _subscription,
              isLoading: _isLoading,
              hasError: _hasError,
              onRetry: _loadSubscription,
            ),
            if (_paymentMessage != null) ...[
              const SizedBox(height: 12),
              _PaymentNotice(
                message: _paymentMessage!,
                isError: _paymentIsError,
              ),
            ],
            const SizedBox(height: 18),
            _PlanCard(
              title: '基础版',
              price: '免费',
              description: '适合先确认你和伙伴是否合拍。',
              features: const [
                '1 个预制角色',
                '基础聊天和语音消息',
                '每日 1-2 次主动关怀',
                '近期记忆容量',
              ],
              isCurrent: currentPlan == 'free',
            ),
            const SizedBox(height: 12),
            _PlanCard(
              title: '进阶版',
              price: '¥29/月',
              description: '完整体验长期记忆和多角色陪伴。',
              features: const [
                '解锁 3 个官方角色',
                '深度长期记忆',
                '高质量语音回复',
                '情绪趋势报告',
              ],
              highlighted: true,
              isCurrent: currentPlan == 'basic',
              isBusy: _pendingPlan == 'basic',
              onUpgrade: currentPlan == 'basic'
                  ? null
                  : () => _startCheckout('basic'),
            ),
            const SizedBox(height: 12),
            _PlanCard(
              title: '专业版',
              price: '¥99/月',
              description: '为高需求陪伴场景保留的人工协作版本。',
              features: const [
                '包含进阶版全部能力',
                '真人专业支持入口',
                '定期陪伴方案复核',
                '重大状态变化提醒',
              ],
              isCurrent: currentPlan == 'pro',
              isBusy: _pendingPlan == 'pro',
              onUpgrade:
                  currentPlan == 'pro' ? null : () => _startCheckout('pro'),
            ),
            const SizedBox(height: 18),
            const _BillingNote(),
          ],
        ),
      ),
    );
  }
}

class _CurrentPlanBanner extends StatelessWidget {
  final Map<String, dynamic>? subscription;
  final bool isLoading;
  final bool hasError;
  final VoidCallback onRetry;

  const _CurrentPlanBanner({
    required this.subscription,
    required this.isLoading,
    required this.hasError,
    required this.onRetry,
  });

  @override
  Widget build(BuildContext context) {
    final plan = (subscription?['plan'] as String?) ?? 'free';
    final planName = _planName(plan);
    final chatQuota = (subscription?['quota'] as Map?)?['chat_daily'] as Map?;
    final limit = chatQuota?['limit'];
    final remaining = chatQuota?['remaining'];
    final subtitle = isLoading
        ? '正在同步订阅状态...'
        : hasError
            ? '订阅状态暂时同步失败，可稍后重试。'
            : remaining != null && limit != null
                ? '今日对话剩余 $remaining / $limit 次。'
                : '订阅状态已同步。';

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppTheme.cardColor,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: AppTheme.spiritGlow.withValues(alpha: 0.22),
          width: 0.8,
        ),
      ),
      child: Row(
        children: [
          Container(
            width: 42,
            height: 42,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: AppTheme.spiritGlow.withValues(alpha: 0.16),
            ),
            child: const Icon(
              Icons.workspace_premium_outlined,
              color: AppTheme.spiritGlow,
              size: 22,
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  '当前为$planName',
                  style: const TextStyle(
                    color: AppTheme.textPrimary,
                    fontSize: 16,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  subtitle,
                  style: const TextStyle(
                    color: AppTheme.textSecondary,
                    fontSize: 12,
                    height: 1.35,
                  ),
                ),
                if (hasError) ...[
                  const SizedBox(height: 8),
                  TextButton.icon(
                    onPressed: onRetry,
                    icon: const Icon(Icons.refresh, size: 16),
                    label: const Text('重试'),
                    style: TextButton.styleFrom(
                      foregroundColor: AppTheme.spiritGlow,
                      padding: EdgeInsets.zero,
                      minimumSize: const Size(0, 28),
                      tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                    ),
                  ),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }

  String _planName(String plan) {
    switch (plan) {
      case 'basic':
        return '进阶版';
      case 'pro':
        return '专业版';
      default:
        return '基础版';
    }
  }
}

class _PaymentNotice extends StatelessWidget {
  final String message;
  final bool isError;

  const _PaymentNotice({
    required this.message,
    required this.isError,
  });

  @override
  Widget build(BuildContext context) {
    final color = isError ? AppTheme.accentColor : AppTheme.spiritGlow;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: color.withValues(alpha: 0.28), width: 0.8),
      ),
      child: Row(
        children: [
          Icon(
            isError ? Icons.info_outline : Icons.check_circle_outline,
            color: color,
            size: 18,
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              message,
              style: const TextStyle(
                color: AppTheme.textPrimary,
                fontSize: 12,
                height: 1.35,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _PlanCard extends StatelessWidget {
  final String title;
  final String price;
  final String description;
  final List<String> features;
  final bool highlighted;
  final bool isCurrent;
  final bool isBusy;
  final VoidCallback? onUpgrade;

  const _PlanCard({
    required this.title,
    required this.price,
    required this.description,
    required this.features,
    this.highlighted = false,
    this.isCurrent = false,
    this.isBusy = false,
    this.onUpgrade,
  });

  @override
  Widget build(BuildContext context) {
    final borderColor = highlighted
        ? AppTheme.accentColor.withValues(alpha: 0.42)
        : AppTheme.primaryColor.withValues(alpha: 0.08);

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppTheme.cardColor,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: borderColor, width: highlighted ? 1.2 : 0.6),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      title,
                      style: const TextStyle(
                        color: AppTheme.textPrimary,
                        fontSize: 17,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    const SizedBox(height: 5),
                    Text(
                      description,
                      style: const TextStyle(
                        color: AppTheme.textSecondary,
                        fontSize: 12,
                        height: 1.35,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 10),
              Column(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  Text(
                    price,
                    style: TextStyle(
                      color: highlighted
                          ? AppTheme.accentColor
                          : AppTheme.textPrimary,
                      fontSize: 18,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  const SizedBox(height: 6),
                  if (isCurrent)
                    const _StatusChip(label: '当前方案')
                  else
                    _UpgradeButton(
                      highlighted: highlighted,
                      isBusy: isBusy,
                      onPressed: onUpgrade,
                    ),
                ],
              ),
            ],
          ),
          const SizedBox(height: 14),
          ...features.map(
            (feature) => Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: Row(
                children: [
                  Icon(
                    Icons.check_circle,
                    color: highlighted
                        ? AppTheme.accentColor
                        : AppTheme.spiritGlow.withValues(alpha: 0.72),
                    size: 16,
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      feature,
                      style: const TextStyle(
                        color: AppTheme.textPrimary,
                        fontSize: 13,
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

class _UpgradeButton extends StatelessWidget {
  final bool highlighted;
  final bool isBusy;
  final VoidCallback? onPressed;

  const _UpgradeButton({
    required this.highlighted,
    required this.isBusy,
    required this.onPressed,
  });

  @override
  Widget build(BuildContext context) {
    final foreground =
        highlighted ? const Color(0xFF140B22) : AppTheme.textPrimary;
    final background = highlighted
        ? AppTheme.accentColor
        : AppTheme.spiritGlow.withValues(alpha: 0.18);

    return SizedBox(
      height: 32,
      child: FilledButton.icon(
        onPressed: isBusy ? null : onPressed,
        icon: isBusy
            ? SizedBox(
                width: 13,
                height: 13,
                child: CircularProgressIndicator(
                  strokeWidth: 2,
                  valueColor: AlwaysStoppedAnimation<Color>(foreground),
                ),
              )
            : Icon(
                Icons.arrow_forward_rounded,
                size: 16,
                color: foreground,
              ),
        label: Text(isBusy ? '处理中' : '立即升级'),
        style: FilledButton.styleFrom(
          backgroundColor: background,
          foregroundColor: foreground,
          disabledBackgroundColor: background.withValues(alpha: 0.55),
          disabledForegroundColor: foreground.withValues(alpha: 0.62),
          padding: const EdgeInsets.symmetric(horizontal: 10),
          textStyle: const TextStyle(
            fontSize: 12,
            fontWeight: FontWeight.w700,
          ),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(999),
          ),
        ),
      ),
    );
  }
}

class _StatusChip extends StatelessWidget {
  final String label;

  const _StatusChip({required this.label});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: AppTheme.primaryColor.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(999),
      ),
      child: Text(
        label,
        style: TextStyle(
          color: AppTheme.primaryColor.withValues(alpha: 0.68),
          fontSize: 11,
        ),
      ),
    );
  }
}

class _BillingNote extends StatelessWidget {
  const _BillingNote();

  @override
  Widget build(BuildContext context) {
    return Text(
      '订阅制不按互动次数计费；产品会优先保护健康使用节奏，避免用连续打卡或时长奖励制造依赖。',
      style: TextStyle(
        color: AppTheme.primaryColor.withValues(alpha: 0.46),
        fontSize: 12,
        height: 1.5,
      ),
    );
  }
}

class _SettingsBackHeader extends StatelessWidget {
  final String title;

  const _SettingsBackHeader({required this.title});

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
