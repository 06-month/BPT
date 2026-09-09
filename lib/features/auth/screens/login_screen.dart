import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/i18n/locale_provider.dart';
import '../../../core/theme/app_colors.dart';
import '../providers/auth_provider.dart';

class LoginScreen extends ConsumerStatefulWidget {
  const LoginScreen({super.key});

  @override
  ConsumerState<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends ConsumerState<LoginScreen>
    with SingleTickerProviderStateMixin {
  final _loginFormKey = GlobalKey<FormState>();
  final _signUpFormKey = GlobalKey<FormState>();

  // Login
  final _loginEmailCtrl = TextEditingController(); // username → email
  final _loginPasswordCtrl = TextEditingController();
  bool _obscureLogin = true;
  // 시안에서 자동 로그인 체크박스가 제거되어 기본값(false)으로 고정.
  // AuthNotifier.login(rememberMe:) 시그니처 호환을 위해 필드는 유지.
  final bool _autoLogin = false;

  // Sign-up
  final _emailCtrl = TextEditingController(); // username → email
  final _signUpPasswordCtrl = TextEditingController();
  final _confirmPasswordCtrl = TextEditingController();
  final _nameCtrl = TextEditingController();
  final _heightCtrl = TextEditingController();
  final _weightCtrl = TextEditingController();

  DateTime? _selectedBirthDate;
  String? _selectedGender;
  String? _selectedGoal;
  bool _obscurePassword = true;
  bool _obscureConfirm = true;

  bool _isSignUp = false;

  late final AnimationController _animCtrl;
  late final Animation<double> _fadeAnim;
  late final Animation<Offset> _slideAnim;

  @override
  void initState() {
    super.initState();
    _animCtrl = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 600),
    );
    _fadeAnim = CurvedAnimation(parent: _animCtrl, curve: Curves.easeOut);
    _slideAnim = Tween(begin: const Offset(0, 0.06), end: Offset.zero).animate(
      CurvedAnimation(parent: _animCtrl, curve: Curves.easeOutCubic),
    );
    _animCtrl.forward();
  }

  @override
  void dispose() {
    _animCtrl.dispose();
    _loginEmailCtrl.dispose();
    _loginPasswordCtrl.dispose();
    _emailCtrl.dispose();
    _signUpPasswordCtrl.dispose();
    _confirmPasswordCtrl.dispose();
    _nameCtrl.dispose();
    _heightCtrl.dispose();
    _weightCtrl.dispose();
    super.dispose();
  }

  Future<void> _submit(s) async {
    final auth = ref.read(authNotifierProvider);
    if (_isSignUp) {
      if (!(_signUpFormKey.currentState?.validate() ?? false)) return;
      if (_selectedGoal == null) return;
      await auth.signUp(
        email: _emailCtrl.text.trim(),
        password: _signUpPasswordCtrl.text.trim(),
        name: _nameCtrl.text.trim(),
        birthDate: _selectedBirthDate,
        gender: _selectedGender,
        heightCm: double.tryParse(_heightCtrl.text),
        weightKg: double.tryParse(_weightCtrl.text),
        workoutGoal: _selectedGoal,
      );
    } else {
      if (!(_loginFormKey.currentState?.validate() ?? false)) return;
      await auth.login(
        _loginEmailCtrl.text.trim(), // username → email
        _loginPasswordCtrl.text.trim(),
        rememberMe: _autoLogin,
      );
    }
  }

  void _toggleMode() {
    setState(() => _isSignUp = !_isSignUp);
    _animCtrl.forward(from: 0);
  }

  @override
  Widget build(BuildContext context) {
    final s = ref.watch(appStringsProvider);
    final auth = ref.watch(authNotifierProvider);
    final theme = Theme.of(context);

    // 회원가입 모드는 기존 폼 UI를 유지하고,
    // 로그인 모드만 신규 시안대로 재구성한다.
    if (_isSignUp) {
      return Scaffold(
        backgroundColor: AppColors.black,
        body: SafeArea(
          child: SingleChildScrollView(
            padding: const EdgeInsets.symmetric(horizontal: 28),
            child: FadeTransition(
              opacity: _fadeAnim,
              child: SlideTransition(
                position: _slideAnim,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const SizedBox(height: 40),
                    _buildBrand(),
                    const SizedBox(height: 24),
                    _buildHeadline(theme, s),
                    const SizedBox(height: 28),
                    _buildSignUpForm(s, auth, theme),
                    const SizedBox(height: 20),
                    _buildBottomSignUpToggle(s),
                    const SizedBox(height: 32),
                  ],
                ),
              ),
            ),
          ),
        ),
      );
    }

    return Theme(
      data: theme.copyWith(
        textTheme: theme.textTheme.apply(fontFamily: 'Pretendard'),
      ),
      child: Scaffold(
        backgroundColor: AppColors.black,
        body: SafeArea(
          child: LayoutBuilder(
            builder: (context, constraints) => SingleChildScrollView(
              keyboardDismissBehavior: ScrollViewKeyboardDismissBehavior.onDrag,
              padding: const EdgeInsets.symmetric(horizontal: 16),
              child: ConstrainedBox(
                constraints: BoxConstraints(minHeight: constraints.maxHeight),
                child: IntrinsicHeight(
                  child: FadeTransition(
                    opacity: _fadeAnim,
                    child: SlideTransition(
                      position: _slideAnim,
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const SizedBox(height: 8),
                          _buildBrand(),
                          const SizedBox(height: 2),
                          _buildHeroHeadline(s),
                          const SizedBox(height: 14),
                          _buildCharacterCard(s),
                          const SizedBox(height: 14),
                          _buildLoginForm(s, auth, theme),
                          const SizedBox(height: 28),
                          const Spacer(),
                          _buildBottomSignUpToggle(s),
                          const SizedBox(height: 12),
                        ],
                      ),
                    ),
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }

  // ── Brand mark (BPT) ─────────────────────────────────────────────────────
  Widget _buildBrand() {
    // w900이 Flutter 기본 최대 굵기라, 채운 글자 위에 stroke를 덧그려
    // 시각적으로 더 두껍게 보이도록 한다.
    return Stack(
      children: [
        const Text(
          'BPT',
          style: TextStyle(
            fontFamily: 'Pretendard',
            fontSize: 20,
            fontWeight: FontWeight.w900,
            letterSpacing: 3,
            color: AppColors.green,
          ),
        ),
        Text(
          'BPT',
          style: TextStyle(
            fontFamily: 'Pretendard',
            fontSize: 20,
            fontWeight: FontWeight.w900,
            letterSpacing: 3,
            foreground: Paint()
              ..style = PaintingStyle.stroke
              ..strokeWidth = 1.4
              ..strokeJoin = StrokeJoin.round
              ..color = AppColors.green,
          ),
        ),
      ],
    );
  }

  // ── Hero headline (시안: "자세는 내가 봐줄게, 넌 운동만 해") ────────────────
  Widget _buildHeroHeadline(s) {
    final isKo = s.locale == 'ko';
    if (isKo) {
      return RichText(
        text: const TextSpan(
          style: TextStyle(
            fontFamily: 'Pretendard',
            fontSize: 32,
            fontWeight: FontWeight.w900,
            height: 1.08,
            color: AppColors.white,
          ),
          children: [
            TextSpan(text: '자세는\n내가 봐줄게,\n'),
            TextSpan(
              text: '넌 운동만 해',
              style: TextStyle(color: AppColors.green),
            ),
          ],
        ),
      );
    }
    return RichText(
      text: const TextSpan(
        style: TextStyle(
          fontFamily: 'Pretendard',
          fontSize: 30,
          fontWeight: FontWeight.w900,
          height: 1.08,
          color: AppColors.white,
        ),
        children: [
          TextSpan(text: "I'll watch your form,\n"),
          TextSpan(
            text: 'you just work out',
            style: TextStyle(color: AppColors.green),
          ),
        ],
      ),
    );
  }

  // ── Character card (purple 배경 + 오리 캐릭터 + 말풍선 + 장식) ──────────────
  Widget _buildCharacterCard(s) {
    final isKo = s.locale == 'ko';
    return Center(
      child: AspectRatio(
        aspectRatio: 322 / 204,
        child: LayoutBuilder(
          builder: (context, constraints) {
            final w = constraints.maxWidth;
            final h = constraints.maxHeight;
            return ClipRRect(
              borderRadius: BorderRadius.circular(28),
              child: ColoredBox(
                color: AppColors.purple,
                child: Stack(
                  children: [
                    Positioned(
                      left: 0,
                      top: h * 0.02,
                      width: w,
                      height: w,
                      child: Image.asset(
                        'assets/images/character/character_greeting.png',
                        fit: BoxFit.contain,
                        excludeFromSemantics: true,
                      ),
                    ),
                    Positioned(
                      left: w * 0.02,
                      top: 0,
                      child: Transform.rotate(
                        angle: -10 * math.pi / 180,
                        child: Image.asset(
                          'assets/images/decoration/spark_pink.png',
                          width: w * 0.22,
                          height: w * 0.22,
                          excludeFromSemantics: true,
                        ),
                      ),
                    ),
                    Positioned(
                      right: w * 0.07,
                      top: h * 0.60,
                      child: Transform.rotate(
                        angle: -12 * math.pi / 180,
                        child: Image.asset(
                          'assets/images/decoration/heart_pink.png',
                          width: w * 0.21,
                          height: w * 0.21,
                          excludeFromSemantics: true,
                        ),
                      ),
                    ),
                    Positioned(
                      left: w * 0.05,
                      bottom: h * 0.07,
                      child: Transform.rotate(
                        angle: -3 * math.pi / 180,
                        child: Container(
                          padding: const EdgeInsets.symmetric(
                            horizontal: 30,
                            vertical: 10,
                          ),
                          decoration: BoxDecoration(
                            color: AppColors.black,
                            borderRadius: BorderRadius.circular(16),
                          ),
                          child: Text(
                            isKo ? '안녕! 난 코리야!' : "Hi! I'm Kory!",
                            style: const TextStyle(
                              fontFamily: 'Pretendard',
                              color: AppColors.white,
                              fontSize: 14,
                              fontWeight: FontWeight.w800,
                            ),
                          ),
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            );
          },
        ),
      ),
    );
  }

  // ── Bottom sign-up toggle (시안: "처음이야? 회원가입 하기") ──────────────────
  Widget _buildBottomSignUpToggle(s) {
    final isKo = s.locale == 'ko';
    return Center(
      child: GestureDetector(
        onTap: _toggleMode,
        behavior: HitTestBehavior.opaque,
        child: RichText(
          text: TextSpan(
            style: const TextStyle(fontFamily: 'Pretendard', fontSize: 14),
            children: [
              TextSpan(
                text: _isSignUp
                    ? (isKo ? '이미 계정이 있나요? ' : 'Already have an account? ')
                    : (isKo ? '처음이야? ' : 'First time? '),
                style: const TextStyle(
                  color: Color(0xFF8A8F94),
                  fontWeight: FontWeight.w500,
                ),
              ),
              TextSpan(
                text: _isSignUp
                    ? (isKo ? '로그인 하기' : 'Sign in')
                    : (isKo ? '회원가입 하기' : 'Sign up'),
                style: TextStyle(
                  color: _isSignUp ? AppColors.white : AppColors.green,
                  fontWeight: FontWeight.w800,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  // ── Login Form (시안 재구성) ────────────────────────────────────────────────
  Widget _buildLoginForm(s, AuthNotifier auth, ThemeData theme) {
    final isKo = s.locale == 'ko';
    return Form(
      key: _loginFormKey,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _buildLoginField(
            controller: _loginEmailCtrl,
            hint: isKo ? '아이디' : 'Email',
            keyboardType: TextInputType.emailAddress,
            validator: (v) {
              if (v == null || v.isEmpty) return s.idRequired;
              if (!v.contains('@')) return s.invalidEmail;
              return null;
            },
          ),
          const SizedBox(height: 10),
          _buildLoginField(
            controller: _loginPasswordCtrl,
            hint: '• • • • • • • •',
            obscureText: _obscureLogin,
            suffixIcon: IconButton(
              icon: Icon(
                _obscureLogin
                    ? Icons.visibility_outlined
                    : Icons.visibility_off_outlined,
                size: 22,
                // 비공개일 때는 회색, 표시할 때는 라임색으로 변한다.
                color:
                    _obscureLogin ? const Color(0xFF8A8F94) : AppColors.green,
              ),
              onPressed: () => setState(() => _obscureLogin = !_obscureLogin),
            ),
            validator: (v) => v == null || v.length < 6 ? s.minSixChars : null,
          ),
          const SizedBox(height: 10),
          Align(
            alignment: Alignment.centerRight,
            child: Text(
              isKo ? '아이디/비밀번호 찾기' : 'Find ID / Password',
              style: const TextStyle(
                color: Color(0xFF8A8F94),
                fontSize: 13,
                fontWeight: FontWeight.w500,
              ),
            ),
          ),
          const SizedBox(height: 18),
          if (auth.error != null) ...[
            _buildErrorBox(auth.error!, s),
            const SizedBox(height: 16),
          ],
          _buildStartButton(auth, s),
        ],
      ),
    );
  }

  // 시안 스타일 입력 필드: grey 배경, 큰 라운드, placeholder, 무테 포커스
  Widget _buildLoginField({
    required TextEditingController controller,
    required String hint,
    TextInputType? keyboardType,
    bool obscureText = false,
    Widget? suffixIcon,
    String? Function(String?)? validator,
  }) {
    return TextFormField(
      controller: controller,
      keyboardType: keyboardType,
      obscureText: obscureText,
      validator: validator,
      cursorColor: const Color(0xFF8A8F94),
      cursorWidth: 1.5,
      style: const TextStyle(
        color: AppColors.white,
        fontSize: 16,
        fontWeight: FontWeight.w500,
        letterSpacing: 0.2,
      ),
      decoration: InputDecoration(
        hintText: hint,
        hintStyle: const TextStyle(
          color: Color(0xFF7A7F84),
          fontSize: 16,
          fontWeight: FontWeight.w400,
        ),
        filled: true,
        fillColor: AppColors.grey,
        suffixIcon: suffixIcon,
        suffixIconColor: const Color(0xFF8A8F94),
        contentPadding:
            const EdgeInsets.symmetric(horizontal: 18, vertical: 14),
        // 시안: 입력창은 테두리 없이 배경색만으로 구분. 포커스 시에도 무테.
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(18),
          borderSide: const BorderSide(color: Color(0xFF2C2C2C)),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(18),
          borderSide: const BorderSide(color: Color(0xFF2C2C2C)),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(18),
          borderSide: const BorderSide(color: Color(0xFF2C2C2C)),
        ),
        errorBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(16),
          borderSide: const BorderSide(color: AppColors.red, width: 1.2),
        ),
        focusedErrorBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(16),
          borderSide: const BorderSide(color: AppColors.red, width: 1.2),
        ),
      ),
    );
  }

  // 시안 CTA: green 배경 + black 텍스트
  Widget _buildStartButton(AuthNotifier auth, s) {
    final isKo = s.locale == 'ko';
    final label = _isSignUp
        ? (isKo ? '회원가입 완료' : 'Create account')
        : (isKo ? '시작하기' : 'Get Started');
    return SizedBox(
      width: double.infinity,
      height: _isSignUp ? 60 : 58,
      child: ElevatedButton(
        onPressed: auth.isLoading ? null : () => _submit(s),
        style: ElevatedButton.styleFrom(
          backgroundColor: AppColors.green,
          foregroundColor: AppColors.black,
          disabledBackgroundColor: AppColors.green.withValues(alpha: 0.5),
          elevation: 0,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(_isSignUp ? 18 : 22),
          ),
        ),
        child: auth.isLoading
            ? const SizedBox(
                height: 22,
                width: 22,
                child: CircularProgressIndicator(
                    strokeWidth: 2.5, color: AppColors.black),
              )
            : Text(
                label,
                style: const TextStyle(
                  fontSize: 17,
                  fontWeight: FontWeight.w800,
                ),
              ),
      ),
    );
  }

  // ── Sign-up Form ───────────────────────────────────────────────────────────
  Widget _buildSignUpForm(s, AuthNotifier auth, ThemeData theme) {
    return Form(
      key: _signUpFormKey,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _sectionLabel(s.accountInfo, theme),
          const SizedBox(height: 12),

          // 이메일 (중복확인 버튼 제거 — Firebase가 자동 처리)
          _buildField(
            controller: _emailCtrl,
            label: s.email,
            icon: Icons.email_outlined,
            keyboardType: TextInputType.emailAddress,
            validator: (v) {
              if (v == null || v.isEmpty) return s.idRequired;
              if (!v.contains('@')) return s.invalidEmail;
              return null;
            },
          ),
          const SizedBox(height: 12),

          // 비밀번호
          _buildField(
            controller: _signUpPasswordCtrl,
            label: s.password,
            icon: Icons.lock_outline_rounded,
            obscureText: _obscurePassword,
            suffixIcon: IconButton(
              icon: Icon(
                _obscurePassword
                    ? Icons.visibility_off_outlined
                    : Icons.visibility_outlined,
                size: 20,
              ),
              onPressed: () =>
                  setState(() => _obscurePassword = !_obscurePassword),
            ),
            validator: (v) => v == null || v.length < 6 ? s.minSixChars : null,
          ),
          const SizedBox(height: 12),

          // 비밀번호 확인
          _buildField(
            controller: _confirmPasswordCtrl,
            label: s.confirmPassword,
            icon: Icons.lock_outline_rounded,
            obscureText: _obscureConfirm,
            suffixIcon: IconButton(
              icon: Icon(
                _obscureConfirm
                    ? Icons.visibility_off_outlined
                    : Icons.visibility_outlined,
                size: 20,
              ),
              onPressed: () =>
                  setState(() => _obscureConfirm = !_obscureConfirm),
            ),
            validator: (v) {
              if (v == null || v.isEmpty) return s.minSixChars;
              if (v != _signUpPasswordCtrl.text) return s.passwordMismatch;
              return null;
            },
          ),
          const SizedBox(height: 28),

          // 이하 개인정보/신체정보/운동목표 섹션은 기존과 동일
          _sectionLabel(s.personalInfo, theme),
          const SizedBox(height: 12),
          _buildField(
            controller: _nameCtrl,
            label: s.fullName,
            icon: Icons.badge_outlined,
            validator: (v) => v == null || v.isEmpty ? s.nameRequired : null,
          ),
          const SizedBox(height: 12),
          _DatePickerField(
            label: s.birthDate,
            selected: _selectedBirthDate,
            isKo: s.locale == 'ko',
            onPicked: (date) => setState(() => _selectedBirthDate = date),
          ),
          const SizedBox(height: 16),
          Text(
            s.gender,
            style: theme.textTheme.bodySmall?.copyWith(
              color: theme.colorScheme.onSurface.withValues(alpha: 0.6),
            ),
          ),
          const SizedBox(height: 8),
          Row(
            children: [
              _GenderChip(
                label: s.male,
                isSelected: _selectedGender == 'male',
                onTap: () => setState(() =>
                    _selectedGender = _selectedGender == 'male' ? null : 'male'),
              ),
              const SizedBox(width: 10),
              _GenderChip(
                label: s.female,
                isSelected: _selectedGender == 'female',
                onTap: () => setState(() =>
                    _selectedGender =
                        _selectedGender == 'female' ? null : 'female'),
              ),
            ],
          ),
          const SizedBox(height: 28),
          _sectionLabel(s.bodyStats, theme),
          const SizedBox(height: 12),
          Row(
            children: [
              Expanded(
                child: _buildField(
                  controller: _heightCtrl,
                  label: s.heightCm,
                  icon: Icons.height_rounded,
                  keyboardType:
                      const TextInputType.numberWithOptions(decimal: true),
                  inputFormatters: [
                    FilteringTextInputFormatter.allow(RegExp(r'[\d.]'))
                  ],
                  validator: (v) => v == null || v.isEmpty ? s.required : null,
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: _buildField(
                  controller: _weightCtrl,
                  label: s.weightKg,
                  icon: Icons.monitor_weight_outlined,
                  keyboardType:
                      const TextInputType.numberWithOptions(decimal: true),
                  inputFormatters: [
                    FilteringTextInputFormatter.allow(RegExp(r'[\d.]'))
                  ],
                  validator: (v) => v == null || v.isEmpty ? s.required : null,
                ),
              ),
            ],
          ),
          const SizedBox(height: 28),
          _sectionLabel(s.workoutGoal, theme),
          const SizedBox(height: 12),
          _GoalCard(
            label: s.goalDiet,
            icon: Icons.local_fire_department_rounded,
            color: const Color(0xFFFF6B35),
            isSelected: _selectedGoal == 'diet',
            onTap: () => setState(() => _selectedGoal = 'diet'),
          ),
          const SizedBox(height: 10),
          _GoalCard(
            label: s.goalStrength,
            icon: Icons.fitness_center_rounded,
            color: AppColors.primary,
            isSelected: _selectedGoal == 'strength',
            onTap: () => setState(() => _selectedGoal = 'strength'),
          ),
          const SizedBox(height: 10),
          _GoalCard(
            label: s.goalPosture,
            icon: Icons.self_improvement_rounded,
            color: const Color(0xFF8B5CF6),
            isSelected: _selectedGoal == 'posture',
            onTap: () => setState(() => _selectedGoal = 'posture'),
          ),
          const SizedBox(height: 12),
          if (auth.error != null) _buildErrorBox(auth.error!, s),
          const SizedBox(height: 28),
          _buildStartButton(auth, s),
        ],
      ),
    );
  }

  // ── Helpers (기존과 동일) ──────────────────────────────────────────────────
  Widget _sectionLabel(String label, ThemeData theme) {
    return Row(
      children: [
        Container(
          width: 3,
          height: 16,
          decoration: BoxDecoration(
            color: AppColors.primary,
            borderRadius: BorderRadius.circular(2),
          ),
        ),
        const SizedBox(width: 8),
        Text(
          label,
          style:
              theme.textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w700),
        ),
      ],
    );
  }

  String _localizeError(String code, s) {
    final isKo = s.locale == 'ko';
    switch (code) {
      case 'username_or_password_incorrect':
        return isKo ? '이메일 또는 비밀번호가 올바르지 않아요.' : 'Email or password is incorrect.';
      case 'username_already_exists':
        return isKo ? '이미 사용 중인 이메일이에요.' : 'This email is already in use.';
      case 'password_too_weak':
        return isKo ? '비밀번호가 너무 짧아요. 6자 이상 입력해주세요.' : 'Password is too weak.';
      case 'invalid_email':
        return isKo ? '올바른 이메일 형식이 아니에요.' : 'Invalid email format.';
      default:
        return isKo ? '오류가 발생했어요. 다시 시도해주세요.' : 'Something went wrong. Please try again.';
    }
  }

  Widget _buildErrorBox(String error, s) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: AppColors.error.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: AppColors.error.withValues(alpha: 0.3)),
      ),
      child: Row(
        children: [
          const Icon(Icons.error_outline, color: AppColors.error, size: 18),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              _localizeError(error, s),
              style: const TextStyle(color: AppColors.error, fontSize: 13),
            ),
          ),
        ],
      ),
    );
  }

  // _buildHeadline, _buildField 는 회원가입 폼에서 사용한다.

  Widget _buildHeadline(ThemeData theme, s) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          _isSignUp ? s.createAccount : s.welcomeBack,
          style: theme.textTheme.headlineMedium?.copyWith(
            fontWeight: FontWeight.w800,
            letterSpacing: -0.5,
          ),
        ),
        const SizedBox(height: 6),
        Text(
          _isSignUp ? s.signUpSubtitle : s.signInSubtitle,
          style: theme.textTheme.bodyMedium?.copyWith(
            color:
                theme.colorScheme.onSurface.withValues(alpha: 0.55),
          ),
        ),
      ],
    );
  }

  Widget _buildField({
    required TextEditingController controller,
    required String label,
    required IconData icon,
    TextInputType? keyboardType,
    bool obscureText = false,
    Widget? suffixIcon,
    List<TextInputFormatter>? inputFormatters,
    String? Function(String?)? validator,
  }) {
    return TextFormField(
      controller: controller,
      keyboardType: keyboardType,
      obscureText: obscureText,
      inputFormatters: inputFormatters,
      validator: validator,
      decoration: InputDecoration(
        labelText: label,
        prefixIcon: Icon(icon, size: 20),
        suffixIcon: suffixIcon,
      ),
    );
  }
}

// ── Gender Chip ────────────────────────────────────────────────────────────
class _GenderChip extends StatelessWidget {
  const _GenderChip({
    required this.label,
    required this.isSelected,
    required this.onTap,
  });
  final String label;
  final bool isSelected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 150),
        padding:
            const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
        decoration: BoxDecoration(
          color: isSelected
              ? AppColors.primary.withValues(alpha: 0.12)
              : Colors.transparent,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
            color: isSelected ? AppColors.primary : Colors.grey.withValues(alpha: 0.3),
            width: isSelected ? 2 : 1,
          ),
        ),
        child: Text(
          label,
          style: TextStyle(
            color: isSelected ? AppColors.primary : Colors.grey,
            fontWeight:
                isSelected ? FontWeight.w700 : FontWeight.w400,
            fontSize: 14,
          ),
        ),
      ),
    );
  }
}

// ── Goal Card ──────────────────────────────────────────────────────────────
class _GoalCard extends StatelessWidget {
  const _GoalCard({
    required this.label,
    required this.icon,
    required this.color,
    required this.isSelected,
    required this.onTap,
  });
  final String label;
  final IconData icon;
  final Color color;
  final bool isSelected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 150),
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
        decoration: BoxDecoration(
          color: isSelected
              ? color.withValues(alpha: 0.1)
              : (isDark ? AppColors.darkCard : AppColors.lightCard),
          borderRadius: BorderRadius.circular(14),
          border: Border.all(
            color: isSelected ? color : Colors.transparent,
            width: 2,
          ),
        ),
        child: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: color.withValues(alpha: 0.15),
                borderRadius: BorderRadius.circular(10),
              ),
              child: Icon(icon, color: color, size: 20),
            ),
            const SizedBox(width: 14),
            Text(
              label,
              style: TextStyle(
                color: isSelected ? color : null,
                fontWeight: isSelected ? FontWeight.w700 : FontWeight.w500,
                fontSize: 15,
              ),
            ),
            const Spacer(),
            if (isSelected)
              Icon(Icons.check_circle_rounded, color: color, size: 20),
          ],
        ),
      ),
    );
  }
}

// ── Date Picker Field ──────────────────────────────────────────────────────
class _DatePickerField extends StatelessWidget {
  const _DatePickerField({
    required this.label,
    required this.selected,
    required this.isKo,
    required this.onPicked,
  });
  final String label;
  final DateTime? selected;
  final bool isKo;
  final ValueChanged<DateTime> onPicked;

  String _format(DateTime d) {
    if (isKo) return '${d.year}년 ${d.month}월 ${d.day}일';
    final months = ['Jan','Feb','Mar','Apr','May','Jun',
                    'Jul','Aug','Sep','Oct','Nov','Dec'];
    return '${months[d.month - 1]} ${d.day}, ${d.year}';
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;

    return GestureDetector(
      onTap: () async {
        final now = DateTime.now();
        final picked = await showDatePicker(
          context: context,
          initialDate: selected ?? DateTime(now.year - 20),
          firstDate: DateTime(1900),
          lastDate: now,
          locale: isKo ? const Locale('ko') : const Locale('en'),
        );
        if (picked != null) onPicked(picked);
      },
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
        decoration: BoxDecoration(
          color: isDark ? const Color(0xFF1A1F2E) : const Color(0xFFF5F5F5),
          borderRadius: BorderRadius.circular(12),
        ),
        child: Row(
          children: [
            Icon(Icons.cake_outlined,
                size: 20,
                color: theme.colorScheme.onSurface.withValues(alpha: 0.55)),
            const SizedBox(width: 12),
            Expanded(
              child: Text(
                selected != null ? _format(selected!) : label,
                style: theme.textTheme.bodyMedium?.copyWith(
                  color: selected != null
                      ? theme.colorScheme.onSurface
                      : theme.colorScheme.onSurface.withValues(alpha: 0.45),
                ),
              ),
            ),
            Icon(Icons.calendar_today_outlined,
                size: 16,
                color: theme.colorScheme.onSurface.withValues(alpha: 0.4)),
          ],
        ),
      ),
    );
  }
}
