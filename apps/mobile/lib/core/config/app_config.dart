import 'package:flutter/foundation.dart' show kIsWeb, kDebugMode;

class AppConfig {
  static String get baseUrl {
    // 开发环境
    if (kDebugMode) {
      if (kIsWeb) return 'http://localhost:8000';
      // Android 模拟器用 10.0.2.2 访问宿主机
      return 'http://10.0.2.2:8000';
    }
    // 生产环境 - 部署时替换
    return 'https://api.lingban.app';
  }
}
