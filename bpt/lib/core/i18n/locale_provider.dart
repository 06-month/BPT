import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'app_strings.dart';

// 'en' or 'ko'
final selectedLanguageProvider = StateProvider<String>((ref) => 'ko');

final appStringsProvider = Provider<AppStrings>((ref) {
  final lang = ref.watch(selectedLanguageProvider);
  return lang == 'ko' ? AppStrings.ko : AppStrings.en;
});

final appLocaleProvider = Provider<Locale>((ref) {
  final lang = ref.watch(selectedLanguageProvider);
  return Locale(lang);
});
