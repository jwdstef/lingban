import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../../core/api/api_client.dart';

class AuthState {
  final bool isAuthenticated;
  final bool isLoading;
  final String? userId;
  final String? nickname;
  final String? selectedCharacterId;

  const AuthState({
    this.isAuthenticated = false,
    this.isLoading = false,
    this.userId,
    this.nickname,
    this.selectedCharacterId,
  });

  AuthState copyWith({
    bool? isAuthenticated,
    bool? isLoading,
    String? userId,
    String? nickname,
    String? selectedCharacterId,
  }) {
    return AuthState(
      isAuthenticated: isAuthenticated ?? this.isAuthenticated,
      isLoading: isLoading ?? this.isLoading,
      userId: userId ?? this.userId,
      nickname: nickname ?? this.nickname,
      selectedCharacterId: selectedCharacterId ?? this.selectedCharacterId,
    );
  }
}

class AuthNotifier extends StateNotifier<AuthState> {
  AuthNotifier() : super(const AuthState()) {
    _checkAuth();
    // 注册 401 回调
    apiClient.onUnauthorized = () {
      state = const AuthState();
    };
  }

  Future<void> _checkAuth() async {
    final prefs = await SharedPreferences.getInstance();
    final token = prefs.getString('access_token');
    if (token != null) {
      try {
        final response = await apiClient.getMe();
        final data = response.data;
        state = state.copyWith(
          isAuthenticated: true,
          userId: data['id'],
          nickname: data['nickname'],
          selectedCharacterId: data['selected_character_id'],
        );
      } catch (e) {
        await prefs.remove('access_token');
      }
    }
  }

  Future<bool> register({
    required String nickname,
    required String password,
    String? phone,
    String? email,
  }) async {
    state = state.copyWith(isLoading: true);
    try {
      final response = await apiClient.register({
        'nickname': nickname,
        'password': password,
        if (phone != null && phone.isNotEmpty) 'phone': phone,
        if (email != null && email.isNotEmpty) 'email': email,
      });
      final token = response.data['access_token'];
      await _saveToken(token);
      await _checkAuth();
      return true;
    } catch (e) {
      state = state.copyWith(isLoading: false);
      return false;
    }
  }

  Future<bool> login({
    required String password,
    String? phone,
    String? email,
  }) async {
    state = state.copyWith(isLoading: true);
    try {
      final response = await apiClient.login({
        'password': password,
        if (phone != null && phone.isNotEmpty) 'phone': phone,
        if (email != null && email.isNotEmpty) 'email': email,
      });
      final token = response.data['access_token'];
      await _saveToken(token);
      await _checkAuth();
      return true;
    } catch (e) {
      state = state.copyWith(isLoading: false);
      return false;
    }
  }

  Future<void> logout() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove('access_token');
    state = const AuthState();
  }

  Future<void> selectCharacter(String characterId) async {
    try {
      await apiClient.selectCharacter(characterId);
      state = state.copyWith(selectedCharacterId: characterId);
    } catch (e) {
      rethrow;
    }
  }

  Future<void> _saveToken(String token) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('access_token', token);
  }
}

final authProvider = StateNotifierProvider<AuthNotifier, AuthState>(
  (ref) => AuthNotifier(),
);

final authStateProvider = authProvider.select((state) => state);
