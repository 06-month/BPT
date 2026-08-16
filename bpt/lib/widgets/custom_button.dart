import 'package:flutter/material.dart';
import '../core/theme/app_colors.dart';

enum ButtonVariant { primary, secondary, outline, ghost, danger }

class CustomButton extends StatelessWidget {
  const CustomButton({
    super.key,
    required this.label,
    required this.onPressed,
    this.variant = ButtonVariant.primary,
    this.icon,
    this.trailing,
    this.isLoading = false,
    this.isFullWidth = true,
    this.height = 52,
    this.borderRadius = 14,
    this.fontSize = 15,
  });

  final String label;
  final VoidCallback? onPressed;
  final ButtonVariant variant;
  final IconData? icon;
  final Widget? trailing;
  final bool isLoading;
  final bool isFullWidth;
  final double height;
  final double borderRadius;
  final double fontSize;

  @override
  Widget build(BuildContext context) {
    Widget child = isLoading
        ? const SizedBox(
            width: 20,
            height: 20,
            child: CircularProgressIndicator(
              strokeWidth: 2.5,
              color: Colors.white,
            ),
          )
        : Row(
            mainAxisSize: MainAxisSize.min,
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              if (icon != null) ...[
                Icon(icon, size: 18),
                const SizedBox(width: 8),
              ],
              Text(
                label,
                style: TextStyle(
                  fontSize: fontSize,
                  fontWeight: FontWeight.w700,
                ),
              ),
              if (trailing != null) ...[
                const SizedBox(width: 8),
                trailing!,
              ],
            ],
          );

    return SizedBox(
      width: isFullWidth ? double.infinity : null,
      height: height,
      child: _buildButton(context, child),
    );
  }

  Widget _buildButton(BuildContext context, Widget child) {
    final style = _buttonStyle();

    switch (variant) {
      case ButtonVariant.primary:
      case ButtonVariant.secondary:
      case ButtonVariant.danger:
        return ElevatedButton(
          onPressed: isLoading ? null : onPressed,
          style: style,
          child: child,
        );
      case ButtonVariant.outline:
        return OutlinedButton(
          onPressed: isLoading ? null : onPressed,
          style: style,
          child: child,
        );
      case ButtonVariant.ghost:
        return TextButton(
          onPressed: isLoading ? null : onPressed,
          style: style,
          child: child,
        );
    }
  }

  ButtonStyle _buttonStyle() {
    final radius = BorderRadius.circular(borderRadius);
    final shape = RoundedRectangleBorder(borderRadius: radius);

    switch (variant) {
      case ButtonVariant.primary:
        return ElevatedButton.styleFrom(
          backgroundColor: AppColors.primary,
          foregroundColor: Colors.white,
          elevation: 0,
          shape: shape,
        );
      case ButtonVariant.secondary:
        return ElevatedButton.styleFrom(
          backgroundColor: AppColors.secondary,
          foregroundColor: Colors.white,
          elevation: 0,
          shape: shape,
        );
      case ButtonVariant.danger:
        return ElevatedButton.styleFrom(
          backgroundColor: AppColors.error,
          foregroundColor: Colors.white,
          elevation: 0,
          shape: shape,
        );
      case ButtonVariant.outline:
        return OutlinedButton.styleFrom(
          foregroundColor: AppColors.primary,
          side: const BorderSide(color: AppColors.primary, width: 1.5),
          shape: shape,
        );
      case ButtonVariant.ghost:
        return TextButton.styleFrom(
          foregroundColor: AppColors.primary,
          shape: shape,
        );
    }
  }
}
