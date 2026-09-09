import 'package:bpt/core/theme/app_colors.dart';
import 'package:bpt/features/auth/providers/account_recovery_provider.dart';
import 'package:bpt/features/auth/screens/account_recovery_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('verification requires send and changing email invalidates proof', () {
    final notifier = AccountRecoveryNotifier();
    addTearDown(notifier.dispose);
    notifier.verifyCode(recoveryPreviewCode);
    expect(notifier.state.verified, isFalse);
    notifier.changeEmail('not-an-email');
    expect(notifier.sendCode(), isFalse);
    notifier.changeEmail('jihoon@bpt.app');
    expect(notifier.sendCode(), isTrue);
    notifier.verifyCode('000000');
    expect(notifier.state.verified, isFalse);
    expect(notifier.state.error, isNotNull);
    notifier.verifyCode(recoveryPreviewCode);
    expect(notifier.state.verified, isTrue);
    expect(notifier.state.maskedId, 'jih***@bpt.app');
    notifier.changeEmail('other@bpt.app');
    expect(notifier.state.sent, isFalse);
    expect(notifier.state.verified, isFalse);
    expect(notifier.state.error, isNull);
  });

  testWidgets('email, code, result and focus follow recovery sequence',
      (tester) async {
    tester.view.physicalSize = const Size(390, 844);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    await tester.pumpWidget(
        const ProviderScope(child: MaterialApp(home: AccountRecoveryScreen())));
    final fields = find.byType(TextField);
    expect(tester.widget<TextField>(fields.at(1)).enabled, isFalse);
    expect(find.text('찾은 아이디 · 미리보기'), findsNothing);
    await tester.enterText(fields.at(0), 'jihoon@bpt.app');
    expect(tester.widget<TextField>(fields.at(0)).focusNode!.hasFocus, isTrue);
    final border = tester
        .widget<TextField>(fields.at(0))
        .decoration!
        .focusedBorder! as OutlineInputBorder;
    expect(border.borderSide.color, AppColors.green);
    await tester.tap(find.text('인증하기').first);
    await tester.pumpAndSettle();
    expect(find.text('전송 완료'), findsOneWidget);
    expect(tester.widget<TextField>(fields.at(1)).enabled, isTrue);
    expect(tester.widget<TextField>(fields.at(0)).focusNode!.hasFocus, isFalse);
    expect(tester.widget<TextField>(fields.at(1)).focusNode!.hasFocus, isTrue);
    await tester.enterText(fields.at(1), '000000');
    await tester.pump();
    await tester.tap(find.text('인증하기'));
    await tester.pump();
    expect(find.text('찾은 아이디 · 미리보기'), findsNothing);
    expect(find.text('인증 코드가 맞지 않아. 다시 확인해줘.'), findsOneWidget);
    await tester.enterText(fields.at(1), recoveryPreviewCode);
    await tester.pump();
    await tester.tap(find.text('인증하기'));
    await tester.pumpAndSettle();
    expect(find.text('인증 완료'), findsOneWidget);
    expect(find.text('찾은 아이디 · 미리보기'), findsOneWidget);
    expect(tester.widget<TextField>(fields.at(1)).focusNode!.hasFocus, isFalse);
    await tester.enterText(fields.at(0), 'different@bpt.app');
    await tester.pump();
    expect(find.text('찾은 아이디 · 미리보기'), findsNothing);
    expect(tester.widget<TextField>(fields.at(1)).enabled, isFalse);
    tester.view.physicalSize = const Size(320, 568);
    tester.view.viewInsets = const FakeViewPadding(bottom: 250);
    addTearDown(tester.view.resetViewInsets);
    await tester.pumpAndSettle();
    expect(tester.takeException(), isNull);
  });
}
