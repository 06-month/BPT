import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'app_colors.dart';

class AppTheme {
  static ThemeData get lightTheme => _build(Brightness.light);
  static ThemeData get darkTheme => _build(Brightness.dark);

  static ThemeData _build(Brightness brightness) {
    final isDark = brightness == Brightness.dark;
    final bg = isDark ? AppColors.darkBackground : AppColors.lightBackground;
    final surface = isDark ? AppColors.darkSurface : AppColors.lightSurface;
    final card = isDark ? AppColors.darkCard : AppColors.lightCard;
    final textPrimary =
        isDark ? AppColors.darkTextPrimary : AppColors.lightTextPrimary;
    final textSecondary =
        isDark ? AppColors.darkTextSecondary : AppColors.lightTextSecondary;
    final divider = isDark ? AppColors.darkDivider : AppColors.lightDivider;
    final inputFill =
        isDark ? AppColors.darkInputFill : AppColors.lightInputFill;

    final base = isDark ? ThemeData.dark() : ThemeData.light();

    // Boosted text theme for readability
    final textTheme = GoogleFonts.interTextTheme(base.textTheme).copyWith(
      displayLarge: GoogleFonts.inter(fontSize: 57, fontWeight: FontWeight.w800, color: textPrimary),
      displayMedium: GoogleFonts.inter(fontSize: 45, fontWeight: FontWeight.w700, color: textPrimary),
      displaySmall: GoogleFonts.inter(fontSize: 36, fontWeight: FontWeight.w700, color: textPrimary),
      headlineLarge: GoogleFonts.inter(fontSize: 32, fontWeight: FontWeight.w800, color: textPrimary),
      headlineMedium: GoogleFonts.inter(fontSize: 28, fontWeight: FontWeight.w700, color: textPrimary),
      headlineSmall: GoogleFonts.inter(fontSize: 26, fontWeight: FontWeight.w700, color: textPrimary),
      titleLarge: GoogleFonts.inter(fontSize: 22, fontWeight: FontWeight.w800, color: textPrimary),
      titleMedium: GoogleFonts.inter(fontSize: 18, fontWeight: FontWeight.w700, color: textPrimary),
      titleSmall: GoogleFonts.inter(fontSize: 16, fontWeight: FontWeight.w600, color: textPrimary),
      bodyLarge: GoogleFonts.inter(fontSize: 17, fontWeight: FontWeight.w500, color: textPrimary),
      bodyMedium: GoogleFonts.inter(fontSize: 15, fontWeight: FontWeight.w500, color: textPrimary),
      bodySmall: GoogleFonts.inter(fontSize: 13, fontWeight: FontWeight.w500, color: textSecondary),
      labelLarge: GoogleFonts.inter(fontSize: 15, fontWeight: FontWeight.w600, color: textPrimary),
      labelMedium: GoogleFonts.inter(fontSize: 13, fontWeight: FontWeight.w600, color: textPrimary),
      labelSmall: GoogleFonts.inter(fontSize: 12, fontWeight: FontWeight.w500, color: textSecondary),
    );

    return ThemeData(
      useMaterial3: true,
      brightness: brightness,
      colorScheme: ColorScheme(
        brightness: brightness,
        primary: AppColors.primary,
        onPrimary: Colors.white,
        secondary: AppColors.secondary,
        onSecondary: Colors.white,
        error: AppColors.error,
        onError: Colors.white,
        surface: surface,
        onSurface: textPrimary,
        surfaceContainerHighest: card,
      ),
      scaffoldBackgroundColor: bg,
      textTheme: textTheme,
      appBarTheme: AppBarTheme(
        backgroundColor: surface,
        foregroundColor: textPrimary,
        elevation: 0,
        centerTitle: true,
        surfaceTintColor: Colors.transparent,
        titleTextStyle: GoogleFonts.inter(
          fontSize: 20,
          fontWeight: FontWeight.w700,
          color: textPrimary,
        ),
        iconTheme: const IconThemeData(size: 26),
      ),
      cardTheme: CardTheme(
        color: card,
        elevation: 0,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        margin: EdgeInsets.zero,
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: AppColors.primary,
          foregroundColor: Colors.white,
          elevation: 0,
          minimumSize: const Size(double.infinity, 56),
          shape:
              RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
          textStyle: GoogleFonts.inter(
            fontSize: 17,
            fontWeight: FontWeight.w700,
            letterSpacing: 0.3,
          ),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: AppColors.primary,
          side: const BorderSide(color: AppColors.primary, width: 1.5),
          minimumSize: const Size(double.infinity, 56),
          shape:
              RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
          textStyle: GoogleFonts.inter(
            fontSize: 17,
            fontWeight: FontWeight.w700,
          ),
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: inputFill,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: BorderSide.none,
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: BorderSide(color: divider, width: 1),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: const BorderSide(color: AppColors.primary, width: 2),
        ),
        errorBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: const BorderSide(color: AppColors.error, width: 1.5),
        ),
        contentPadding:
            const EdgeInsets.symmetric(horizontal: 16, vertical: 18),
        hintStyle: GoogleFonts.inter(
          fontSize: 15,
          color: textSecondary,
          fontWeight: FontWeight.w400,
        ),
        labelStyle: GoogleFonts.inter(fontSize: 15, color: textSecondary),
      ),
      dividerTheme: DividerThemeData(color: divider, thickness: 1),
      bottomNavigationBarTheme: BottomNavigationBarThemeData(
        backgroundColor: surface,
        selectedItemColor: AppColors.primary,
        unselectedItemColor: textSecondary,
        elevation: 0,
        type: BottomNavigationBarType.fixed,
        selectedLabelStyle:
            GoogleFonts.inter(fontSize: 13, fontWeight: FontWeight.w700),
        unselectedLabelStyle:
            GoogleFonts.inter(fontSize: 13, fontWeight: FontWeight.w500),
      ),
      chipTheme: ChipThemeData(
        backgroundColor: inputFill,
        labelStyle: GoogleFonts.inter(fontSize: 14, color: textPrimary),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
      ),
      tabBarTheme: TabBarTheme(
        labelColor: AppColors.primary,
        unselectedLabelColor: textSecondary,
        indicatorColor: AppColors.primary,
        labelStyle:
            GoogleFonts.inter(fontSize: 15, fontWeight: FontWeight.w700),
        unselectedLabelStyle:
            GoogleFonts.inter(fontSize: 15, fontWeight: FontWeight.w500),
      ),
      iconTheme: const IconThemeData(size: 26),
    );
  }
}
