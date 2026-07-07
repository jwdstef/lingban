import 'package:flutter/foundation.dart' show kDebugMode, kIsWeb;

class AppConfig {
  static const _configuredBaseUrl = String.fromEnvironment('API_BASE_URL');

  static String get baseUrl {
    if (_configuredBaseUrl.isNotEmpty) return _configuredBaseUrl;

    if (kDebugMode) {
      if (kIsWeb) return 'http://localhost:8000';
      return 'http://10.0.2.2:8000';
    }

    return 'https://api.lingban.app';
  }
}
