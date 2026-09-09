import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/constants/route_constants.dart';
import '../../../core/theme/app_colors.dart';
import '../providers/account_recovery_provider.dart';

class AccountRecoveryScreen extends ConsumerStatefulWidget {
  const AccountRecoveryScreen({super.key});

  @override
  ConsumerState<AccountRecoveryScreen> createState() =>
      _AccountRecoveryScreenState();
}

class _AccountRecoveryScreenState extends ConsumerState<AccountRecoveryScreen> {
  final _email = TextEditingController();
  final _code = TextEditingController();
  final _password = TextEditingController();
  final _confirmation = TextEditingController();
  final _emailFocus = FocusNode();
  final _codeFocus = FocusNode();
  final _passwordFocus = FocusNode();
  final _confirmationFocus = FocusNode();
  bool _resetMode = false;
  bool _hidePassword = true;
  bool _hideConfirmation = true;
  String? _passwordError;

  @override
  void dispose() {
    for (final controller in [_email, _code, _password, _confirmation]) {
      controller.dispose();
    }
    for (final focus in [
      _emailFocus,
      _codeFocus,
      _passwordFocus,
      _confirmationFocus
    ]) {
      focus.dispose();
    }
    super.dispose();
  }

  void _changeMode(bool reset) {
    FocusScope.of(context).unfocus();
    setState(() {
      _resetMode = reset;
      _passwordError = null;
      _password.clear();
      _confirmation.clear();
    });
  }

  void _back({String? email}) {
    if (context.canPop()) {
      context.pop(email);
    } else {
      context.go(RouteConstants.login);
    }
  }

  void _sendCode() {
    final notifier = ref.read(accountRecoveryProvider.notifier);
    if (notifier.sendCode()) {
      _code.clear();
      // The code field only becomes enabled after this rebuild, so
      // requesting focus must wait for that frame or it's silently dropped.
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted) _codeFocus.requestFocus();
      });
    } else {
      _emailFocus.requestFocus();
    }
  }

  void _verifyCode() {
    ref.read(accountRecoveryProvider.notifier).verifyCode(_code.text);
    if (ref.read(accountRecoveryProvider).verified) {
      FocusScope.of(context).unfocus();
    }
  }

  void _previewReset() {
    if (!ref.read(accountRecoveryProvider).verified) return;
    setState(() {
      _passwordError = _password.text.length < 6
          ? '비밀번호를 6자 이상 입력해줘.'
          : _password.text != _confirmation.text
              ? '비밀번호가 서로 달라. 다시 확인해줘.'
              : null;
    });
    if (_passwordError != null) return;
    FocusScope.of(context).unfocus();
    _password.clear();
    _confirmation.clear();
    ScaffoldMessenger.of(context).showSnackBar(const SnackBar(
      content: Text('미리보기 완료! 실제 비밀번호는 변경되지 않았어.'),
    ));
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(accountRecoveryProvider);
    return Theme(
      data: ThemeData.dark().copyWith(
        textTheme: ThemeData.dark().textTheme.apply(fontFamily: 'Pretendard'),
        scaffoldBackgroundColor: AppColors.black,
      ),
      child: Scaffold(
        backgroundColor: AppColors.black,
        body: SafeArea(
          child: LayoutBuilder(builder: (context, constraints) {
            return SingleChildScrollView(
              keyboardDismissBehavior: ScrollViewKeyboardDismissBehavior.onDrag,
              padding: const EdgeInsets.symmetric(horizontal: 22),
              child: ConstrainedBox(
                constraints: BoxConstraints(minHeight: constraints.maxHeight),
                child: IntrinsicHeight(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      SizedBox(
                        height: 60,
                        child: Stack(alignment: Alignment.center, children: [
                          const Text('계정 찾기',
                              style: TextStyle(
                                  fontSize: 18, fontWeight: FontWeight.w800)),
                          Align(
                            alignment: Alignment.centerLeft,
                            child: IconButton(
                              tooltip: '로그인으로 돌아가기',
                              onPressed: () => _back(),
                              icon: const Icon(Icons.arrow_back_ios_new_rounded,
                                  size: 22),
                            ),
                          ),
                        ]),
                      ),
                      _tabs(),
                      const SizedBox(height: 24),
                      Text(
                        _resetMode ? '비밀번호 까먹었어?' : '아이디 까먹었어?',
                        style: const TextStyle(
                            fontSize: 27,
                            height: 1.15,
                            fontWeight: FontWeight.w900,
                            letterSpacing: -1),
                      ),
                      const SizedBox(height: 20),
                      Row(
                          crossAxisAlignment: CrossAxisAlignment.end,
                          children: [
                            Image.asset(
                              state.sent || _resetMode
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
                              padding: const EdgeInsets.symmetric(
                                  horizontal: 18, vertical: 14),
                              decoration: const BoxDecoration(
                                color: AppColors.purple,
                                borderRadius: BorderRadius.only(
                                  topLeft: Radius.circular(22),
                                  topRight: Radius.circular(22),
                                  bottomRight: Radius.circular(22),
                                  bottomLeft: Radius.circular(3),
                                ),
                              ),
                              child: Text(
                                state.verified
                                    ? '인증 완료! 이제 확인해봐!'
                                    : '이메일만 인증하면 바로 찾아줄게!',
                                style: const TextStyle(
                                    color: AppColors.black,
                                    fontWeight: FontWeight.w800,
                                    fontSize: 14),
                              ),
                            )),
                          ]),
                      const SizedBox(height: 16),
                      const Text('미리보기 · 실제 이메일은 발송되지 않아. 테스트 코드: 418320',
                          style: TextStyle(
                              color: Color(0xFF999999), fontSize: 11)),
                      const SizedBox(height: 12),
                      _label('이메일'),
                      Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Expanded(
                                child: _field(
                              controller: _email,
                              focus: _emailFocus,
                              hint: '이메일을 입력해줘',
                              keyboard: TextInputType.emailAddress,
                              onChanged: (value) {
                                ref
                                    .read(accountRecoveryProvider.notifier)
                                    .changeEmail(value);
                                _code.clear();
                                _password.clear();
                                _confirmation.clear();
                                setState(() => _passwordError = null);
                              },
                            )),
                            const SizedBox(width: 12),
                            _statusButton(
                                label: state.sent ? '전송 완료' : '인증하기',
                                complete: state.sent,
                                onTap: state.sent ? null : _sendCode),
                          ]),
                      const SizedBox(height: 14),
                      _label('인증 코드'),
                      Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Expanded(
                                child: _field(
                              controller: _code,
                              focus: _codeFocus,
                              hint: '인증 코드 6자리',
                              enabled: state.sent && !state.verified,
                              keyboard: TextInputType.number,
                              formatters: [
                                FilteringTextInputFormatter.digitsOnly,
                                LengthLimitingTextInputFormatter(6)
                              ],
                              onChanged: (_) => setState(() {}),
                            )),
                            const SizedBox(width: 12),
                            _statusButton(
                                label: state.verified ? '인증 완료' : '인증하기',
                                complete: state.verified,
                                onTap: state.sent &&
                                        !state.verified &&
                                        _code.text.length == 6
                                    ? _verifyCode
                                    : null),
                          ]),
                      if (state.error != null) ...[
                        const SizedBox(height: 10),
                        Text(state.error!,
                            style: const TextStyle(
                                color: AppColors.red, fontSize: 13)),
                      ],
                      const SizedBox(height: 20),
                      if (!_resetMode && state.verified) _result(state),
                      if (_resetMode && state.verified) ...[
                        _label('새 비밀번호'),
                        _field(
                            controller: _password,
                            focus: _passwordFocus,
                            hint: '6자 이상 입력해줘',
                            obscure: _hidePassword,
                            suffix: _eye(
                                _hidePassword,
                                () => setState(
                                    () => _hidePassword = !_hidePassword))),
                        const SizedBox(height: 14),
                        _label('새 비밀번호 확인'),
                        _field(
                            controller: _confirmation,
                            focus: _confirmationFocus,
                            hint: '비밀번호를 한 번 더 입력해줘',
                            obscure: _hideConfirmation,
                            suffix: _eye(
                                _hideConfirmation,
                                () => setState(() =>
                                    _hideConfirmation = !_hideConfirmation))),
                        if (_passwordError != null)
                          Padding(
                            padding: const EdgeInsets.only(top: 10),
                            child: Text(_passwordError!,
                                style: const TextStyle(
                                    color: AppColors.red, fontSize: 13)),
                          ),
                      ],
                      const SizedBox(height: 32),
                      const Spacer(),
                      _bottomButton(
                        label: _resetMode ? '비밀번호 재설정하기' : '이 아이디로 로그인',
                        onTap: !state.verified
                            ? null
                            : _resetMode
                                ? _previewReset
                                : () => _back(email: state.email),
                        primary: true,
                      ),
                      const SizedBox(height: 10),
                      _bottomButton(
                          label: _resetMode ? '아이디 찾기' : '비밀번호 재설정하기',
                          onTap: () => _changeMode(!_resetMode),
                          primary: false),
                      const SizedBox(height: 16),
                    ],
                  ),
                ),
              ),
            );
          }),
        ),
      ),
    );
  }

  Widget _tabs() => Container(
        padding: const EdgeInsets.all(4),
        decoration: BoxDecoration(
            color: AppColors.grey, borderRadius: BorderRadius.circular(18)),
        child: Row(children: [
          for (final reset in [false, true])
            Expanded(
                child: TextButton(
              onPressed: () => _changeMode(reset),
              style: TextButton.styleFrom(
                backgroundColor:
                    _resetMode == reset ? AppColors.green : Colors.transparent,
                foregroundColor: _resetMode == reset
                    ? AppColors.black
                    : const Color(0xFF888888),
                minimumSize: const Size(0, 48),
                shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(14)),
              ),
              child: Text(reset ? '비밀번호 재설정' : '아이디 찾기',
                  style: const TextStyle(
                      fontSize: 16, fontWeight: FontWeight.w800)),
            )),
        ]),
      );

  Widget _label(String text) => Padding(
        padding: const EdgeInsets.only(bottom: 7),
        child: Text(text,
            style: const TextStyle(
                color: Color(0xFF888888),
                fontSize: 13,
                fontWeight: FontWeight.w600)),
      );

  Widget _field({
    required TextEditingController controller,
    required FocusNode focus,
    required String hint,
    bool enabled = true,
    bool obscure = false,
    TextInputType? keyboard,
    List<TextInputFormatter>? formatters,
    ValueChanged<String>? onChanged,
    Widget? suffix,
  }) =>
      SizedBox(
        height: 52,
        child: TextField(
          controller: controller,
          focusNode: focus,
          enabled: enabled,
          obscureText: obscure,
          keyboardType: keyboard,
          inputFormatters: formatters,
          onChanged: onChanged,
          autocorrect: false,
          enableSuggestions: false,
          textAlignVertical: TextAlignVertical.center,
          style: const TextStyle(color: AppColors.white, fontSize: 16),
          cursorColor: AppColors.green,
          decoration: InputDecoration(
            isDense: true,
            hintText: hint,
            hintStyle: const TextStyle(color: Color(0xFF888888), fontSize: 14),
            filled: true,
            fillColor: AppColors.grey,
            suffixIcon: suffix,
            contentPadding:
                const EdgeInsets.symmetric(horizontal: 18, vertical: 16),
            border: _border(const Color(0xFF2B2B2B)),
            enabledBorder: _border(const Color(0xFF2B2B2B)),
            disabledBorder: _border(const Color(0xFF2B2B2B)),
            focusedBorder: _border(AppColors.green),
          ),
        ),
      );

  OutlineInputBorder _border(Color color) => OutlineInputBorder(
        borderRadius: BorderRadius.circular(18),
        borderSide: BorderSide(color: color),
      );

  Widget _eye(bool hidden, VoidCallback onTap) => IconButton(
        tooltip: hidden ? '비밀번호 표시' : '비밀번호 숨기기',
        onPressed: onTap,
        icon: Icon(Icons.visibility_outlined,
            size: 22,
            color: hidden ? const Color(0xFF888888) : AppColors.green),
      );

  Widget _statusButton(
          {required String label,
          required bool complete,
          VoidCallback? onTap}) =>
      SizedBox(
        width: 90,
        height: 52,
        child: OutlinedButton(
          onPressed: onTap,
          style: OutlinedButton.styleFrom(
            padding: EdgeInsets.zero,
            backgroundColor: complete || onTap == null
                ? Colors.transparent
                : AppColors.purple,
            foregroundColor: AppColors.black,
            disabledForegroundColor:
                complete ? AppColors.purple : const Color(0xFF666666),
            side: BorderSide(
                color: complete
                    ? AppColors.purple
                    : onTap == null
                        ? const Color(0xFF333333)
                        : Colors.transparent),
            shape:
                RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
          ),
          child: Row(mainAxisAlignment: MainAxisAlignment.center, children: [
            if (complete)
              const Padding(
                  padding: EdgeInsets.only(right: 4),
                  child: Icon(Icons.check_rounded, size: 17)),
            Text(label,
                style:
                    const TextStyle(fontSize: 13, fontWeight: FontWeight.w800)),
          ]),
        ),
      );

  Widget _result(AccountRecoveryState state) => Container(
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(
            color: AppColors.green, borderRadius: BorderRadius.circular(28)),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Text('찾은 아이디 · 미리보기',
              style: TextStyle(
                  color: Color(0xFF536E29),
                  fontSize: 13,
                  fontWeight: FontWeight.w700)),
          const SizedBox(height: 8),
          Text(state.maskedId,
              style: const TextStyle(
                  color: AppColors.black,
                  fontSize: 26,
                  fontWeight: FontWeight.w900)),
          const SizedBox(height: 8),
          const Text('가입일은 계정 연동 후 표시돼.',
              style: TextStyle(color: Color(0xFF536E29), fontSize: 12)),
        ]),
      );

  Widget _bottomButton(
          {required String label,
          required VoidCallback? onTap,
          required bool primary}) =>
      SizedBox(
        height: 56,
        child: ElevatedButton(
          onPressed: onTap,
          style: ElevatedButton.styleFrom(
            elevation: 0,
            backgroundColor: primary ? AppColors.white : AppColors.grey,
            foregroundColor: primary ? AppColors.black : AppColors.white,
            disabledBackgroundColor: AppColors.grey,
            disabledForegroundColor: const Color(0xFF666666),
            shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(22),
                side: primary
                    ? BorderSide.none
                    : const BorderSide(color: Color(0xFF2B2B2B))),
          ),
          child: Text(label,
              style:
                  const TextStyle(fontSize: 17, fontWeight: FontWeight.w800)),
        ),
      );
}
