import 'package:bpt/features/onboarding/providers/onboarding_provider.dart';
import 'package:bpt/features/onboarding/screens/onboarding_body_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('bmi is derived from height and weight and buckets correctly', () {
    final notifier = OnboardingNotifier();
    addTearDown(notifier.dispose);

    // Default: 176cm / 71.5kg -> BMI 23.1 (overweight bucket starts at 23).
    expect(notifier.state.bmi, closeTo(23.08, 0.01));
    expect(notifier.state.bmiCategory, BmiCategory.overweight);

    notifier.setHeight(180);
    notifier.setWeight(60);
    expect(notifier.state.bmi, closeTo(18.52, 0.01));
    expect(notifier.state.bmiCategory, BmiCategory.normal);

    notifier.setWeight(50);
    expect(notifier.state.bmiCategory, BmiCategory.underweight);

    notifier.setWeight(90);
    expect(notifier.state.bmiCategory, BmiCategory.obese);
  });

  testWidgets('sliders update the displayed height/weight and BMI live',
      (tester) async {
    await tester.pumpWidget(
        const ProviderScope(child: MaterialApp(home: OnboardingBodyScreen())));

    expect(find.text('176'), findsOneWidget);
    expect(find.text('71.5'), findsOneWidget);
    expect(find.text('23.1'), findsOneWidget);

    final heightSlider = find.byType(Slider).first;
    await tester.drag(heightSlider, const Offset(-300, 0));
    await tester.pump();

    expect(find.text('176'), findsNothing);
    expect(tester.takeException(), isNull);
  });

  testWidgets('tapping the value shows a text field to type an exact number',
      (tester) async {
    late final ProviderContainer container;
    await tester.pumpWidget(ProviderScope(
      child: Builder(builder: (context) {
        container = ProviderScope.containerOf(context);
        return const MaterialApp(home: OnboardingBodyScreen());
      }),
    ));

    await tester.tap(find.text('176'));
    await tester.pump();
    expect(find.byType(TextField), findsOneWidget);

    await tester.enterText(find.byType(TextField), '190');
    await tester.testTextInput.receiveAction(TextInputAction.done);
    await tester.pump();

    expect(container.read(onboardingProvider).heightCm, 190);
    expect(find.text('190'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets('typed value is clamped to the slider range', (tester) async {
    late final ProviderContainer container;
    await tester.pumpWidget(ProviderScope(
      child: Builder(builder: (context) {
        container = ProviderScope.containerOf(context);
        return const MaterialApp(home: OnboardingBodyScreen());
      }),
    ));

    await tester.tap(find.text('176'));
    await tester.pump();
    await tester.enterText(find.byType(TextField), '999');
    await tester.testTextInput.receiveAction(TextInputAction.done);
    await tester.pump();

    expect(container.read(onboardingProvider).heightCm, 200); // clamped max
  });
}
