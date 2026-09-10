import 'package:bpt/features/onboarding/providers/onboarding_provider.dart';
import 'package:bpt/features/onboarding/screens/onboarding_goal_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('goal course label matches the selected goal', () {
    final notifier = OnboardingNotifier();
    addTearDown(notifier.dispose);

    expect(notifier.state.goal, WorkoutGoal.strength); // default
    expect(notifier.state.goalCourseLabel, '근력');
    expect(notifier.state.weeklyFrequency, 5); // default

    notifier.selectGoal(WorkoutGoal.weightLoss);
    expect(notifier.state.goalCourseLabel, '체중 감량');

    notifier.setWeeklyFrequency(3);
    expect(notifier.state.weeklyFrequency, 3);
  });

  testWidgets('selecting a goal and frequency updates the speech bubble',
      (tester) async {
    tester.view.physicalSize = const Size(390, 1200);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    await tester.pumpWidget(
        const ProviderScope(child: MaterialApp(home: OnboardingGoalScreen())));

    // Default selection reflected in the bubble.
    expect(find.text('주 5회 근력 코스로 가볼게!\n세트 수량 반복 횟수는 나중에 바꿀 수 있어.'),
        findsOneWidget);

    await tester.tap(find.text('체형 교정'));
    await tester.pump();
    await tester.tap(find.text('3'));
    await tester.pump();

    expect(find.text('주 3회 체형 교정 코스로 가볼게!\n세트 수량 반복 횟수는 나중에 바꿀 수 있어.'),
        findsOneWidget);

    // Only one goal is selected at a time.
    expect(find.byIcon(Icons.check_rounded), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets('next button is always enabled and labeled for this step',
      (tester) async {
    await tester.pumpWidget(
        const ProviderScope(child: MaterialApp(home: OnboardingGoalScreen())));

    final nextFinder = find.widgetWithText(ElevatedButton, '체형 측정하러 가기');
    expect(nextFinder, findsOneWidget);
    expect(tester.widget<ElevatedButton>(nextFinder).onPressed, isNotNull);
  });

  testWidgets('headline stays fixed while the goal list scrolls',
      (tester) async {
    tester.view.physicalSize = const Size(390, 500);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    await tester.pumpWidget(
        const ProviderScope(child: MaterialApp(home: OnboardingGoalScreen())));

    final headlineBefore = tester.getTopLeft(find.text('목표가 뭐야?\n거기에 맞춰줄게'));
    await tester.drag(
        find.byType(SingleChildScrollView), const Offset(0, -300));
    await tester.pump();
    final headlineAfter = tester.getTopLeft(find.text('목표가 뭐야?\n거기에 맞춰줄게'));

    expect(headlineAfter, headlineBefore);
    expect(tester.takeException(), isNull);
  });
}
