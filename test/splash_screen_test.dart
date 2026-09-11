import 'dart:async';
import 'dart:math' as math;

import 'package:bpt/core/theme/app_colors.dart';
import 'package:bpt/features/auth/providers/auth_provider.dart';
import 'package:bpt/features/splash/splash_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';

class _Auth extends ChangeNotifier implements AuthNotifier {
  final result = Completer<bool>();
  int calls = 0;

  @override
  Future<bool> tryAutoLogin() {
    calls++;
    return result.future;
  }

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

Future<void> _showSplash(WidgetTester tester, _Auth auth, Size size) async {
  tester.view.physicalSize = size;
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);
  // Decode the actual bundled PNG before advancing the animation clock.
  await tester.pumpWidget(const MaterialApp(home: SizedBox()));
  await tester.runAsync(() => precacheImage(
        const AssetImage('assets/images/character/splash_logo.png'),
        tester.element(find.byType(SizedBox)),
      ));
  final router = GoRouter(routes: [
    GoRoute(path: '/', builder: (_, __) => const SplashScreen()),
    GoRoute(path: '/home', builder: (_, __) => const Text('home destination')),
    GoRoute(
        path: '/login', builder: (_, __) => const Text('login destination')),
  ]);
  addTearDown(router.dispose);
  await tester.pumpWidget(ProviderScope(
    overrides: [authNotifierProvider.overrideWith((ref) => auth)],
    child: MaterialApp.router(
      // The splash must stay #101010 even when the system uses a light theme.
      theme: ThemeData(scaffoldBackgroundColor: Colors.white),
      routerConfig: router,
    ),
  ));
  await tester.pump();
}

void main() {
  for (final size in [const Size(390, 844), const Size(800, 1280)]) {
    testWidgets('circle covers $size; logo stays fixed through fade and bounce',
        (tester) async {
      final auth = _Auth();
      await _showSplash(tester, auth, size);
      final circle = find.byWidgetPredicate((widget) =>
          widget is DecoratedBox &&
          widget.decoration is BoxDecoration &&
          (widget.decoration as BoxDecoration).shape == BoxShape.circle);
      final logo = find.byType(Image);
      final initialLogoSize = tester.getSize(logo);
      final center = tester.getCenter(logo);
      double opacity() => tester
          .widget<FadeTransition>(find
              .ancestor(
                of: logo,
                matching: find.byType(FadeTransition),
              )
              .first)
          .opacity
          .value;
      expect(
          tester.getSize(circle).width,
          greaterThan(
              math.sqrt(size.width * size.width + size.height * size.height)));
      expect(opacity(), 0);
      expect(center, Offset(size.width / 2, size.height / 2));
      final circleCenter = tester.getCenter(circle);
      final initialRadius = tester.getSize(circle).width / 2;
      for (final corner in [
        Offset.zero,
        Offset(size.width, 0),
        Offset(0, size.height),
        Offset(size.width, size.height),
      ]) {
        expect((corner - circleCenter).distance, lessThan(initialRadius));
      }
      expect(tester.widget<Scaffold>(find.byType(Scaffold)).backgroundColor,
          AppColors.black);
      await tester.pump(const Duration(milliseconds: 350));
      expect(opacity(), inExclusiveRange(0, 1));
      expect(tester.getSize(logo), initialLogoSize);
      expect(tester.getCenter(logo), center);
      expect(auth.calls, 0);
      await tester.pump(const Duration(milliseconds: 354));
      final finalDiameter = initialLogoSize.width * 0.62;
      expect(tester.getSize(circle).width, closeTo(finalDiameter, 0.01));
      expect(tester.getCenter(circle).dx, center.dx);
      expect(tester.getCenter(circle).dy,
          closeTo(center.dy - initialLogoSize.height * 0.11, 0.01));
      // Circle ends within the upper portion of the lettering, leaving the
      // bottom of BPT (at ~88% of the PNG canvas) outside the backdrop.
      expect(tester.getRect(circle).bottom,
          lessThan(tester.getRect(logo).top + initialLogoSize.height * 0.72));
      expect(opacity(), closeTo(1, 0.00001));
      await tester.pump(const Duration(milliseconds: 62));
      expect(tester.getSize(circle).width,
          inExclusiveRange(finalDiameter * 0.98, finalDiameter));
      expect(tester.getSize(logo), initialLogoSize);
      expect(tester.getCenter(logo), center);
      await tester.pump(const Duration(milliseconds: 115));
      expect(tester.getSize(circle).width, closeTo(finalDiameter, 0.01));
      expect(auth.calls, 1);
      expect(find.byType(SplashScreen), findsOneWidget);
      auth.result.complete(true);
      await tester.pumpAndSettle();
      expect(find.text('home destination'), findsOneWidget);
      expect(tester.takeException(), isNull);
    });
  }

  testWidgets('signed-out users retain the existing login destination',
      (tester) async {
    final auth = _Auth()..result.complete(false);
    await _showSplash(tester, auth, const Size(390, 844));
    await tester.pump(const Duration(milliseconds: 800));
    expect(find.text('login destination'), findsNothing);
    await tester.pumpAndSettle();
    expect(find.text('login destination'), findsOneWidget);
  });

  testWidgets('disposing during animation cancels navigation', (tester) async {
    final auth = _Auth();
    await _showSplash(tester, auth, const Size(390, 844));
    await tester.pump(const Duration(milliseconds: 300));
    await tester.pumpWidget(const SizedBox());
    await tester.pump(const Duration(seconds: 3));
    expect(auth.calls, 0);
    expect(tester.takeException(), isNull);
  });
}
