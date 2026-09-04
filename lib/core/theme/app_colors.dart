import 'package:flutter/material.dart';

class AppColors {
  // Primary – Teal (energy + professionalism)
  static const Color primary = Color(0xFF00C6AE);
  static const Color primaryDark = Color(0xFF009E8A);
  static const Color primaryLight = Color(0xFF4DD9C6);

  // Secondary – Vivid Orange accent
  static const Color secondary = Color(0xFFFF6B35);
  static const Color secondaryDark = Color(0xFFCC5228);
  static const Color secondaryLight = Color(0xFFFF9068);

  // ── Light Mode ──────────────────────────────────────────
  static const Color lightBackground = Color(0xFFF5F7FA);
  static const Color lightSurface = Color(0xFFFFFFFF);
  static const Color lightCard = Color(0xFFFFFFFF);
  static const Color lightTextPrimary = Color(0xFF1A1A2E);
  static const Color lightTextSecondary = Color(0xFF6B7280);
  static const Color lightDivider = Color(0xFFE5E7EB);
  static const Color lightInputFill = Color(0xFFF0F2F5);

  // ── Dark Mode ────────────────────────────────────────────
  static const Color darkBackground = Color(0xFF0F1117);
  static const Color darkSurface = Color(0xFF1A1D27);
  static const Color darkCard = Color(0xFF242838);
  static const Color darkTextPrimary = Color(0xFFF1F5F9);
  static const Color darkTextSecondary = Color(0xFF94A3B8);
  static const Color darkDivider = Color(0xFF2D3148);
  static const Color darkInputFill = Color(0xFF2A2D3E);

  // ── Semantic ─────────────────────────────────────────────
  static const Color success = Color(0xFF10B981);
  static const Color warning = Color(0xFFF59E0B);
  static const Color error = Color(0xFFEF4444);
  static const Color info = Color(0xFF3B82F6);

  // ── Score gradient ───────────────────────────────────────
  static const Color scoreExcellent = Color(0xFF10B981);
  static const Color scoreGood = Color(0xFF00C6AE);
  static const Color scoreFair = Color(0xFFF59E0B);
  static const Color scorePoor = Color(0xFFEF4444);

  // ── Gradients ────────────────────────────────────────────
  static const LinearGradient primaryGradient = LinearGradient(
    colors: [Color(0xFF00C6AE), Color(0xFF0099FF)],
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  );

  static const LinearGradient orangeGradient = LinearGradient(
    colors: [Color(0xFFFF6B35), Color(0xFFFF9A3C)],
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  );

  static const LinearGradient darkCardGradient = LinearGradient(
    colors: [Color(0xFF242838), Color(0xFF1A1D27)],
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  );
}
