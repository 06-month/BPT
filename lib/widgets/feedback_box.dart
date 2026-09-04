import 'package:flutter/material.dart';
import '../core/theme/app_colors.dart';

enum FeedbackType { info, success, warning, error, ai }

class FeedbackBox extends StatelessWidget {
  const FeedbackBox({
    super.key,
    required this.message,
    this.type = FeedbackType.ai,
    this.isAnimated = false,
    this.compact = false,
  });

  final String message;
  final FeedbackType type;
  final bool isAnimated;
  final bool compact;

  Color get _color {
    switch (type) {
      case FeedbackType.info:
        return AppColors.info;
      case FeedbackType.success:
        return AppColors.success;
      case FeedbackType.warning:
        return AppColors.warning;
      case FeedbackType.error:
        return AppColors.error;
      case FeedbackType.ai:
        return AppColors.primary;
    }
  }

  IconData get _icon {
    switch (type) {
      case FeedbackType.info:
        return Icons.info_outline_rounded;
      case FeedbackType.success:
        return Icons.check_circle_outline_rounded;
      case FeedbackType.warning:
        return Icons.warning_amber_rounded;
      case FeedbackType.error:
        return Icons.error_outline_rounded;
      case FeedbackType.ai:
        return Icons.auto_awesome_rounded;
    }
  }

  @override
  Widget build(BuildContext context) {
    final color = _color;

    return AnimatedSwitcher(
      duration: const Duration(milliseconds: 300),
      transitionBuilder: (child, anim) =>
          FadeTransition(opacity: anim, child: child),
      child: Container(
        key: ValueKey(message),
        padding: EdgeInsets.symmetric(
          horizontal: compact ? 12 : 16,
          vertical: compact ? 8 : 12,
        ),
        decoration: BoxDecoration(
          color: color.withValues(alpha: 0.08),
          borderRadius: BorderRadius.circular(compact ? 10 : 14),
          border: Border.all(color: color.withValues(alpha: 0.25), width: 1),
        ),
        child: Row(
          children: [
            if (isAnimated)
              _PulsingDot(color: color)
            else
              Icon(_icon, color: color, size: compact ? 16 : 20),
            const SizedBox(width: 10),
            Expanded(
              child: Text(
                message,
                style: TextStyle(
                  color: color,
                  fontSize: compact ? 12 : 14,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _PulsingDot extends StatefulWidget {
  const _PulsingDot({required this.color});
  final Color color;

  @override
  State<_PulsingDot> createState() => _PulsingDotState();
}

class _PulsingDotState extends State<_PulsingDot>
    with SingleTickerProviderStateMixin {
  late AnimationController _ctrl;

  @override
  void initState() {
    super.initState();
    _ctrl = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 900),
    )..repeat(reverse: true);
  }

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _ctrl,
      builder: (_, __) => Container(
        width: 8,
        height: 8,
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          color: widget.color.withValues(alpha: 0.4 + 0.6 * _ctrl.value),
        ),
      ),
    );
  }
}
