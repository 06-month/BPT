import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/theme/app_colors.dart';
import '../providers/sign_up_provider.dart';
import '../widgets/auth_dark_form.dart';

class SignUpScreen extends ConsumerStatefulWidget {
  const SignUpScreen({super.key});

  @override
  ConsumerState<SignUpScreen> createState() => _SignUpScreenState();
}

class _SignUpScreenState extends ConsumerState<SignUpScreen> {
  final _email = TextEditingController();
  final _id = TextEditingController();
  final _password = TextEditingController();
  final _confirmPassword = TextEditingController();
  final _phone = TextEditingController();
  final _birthDate = TextEditingController();

  final _emailFocus = FocusNode();
  final _idFocus = FocusNode();
  final _passwordFocus = FocusNode();
  final _confirmPasswordFocus = FocusNode();
  final _phoneFocus = FocusNode();
  final _birthDateFocus = FocusNode(canRequestFocus: false);

  bool _hidePassword = true;
  bool _hideConfirmPassword = true;

  @override
  void dispose() {
    for (final controller in [
      _email,
      _id,
      _password,
      _confirmPassword,
      _phone,
      _birthDate,
    ]) {
      controller.dispose();
    }
    for (final focus in [
      _emailFocus,
      _idFocus,
      _passwordFocus,
      _confirmPasswordFocus,
      _phoneFocus,
      _birthDateFocus,
    ]) {
      focus.dispose();
    }
    super.dispose();
  }

  Future<void> _pickBirthDate() async {
    FocusScope.of(context).unfocus();
    final now = DateTime.now();
    final state = ref.read(signUpProvider);
    final picked = await showDatePicker(
      context: context,
      initialDate: state.birthDate ?? DateTime(now.year - 20),
      firstDate: DateTime(1900),
      lastDate: now,
      locale: const Locale('ko'),
      builder: (context, child) => Theme(
        data: ThemeData.dark().copyWith(
          textTheme: ThemeData.dark().textTheme.apply(fontFamily: 'Pretendard'),
          colorScheme: const ColorScheme.dark(
            primary: AppColors.green,
            onPrimary: AppColors.black,
            surface: AppColors.grey,
            onSurface: AppColors.white,
          ),
          dialogTheme: const DialogThemeData(backgroundColor: AppColors.grey),
          textButtonTheme: TextButtonThemeData(
            style: TextButton.styleFrom(foregroundColor: AppColors.green),
          ),
        ),
        child: child!,
      ),
    );
    if (picked == null || !mounted) return;
    ref.read(signUpProvider.notifier).setBirthDate(picked);
    _birthDate.text =
        '${picked.year}. ${picked.month.toString().padLeft(2, '0')}. '
        '${picked.day.toString().padLeft(2, '0')}';
  }

  void _submit(SignUpState state) {
    if (!state.canSubmit) return;
    FocusScope.of(context).unfocus();
    ScaffoldMessenger.of(context).showSnackBar(const SnackBar(
      content: Text('미리보기 완료! 실제 계정은 아직 생성되지 않았어.'),
    ));
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(signUpProvider);
    final notifier = ref.read(signUpProvider.notifier);
    return AuthScrollScaffold(
      title: '회원가입',
      onBack: () => context.pop(),
      body: [
        const SizedBox(height: 8),
        Row(crossAxisAlignment: CrossAxisAlignment.end, children: [
          Image.asset(
            state.canSubmit
                ? 'assets/images/character/face2.png'
                : 'assets/images/character/face.png',
            width: 62,
            height: 68,
            fit: BoxFit.contain,
            excludeFromSemantics: true,
          ),
          const SizedBox(width: 10),
          Expanded(
              child: Container(
            margin: const EdgeInsets.only(bottom: 4),
            padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 14),
            decoration: const BoxDecoration(
              color: AppColors.green,
              borderRadius: BorderRadius.only(
                topLeft: Radius.circular(22),
                topRight: Radius.circular(22),
                bottomRight: Radius.circular(22),
                bottomLeft: Radius.circular(3),
              ),
            ),
            child: Text(
              state.canSubmit ? '좋아! 이제 가입할 수 있어!' : '너에 대해 알려줘!',
              style: const TextStyle(
                  color: AppColors.black,
                  fontWeight: FontWeight.w800,
                  fontSize: 14),
            ),
          )),
        ]),
        const SizedBox(height: 20),
        const AuthFieldLabel('이메일'),
        AuthTextField(
          controller: _email,
          focus: _emailFocus,
          hint: '이메일을 입력해줘',
          keyboard: TextInputType.emailAddress,
          onChanged: notifier.changeEmail,
        ),
        const SizedBox(height: 14),
        const AuthFieldLabel('아이디'),
        Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Expanded(
              child: AuthTextField(
            controller: _id,
            focus: _idFocus,
            hint: '아이디를 입력해줘',
            onChanged: notifier.changeId,
          )),
          const SizedBox(width: 12),
          AuthStatusButton(
              label:
                  state.idCheck == IdCheckStatus.available ? '확인 완료' : '중복확인',
              complete: state.idCheck == IdCheckStatus.available,
              onTap: state.id.trim().isEmpty ||
                      state.idCheck == IdCheckStatus.available
                  ? null
                  : notifier.checkIdDuplicate),
        ]),
        if (state.idCheck == IdCheckStatus.taken) ...[
          const SizedBox(height: 8),
          const Text('이미 사용 중인 아이디예요. 다른 아이디를 입력해줘.',
              style: TextStyle(color: AppColors.red, fontSize: 13)),
        ],
        const SizedBox(height: 14),
        const AuthFieldLabel('비밀번호'),
        AuthTextField(
          controller: _password,
          focus: _passwordFocus,
          hint: '영문, 숫자 포함 8자 이상',
          obscure: _hidePassword,
          onChanged: notifier.changePassword,
          suffix: authEyeToggle(_hidePassword,
              () => setState(() => _hidePassword = !_hidePassword)),
        ),
        const SizedBox(height: 14),
        const AuthFieldLabel('비밀번호 재확인'),
        AuthTextField(
          controller: _confirmPassword,
          focus: _confirmPasswordFocus,
          hint: '비밀번호를 한 번 더 입력해줘',
          obscure: _hideConfirmPassword,
          onChanged: notifier.changeConfirmPassword,
          suffix: state.confirmValid
              ? const Icon(Icons.check_rounded,
                  color: AppColors.green, size: 22)
              : authEyeToggle(
                  _hideConfirmPassword,
                  () => setState(
                      () => _hideConfirmPassword = !_hideConfirmPassword)),
        ),
        if (state.confirmPassword.isNotEmpty && !state.confirmValid) ...[
          const SizedBox(height: 8),
          const Text('비밀번호가 서로 달라. 다시 확인해줘.',
              style: TextStyle(color: AppColors.red, fontSize: 13)),
        ],
        const SizedBox(height: 14),
        const AuthFieldLabel('전화번호'),
        AuthTextField(
          controller: _phone,
          focus: _phoneFocus,
          hint: '010-0000-0000',
          keyboard: TextInputType.phone,
          formatters: [
            FilteringTextInputFormatter.digitsOnly,
            LengthLimitingTextInputFormatter(11),
            _PhoneNumberFormatter(),
          ],
          onChanged: notifier.changePhone,
        ),
        const SizedBox(height: 14),
        const AuthFieldLabel('생년월일'),
        AuthTextField(
          controller: _birthDate,
          focus: _birthDateFocus,
          hint: '2000. 01. 01',
          readOnly: true,
          onTap: _pickBirthDate,
          suffix: const Icon(Icons.calendar_today_outlined,
              color: Color(0xFF888888), size: 20),
        ),
        const SizedBox(height: 20),
        GestureDetector(
          onTap: notifier.toggleAgreed,
          behavior: HitTestBehavior.opaque,
          child: Row(children: [
            Container(
              width: 22,
              height: 22,
              decoration: BoxDecoration(
                color: state.agreed ? AppColors.green : Colors.transparent,
                border: Border.all(
                    color: state.agreed
                        ? AppColors.green
                        : const Color(0xFF444444)),
                borderRadius: BorderRadius.circular(6),
              ),
              child: state.agreed
                  ? const Icon(Icons.check_rounded,
                      color: AppColors.black, size: 16)
                  : null,
            ),
            const SizedBox(width: 10),
            const Expanded(
              child: Text('이용약관 및 개인정보 처리방침에 동의',
                  style: TextStyle(color: Color(0xFFBBBBBB), fontSize: 13)),
            ),
          ]),
        ),
      ],
      bottomBar: AuthPillButton(
        label: '가입하기',
        onTap: state.canSubmit ? () => _submit(state) : null,
        background: AppColors.green,
        foreground: AppColors.black,
        disabledBackground: AppColors.green.withValues(alpha: 0.5),
        disabledForeground: AppColors.black.withValues(alpha: 0.5),
      ),
    );
  }
}

/// Formats digits as 010-1234-5678 while typing.
class _PhoneNumberFormatter extends TextInputFormatter {
  @override
  TextEditingValue formatEditUpdate(
    TextEditingValue oldValue,
    TextEditingValue newValue,
  ) {
    final digits = newValue.text.replaceAll(RegExp(r'\D'), '');
    final buffer = StringBuffer();
    for (var i = 0; i < digits.length; i++) {
      if (i == 3 || i == 7) buffer.write('-');
      buffer.write(digits[i]);
    }
    return TextEditingValue(
      text: buffer.toString(),
      selection: TextSelection.collapsed(offset: buffer.length),
    );
  }
}
