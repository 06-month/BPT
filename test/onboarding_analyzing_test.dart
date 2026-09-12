import 'package:bpt/features/onboarding/screens/onboarding_analyzing_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  void setPhoneSize(WidgetTester tester) {
    tester.view.physicalSize = const Size(390, 844);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
  }

  testWidgets('shows 0% and only the first step done at the start',
      (tester) async {
    setPhoneSize(tester);
    await tester
        .pumpWidget(const MaterialApp(home: OnboardingAnalyzingScreen()));

    expect(find.text('체형 분석 중이야!\n금방 끝나'), findsOneWidget);
    expect(find.text('0%'), findsOneWidget);
    expect(find.text('완료'), findsOneWidget);
    expect(find.text('진행 중'), findsOneWidget);
    expect(find.text('대기 중'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets(
      'halfway through, the keypoint step completes and 3D step becomes active',
      (tester) async {
    setPhoneSize(tester);
    await tester
        .pumpWidget(const MaterialApp(home: OnboardingAnalyzingScreen()));

    await tester.pump(const Duration(seconds: 20));

    expect(find.text('50%'), findsOneWidget);
    expect(find.text('완료'), findsNWidgets(2));
    expect(find.text('진행 중'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });
}
