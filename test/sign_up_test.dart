import 'package:bpt/core/theme/app_colors.dart';
import 'package:bpt/features/auth/providers/sign_up_provider.dart';
import 'package:bpt/features/auth/screens/sign_up_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('id duplicate check and submit gating follow the mock rules', () {
    final notifier = SignUpNotifier();
    addTearDown(notifier.dispose);

    notifier.changeEmail('jihoon@bpt.app');
    notifier.changeId('admin');
    notifier.checkIdDuplicate();
    expect(notifier.state.idCheck, IdCheckStatus.taken);
    expect(notifier.state.canSubmit, isFalse);

    notifier.changeId('jihoon_kim');
    // Editing the id after a check must reset the check result.
    expect(notifier.state.idCheck, IdCheckStatus.none);
    notifier.checkIdDuplicate();
    expect(notifier.state.idCheck, IdCheckStatus.available);

    notifier.changePassword('1234567');
    expect(notifier.state.passwordValid, isFalse); // under 8 chars
    notifier.changePassword('12345678');
    notifier.changeConfirmPassword('12345678');
    notifier.changePhone('01028417756');
    expect(notifier.state.canSubmit, isFalse); // no birth date / terms yet

    notifier.setBirthDate(DateTime(1999, 4, 12));
    expect(notifier.state.canSubmit, isFalse); // terms not agreed

    notifier.toggleAgreed();
    expect(notifier.state.canSubmit, isTrue);
  });

  testWidgets('sign up form enables fields and the submit button in order',
      (tester) async {
    tester.view.physicalSize = const Size(390, 1000);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    await tester.pumpWidget(
        const ProviderScope(child: MaterialApp(home: SignUpScreen())));

    final fields = find.byType(TextField);
    // email, id, password, confirm, phone, birth date
    expect(fields, findsNWidgets(6));

    await tester.enterText(fields.at(0), 'jihoon@bpt.app');
    final border = tester
        .widget<TextField>(fields.at(0))
        .decoration!
        .focusedBorder! as OutlineInputBorder;
    expect(border.borderSide.color, AppColors.green);

    await tester.enterText(fields.at(1), 'admin');
    await tester.pump();
    await tester.tap(find.text('중복확인'));
    await tester.pump();
    expect(find.text('이미 사용 중인 아이디예요. 다른 아이디를 입력해줘.'), findsOneWidget);

    await tester.enterText(fields.at(1), 'jihoon_kim');
    await tester.pump();
    // editing after a failed check clears the error and re-enables the button
    expect(find.text('이미 사용 중인 아이디예요. 다른 아이디를 입력해줘.'), findsNothing);
    await tester.tap(find.text('중복확인'));
    await tester.pump();
    expect(find.text('확인 완료'), findsOneWidget);

    await tester.enterText(fields.at(2), '12345678');
    await tester.enterText(fields.at(3), '00000000');
    await tester.pump();
    expect(find.text('비밀번호가 서로 달라. 다시 확인해줘.'), findsOneWidget);
    // Mismatched: both password fields show a visibility toggle.
    expect(find.byIcon(Icons.visibility_outlined), findsNWidgets(2));
    expect(tester.widget<TextField>(fields.at(3)).obscureText, isTrue);
    await tester.tap(find.byIcon(Icons.visibility_outlined).last);
    await tester.pump();
    expect(tester.widget<TextField>(fields.at(3)).obscureText, isFalse);

    await tester.enterText(fields.at(3), '12345678');
    await tester.pump();
    expect(find.text('비밀번호가 서로 달라. 다시 확인해줘.'), findsNothing);
    // Matched: the confirm field swaps its toggle for a check mark.
    expect(find.byIcon(Icons.visibility_outlined), findsOneWidget);

    await tester.enterText(fields.at(4), '01028417756');
    await tester.pump();

    final submitFinder = find.widgetWithText(ElevatedButton, '가입하기');
    expect(tester.widget<ElevatedButton>(submitFinder).onPressed, isNull);

    // Simulate picking a birth date directly through the provider, since
    // showDatePicker opens a real dialog that isn't worth driving here.
    final context = tester.element(find.byType(SignUpScreen));
    ProviderScope.containerOf(context, listen: false)
        .read(signUpProvider.notifier)
        .setBirthDate(DateTime(1999, 4, 12));
    await tester.pump();
    expect(tester.widget<ElevatedButton>(submitFinder).onPressed, isNull);

    await tester.tap(find.text('이용약관 및 개인정보 처리방침에 동의'));
    await tester.pump();
    expect(tester.widget<ElevatedButton>(submitFinder).onPressed, isNotNull);

    await tester.tap(submitFinder);
    await tester.pump();
    expect(find.text('미리보기 완료! 실제 계정은 아직 생성되지 않았어.'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });
}
