import 'package:bpt/features/onboarding/providers/onboarding_provider.dart';
import 'package:bpt/features/onboarding/screens/onboarding_gender_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  testWidgets('next is disabled until a gender option is picked',
      (tester) async {
    tester.view.physicalSize = const Size(390, 844);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    await tester.pumpWidget(const ProviderScope(
        child: MaterialApp(home: OnboardingGenderScreen())));

    final nextFinder = find.widgetWithText(ElevatedButton, '다음');
    expect(tester.widget<ElevatedButton>(nextFinder).onPressed, isNull);

    await tester.tap(find.text('남자'));
    await tester.pump();
    expect(tester.widget<ElevatedButton>(nextFinder).onPressed, isNotNull);
    expect(tester.takeException(), isNull);
  });

  testWidgets(
      'selecting a card is reflected in provider state and is exclusive',
      (tester) async {
    tester.view.physicalSize = const Size(390, 844);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    late final ProviderContainer container;
    await tester.pumpWidget(ProviderScope(
      child: Builder(builder: (context) {
        container = ProviderScope.containerOf(context);
        return const MaterialApp(home: OnboardingGenderScreen());
      }),
    ));

    await tester.tap(find.text('남자'));
    await tester.pump();
    expect(container.read(onboardingProvider).gender, Gender.male);

    await tester.tap(find.text('여자'));
    await tester.pump();
    expect(container.read(onboardingProvider).gender, Gender.female);

    await tester.tap(find.text('선택하지 않음'));
    await tester.pump();
    expect(container.read(onboardingProvider).gender, Gender.preferNotToSay);
  });
}
