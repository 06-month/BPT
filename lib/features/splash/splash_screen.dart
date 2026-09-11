import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/constants/route_constants.dart';
import '../../core/theme/app_colors.dart';
import '../auth/providers/auth_provider.dart';

class SplashScreen extends ConsumerStatefulWidget {
  const SplashScreen({super.key});

  @override
  ConsumerState<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends ConsumerState<SplashScreen>
    with SingleTickerProviderStateMixin {
  late final AnimationController _ctrl;
  late final Animation<double> _fadeAnim;
  static const _logo = AssetImage('assets/images/character/splash_logo.png');
  // Bounce is relative to the final circle, not the screen-sized circle.
  final _settle = TweenSequence<double>([
    TweenSequenceItem(
      tween: Tween(begin: 1.0, end: 0.985)
          .chain(CurveTween(curve: Curves.easeOut)),
      weight: 35,
    ),
    TweenSequenceItem(
      tween: Tween(begin: 0.985, end: 1.004)
          .chain(CurveTween(curve: Curves.easeInOut)),
      weight: 40,
    ),
    TweenSequenceItem(
      tween: Tween(begin: 1.004, end: 1.0)
          .chain(CurveTween(curve: Curves.easeOut)),
      weight: 25,
    ),
  ]);

  @override
  void initState() {
    super.initState();
    _ctrl = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 880),
    );
    _fadeAnim = _ctrl.drive(
      CurveTween(curve: const Interval(0, 0.8, curve: Curves.easeInOut)),
    );
    // Show the full lime circle on the first Flutter frame, then animate only
    // once the transparent logo is decoded so its fade never pops in late.
    WidgetsBinding.instance.addPostFrameCallback((_) => _start());
  }

  Future<void> _start() async {
    if (!mounted) return;
    await precacheImage(_logo, context);
    if (!mounted) return;
    try {
      await _ctrl.forward().orCancel;
    } on TickerCanceled {
      return;
    }
    if (!mounted) return;
    final loggedIn = await ref.read(authNotifierProvider).tryAutoLogin();
    if (!mounted) return;
    context.go(loggedIn ? RouteConstants.home : RouteConstants.login);
  }

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.black,
      body: LayoutBuilder(
        builder: (context, constraints) {
          final size = constraints.biggest;
          final logoSize = size.shortestSide * 0.75;
          // Match the character's backdrop within the transparent PNG canvas:
          // the BPT lettering hangs below the circle, as in the reference.
          final circleDiameter = logoSize * 0.62;
          final circleOffsetY = -logoSize * 0.11;
          // Cover even the farthest corner from the raised circle center.
          final farthestY = size.height / 2 + circleOffsetY.abs();
          final initialDiameter = 2 *
                  math.sqrt(
                      size.width * size.width / 4 + farthestY * farthestY) +
              2;
          return ClipRect(
            child: Stack(
              fit: StackFit.expand,
              alignment: Alignment.center,
              children: [
                AnimatedBuilder(
                  animation: _ctrl,
                  builder: (context, child) {
                    final t = _ctrl.value;
                    final diameter = t <= 0.8
                        ? initialDiameter +
                            (circleDiameter - initialDiameter) *
                                Curves.easeOutCubic.transform(t / 0.8)
                        : circleDiameter *
                            _settle.transform(
                              ((t - 0.8) / 0.2).clamp(0.0, 1.0),
                            );
                    return Transform.translate(
                      offset: Offset(0, circleOffsetY),
                      child: OverflowBox(
                        minWidth: diameter,
                        maxWidth: diameter,
                        minHeight: diameter,
                        maxHeight: diameter,
                        child: const DecoratedBox(
                          decoration: BoxDecoration(
                            color: AppColors.green,
                            shape: BoxShape.circle,
                          ),
                        ),
                      ),
                    );
                  },
                ),
                Center(
                  child: FadeTransition(
                    opacity: _fadeAnim,
                    child: Image(
                      image: _logo,
                      width: logoSize,
                      height: logoSize,
                      fit: BoxFit.contain,
                      semanticLabel: 'BPT',
                    ),
                  ),
                ),
              ],
            ),
          );
        },
      ),
    );
  }
}
