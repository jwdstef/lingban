import 'package:flutter/material.dart';

class AppTheme {
  // 原型的紫银暗色主题
  static const String fontFamily = 'NotoSansSC';

  static const Color primaryColor = Color(0xFFF8FAFC);
  static const Color accentColor = Color(0xFFF472B6);
  static const Color backgroundColor = Color(0xFF080515);
  static const Color surfaceColor = Color(0xFF0F0B1E);
  static const Color cardColor = Color(0xFF1E143C);
  static const Color textPrimary = Color(0xFFF8FAFC);
  static const Color textSecondary = Color(0xFF94A3B8);
  static const Color spiritGlow = Color(0xFFA78BFA);
  static const Color emotionCalm = Color(0xFFA78BFA);
  static const Color emotionHappy = Color(0xFFFBBF24);
  static const Color emotionWorried = Color(0xFFA78BFA);
  static const Color emotionExcited = Color(0xFFF472B6);
  static const Color emotionThinking = Color(0xFF22D3EE);

  static ThemeData get darkTheme => ThemeData(
        brightness: Brightness.dark,
        fontFamily: fontFamily,
        primaryColor: primaryColor,
        scaffoldBackgroundColor: backgroundColor,
        colorScheme: const ColorScheme.dark(
          primary: primaryColor,
          secondary: accentColor,
          surface: surfaceColor,
        ),
        appBarTheme: const AppBarTheme(
          backgroundColor: Colors.transparent,
          elevation: 0,
          centerTitle: true,
          titleTextStyle: TextStyle(
            color: textPrimary,
            fontFamily: fontFamily,
            fontSize: 18,
            fontWeight: FontWeight.w600,
          ),
          iconTheme: IconThemeData(color: primaryColor),
        ),
        cardTheme: CardThemeData(
          color: cardColor,
          elevation: 0,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(16),
          ),
        ),
        elevatedButtonTheme: ElevatedButtonThemeData(
          style: ElevatedButton.styleFrom(
            backgroundColor: primaryColor,
            foregroundColor: Colors.black,
            elevation: 0,
            padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 14),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(28),
            ),
            textStyle: const TextStyle(
              fontFamily: fontFamily,
              fontSize: 16,
              fontWeight: FontWeight.w600,
            ),
          ),
        ),
        textTheme: const TextTheme(
          displayLarge: TextStyle(
            fontFamily: fontFamily,
            fontSize: 32,
            fontWeight: FontWeight.bold,
            color: textPrimary,
          ),
          headlineMedium: TextStyle(
            fontFamily: fontFamily,
            fontSize: 24,
            fontWeight: FontWeight.w600,
            color: textPrimary,
          ),
          titleLarge: TextStyle(
            fontFamily: fontFamily,
            fontSize: 20,
            fontWeight: FontWeight.w600,
            color: textPrimary,
          ),
          titleMedium: TextStyle(
            fontFamily: fontFamily,
            fontSize: 16,
            fontWeight: FontWeight.w500,
            color: textPrimary,
          ),
          bodyLarge: TextStyle(fontFamily: fontFamily, color: textPrimary),
          bodyMedium: TextStyle(fontFamily: fontFamily, color: textSecondary),
          bodySmall: TextStyle(
            fontFamily: fontFamily,
            color: textSecondary,
            fontSize: 12,
          ),
        ),
        inputDecorationTheme: InputDecorationTheme(
          filled: true,
          fillColor: cardColor,
          border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(12),
            borderSide: BorderSide.none,
          ),
          contentPadding: const EdgeInsets.symmetric(
            horizontal: 16,
            vertical: 14,
          ),
          hintStyle: const TextStyle(
            fontFamily: fontFamily,
            color: textSecondary,
          ),
        ),
      );
}
