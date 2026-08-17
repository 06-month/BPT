import 'package:flutter/material.dart';
import '../core/theme/app_colors.dart';

class CustomProgressBar extends StatelessWidget {
  const CustomProgressBar({
    super.key,
    required this.value,
    this.height = 8,
    this.backgroundColor,
    this.gradient,
    this.color,
    this.borderRadius = 100,
    this.showLabel = false,
    this.label,
    this.animationDuration = const Duration(milliseconds: 400),
  }) : assert(value >= 0.0 && value <= 1.0);

  final double value;
  final double height;
  final Color? backgroundColor;
  final LinearGradient? gradient;
  final Color? color;
  final double borderRadius;
  final bool showLabel;
  final String? label;
  final Duration animationDuration;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;
    final bgColor = backgroundColor ??
        (isDark
            ? AppColors.darkDivider
            : AppColors.lightDivider);
    final fg = color ?? AppColors.primary;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        if (showLabel) ...[
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              if (label != null)
                Text(
                  label!,
                  style: theme.textTheme.bodySmall?.copyWith(
                    color: theme.colorScheme.onSurface.withValues(alpha: 0.55),
                  ),
                ),
              Text(
                '${(value * 100).round()}%',
                style: TextStyle(
                  color: fg,
                  fontWeight: FontWeight.w700,
                  fontSize: 12,
                ),
              ),
            ],
          ),
          const SizedBox(height: 6),
        ],
        ClipRRect(
          borderRadius: BorderRadius.circular(borderRadius),
          child: Stack(
            children: [
              Container(
                height: height,
                width: double.infinity,
                color: bgColor,
              ),
              AnimatedFractionallySizedBox(
                duration: animationDuration,
                curve: Curves.easeOut,
                widthFactor: value,
                child: Container(
                  height: height,
                  decoration: BoxDecoration(
                    color: gradient == null ? fg : null,
                    gradient: gradient,
                  ),
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class CircularProgressWidget extends StatelessWidget {
  const CircularProgressWidget({
    super.key,
    required this.value,
    this.size = 80,
    this.strokeWidth = 6,
    this.color = AppColors.primary,
    this.backgroundColor,
    this.child,
  });

  final double value;
  final double size;
  final double strokeWidth;
  final Color color;
  final Color? backgroundColor;
  final Widget? child;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final bg = backgroundColor ??
        theme.colorScheme.onSurface.withValues(alpha: 0.1);

    return SizedBox(
      width: size,
      height: size,
      child: Stack(
        alignment: Alignment.center,
        children: [
          CircularProgressIndicator(
            value: value,
            strokeWidth: strokeWidth,
            backgroundColor: bg,
            valueColor: AlwaysStoppedAnimation(color),
            strokeCap: StrokeCap.round,
          ),
          if (child != null) child!,
        ],
      ),
    );
  }
}
