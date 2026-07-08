import 'package:flutter/material.dart';
import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:lingban_mobile/core/theme/app_theme.dart';
import 'package:lingban_mobile/features/settings/about_page.dart';
import 'package:lingban_mobile/features/settings/subscription_page.dart';

void main() {
  test('placeholder test', () {
    expect(1 + 1, 2);
  });

  testWidgets('subscription page shows MVP plans', (tester) async {
    await tester.pumpWidget(
      MaterialApp(
        theme: AppTheme.darkTheme,
        home: SubscriptionPage(
          loadSubscription: () async => _freeSubscription(),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('订阅管理'), findsOneWidget);
    expect(find.text('基础版'), findsOneWidget);
    expect(find.text('进阶版'), findsOneWidget);

    await tester.drag(find.byType(ListView), const Offset(0, -420));
    await tester.pumpAndSettle();

    expect(find.text('专业版'), findsOneWidget);
  });

  testWidgets('subscription page creates order and launches WeChat payment',
      (tester) async {
    String? createdPlan;
    Map<String, dynamic>? launchedParams;

    await tester.pumpWidget(
      MaterialApp(
        theme: AppTheme.darkTheme,
        home: SubscriptionPage(
          loadSubscription: () async => _freeSubscription(),
          createSubscription: (plan) async {
            createdPlan = plan;
            return {
              'order_id': 'order-1',
              'payment_params': {
                'appid': 'wx-test-app',
                'partnerid': '1900000001',
                'prepayid': 'wx-prepay-id',
                'package': 'Sign=WXPay',
                'noncestr': 'nonce',
                'timestamp': '1780000000',
                'sign': 'signature',
                'sign_type': 'RSA',
              },
            };
          },
          launchWechatPayment: (params) async {
            launchedParams = params;
            return const WechatPaymentLaunchResult(
              launched: true,
              message: '支付请求已提交，请完成微信支付后返回刷新订阅状态。',
            );
          },
        ),
      ),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.text('立即升级').first);
    await tester.pumpAndSettle();

    expect(createdPlan, 'basic');
    expect(launchedParams?['prepayid'], 'wx-prepay-id');
    expect(find.text('支付请求已提交，请完成微信支付后返回刷新订阅状态。'), findsOneWidget);
  });

  testWidgets('subscription page reports unconfigured payment provider',
      (tester) async {
    final requestOptions = RequestOptions(path: '/api/v1/subscription/create');

    await tester.pumpWidget(
      MaterialApp(
        theme: AppTheme.darkTheme,
        home: SubscriptionPage(
          loadSubscription: () async => _freeSubscription(),
          createSubscription: (_) async {
            throw DioException(
              requestOptions: requestOptions,
              response: Response(
                requestOptions: requestOptions,
                statusCode: 503,
                data: {
                  'detail': {'code': 'payment_provider_not_configured'},
                },
              ),
            );
          },
        ),
      ),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.text('立即升级').first);
    await tester.pumpAndSettle();

    expect(find.text('支付通道暂未配置，升级入口暂时不可用。'), findsOneWidget);
  });

  testWidgets('about page states the AI identity boundary', (tester) async {
    await tester.pumpWidget(
      MaterialApp(
        theme: AppTheme.darkTheme,
        home: const AboutPage(),
      ),
    );

    expect(find.text('关于灵伴'), findsOneWidget);
    expect(find.textContaining('我是 AI'), findsOneWidget);
    expect(find.textContaining('不能替代真实的人际关系'), findsOneWidget);
  });

  testWidgets('legal pages expose privacy and terms content', (tester) async {
    await tester.pumpWidget(
      MaterialApp(
        theme: AppTheme.darkTheme,
        home: const LegalPage(document: LegalDocument.privacy),
      ),
    );
    expect(find.text('隐私政策'), findsOneWidget);
    expect(find.text('你的控制权'), findsOneWidget);

    await tester.pumpWidget(
      MaterialApp(
        theme: AppTheme.darkTheme,
        home: const LegalPage(document: LegalDocument.terms),
      ),
    );
    expect(find.text('用户协议'), findsOneWidget);
    expect(find.text('服务定位'), findsOneWidget);
  });
}

Map<String, dynamic> _freeSubscription() => {
      'plan': 'free',
      'status': 'active',
      'quota': {
        'chat_daily': {
          'limit': 20,
          'used': 0,
          'remaining': 20,
        },
      },
    };
