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
  final _loginIdCtrl = TextEditingController();
  final _loginPasswordCtrl = TextEditingController();
  bool _obscureLogin = true;
  bool _autoLogin = false;

  // Sign-up
  final _usernameCtrl = TextEditingController();
  final _signUpPasswordCtrl = TextEditingController();
  final _confirmPasswordCtrl = TextEditingController();
  final _nameCtrl = TextEditingController();
  final _heightCtrl = TextEditingController();
  final _weightCtrl = TextEditingController();

  String? _selectedGender;
  String? _selectedGoal;
  bool _idChecked = false;
  bool _idAvailable = false;
  bool _obscurePassword = true;
  bool _obscureConfirm = true;
  bool _isCheckingId = false;

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
    _loginIdCtrl.dispose();
    _loginPasswordCtrl.dispose();
    _usernameCtrl.dispose();
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
        username: _usernameCtrl.text.trim(),
        password: _signUpPasswordCtrl.text.trim(),
        name: _nameCtrl.text.trim(),
        gender: _selectedGender,
        heightCm: double.tryParse(_heightCtrl.text),
        weightKg: double.tryParse(_weightCtrl.text),
        workoutGoal: _selectedGoal,
      );
    } else {
      if (!(_loginFormKey.currentState?.validate() ?? false)) return;
      await auth.login(
          _loginIdCtrl.text.trim(), _loginPasswordCtrl.text.trim());
      if (auth.isLoggedIn) {
        ref.read(autoLoginProvider.notifier).state = _autoLogin;
      }
    }
  }

  Future<void> _checkDuplicate() async {
    if (_usernameCtrl.text.trim().isEmpty) return;
    setState(() => _isCheckingId = true);
    await Future.delayed(const Duration(milliseconds: 700));
    setState(() {
      _isCheckingId = false;
      _idChecked = true;
      _idAvailable = true;
    });
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

    return Scaffold(
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
                  const SizedBox(height: 60),
                  _buildLogo(s),
                  const SizedBox(height: 48),
                  _buildHeadline(theme, s),
                  const SizedBox(height: 32),
                  if (_isSignUp)
                    _buildSignUpForm(s, auth, theme)
                  else
                    _buildLoginForm(s, auth, theme),
                  const SizedBox(height: 20),
                  _buildToggle(theme, s),
                  const SizedBox(height: 32),
                  _buildDivider(theme),
                  const SizedBox(height: 20),
                  Center(
                    child: Text(
                      s.poweredBy,
                      style: theme.textTheme.bodySmall?.copyWith(
                        color: theme.colorScheme.onSurface
                            .withValues(alpha: 0.35),
                      ),
                    ),
                  ),
                  const SizedBox(height: 40),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }

  // ── Login Form ─────────────────────────────────────────────────────────────
  Widget _buildLoginForm(s, AuthNotifier auth, ThemeData theme) {
    return Form(
      key: _loginFormKey,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _buildField(
            controller: _loginIdCtrl,
            label: s.username,
            icon: Icons.person_outline_rounded,
            validator: (v) =>
                v == null || v.isEmpty ? s.idRequired : null,
          ),
          const SizedBox(height: 16),
          _buildField(
            controller: _loginPasswordCtrl,
            label: s.password,
            icon: Icons.lock_outline_rounded,
            obscureText: _obscureLogin,
            suffixIcon: IconButton(
              icon: Icon(
                _obscureLogin
                    ? Icons.visibility_off_outlined
                    : Icons.visibility_outlined,
                size: 20,
              ),
              onPressed: () =>
                  setState(() => _obscureLogin = !_obscureLogin),
            ),
            validator: (v) =>
                v == null || v.length < 6 ? s.minSixChars : null,
          ),
          const SizedBox(height: 4),
          Row(
            children: [
              SizedBox(
                width: 24,
                height: 24,
                child: Checkbox(
                  value: _autoLogin,
                  onChanged: (v) =>
                      setState(() => _autoLogin = v ?? false),
                  activeColor: AppColors.primary,
                  shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(4)),
                  materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
                ),
              ),
              const SizedBox(width: 8),
              GestureDetector(
                onTap: () =>
                    setState(() => _autoLogin = !_autoLogin),
                child: Text(
                  s.locale == 'ko' ? '자동 로그인' : 'Remember me',
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: Theme.of(context)
                            .colorScheme
                            .onSurface
                            .withValues(alpha: 0.65),
                      ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          if (auth.error != null) _buildErrorBox(auth.error!),
          const SizedBox(height: 20),
          _buildCTA(auth, s),
        ],
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
          // ─ 계정 정보 ────────────────────────────────────────────────────────
          _sectionLabel(s.accountInfo, theme),
          const SizedBox(height: 12),

          // 아이디 + 중복확인
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: TextFormField(
                  controller: _usernameCtrl,
                  onChanged: (_) => setState(() {
                    _idChecked = false;
                    _idAvailable = false;
                  }),
                  decoration: InputDecoration(
                    labelText: s.username,
                    prefixIcon: const Icon(
                        Icons.person_outline_rounded,
                        size: 20),
                    suffixIcon: _idChecked
                        ? Icon(
                            _idAvailable
                                ? Icons.check_circle_rounded
                                : Icons.cancel_rounded,
                            color: _idAvailable
                                ? AppColors.scoreExcellent
                                : AppColors.error,
                            size: 20,
                          )
                        : null,
                  ),
                  validator: (v) {
                    if (v == null || v.isEmpty) return s.idRequired;
                    if (!_idChecked) return s.duplicateCheckRequired;
                    if (!_idAvailable) return s.duplicateTaken;
                    return null;
                  },
                ),
              ),
              const SizedBox(width: 8),
              Padding(
                padding: const EdgeInsets.only(top: 4),
                child: _isCheckingId
                    ? const SizedBox(
                        width: 80,
                        height: 52,
                        child: Center(
                          child: SizedBox(
                            width: 20,
                            height: 20,
                            child: CircularProgressIndicator(
                                strokeWidth: 2),
                          ),
                        ),
                      )
                    : OutlinedButton(
                        onPressed: _checkDuplicate,
                        style: OutlinedButton.styleFrom(
                          minimumSize: const Size(80, 52),
                          shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(12)),
                          side:
                              const BorderSide(color: AppColors.primary),
                        ),
                        child: Text(
                          s.checkDuplicate,
                          style: const TextStyle(
                              color: AppColors.primary, fontSize: 13),
                        ),
                      ),
              ),
            ],
          ),
          if (_idChecked)
            Padding(
              padding: const EdgeInsets.only(top: 6, left: 4),
              child: Text(
                _idAvailable ? s.duplicateAvailable : s.duplicateTaken,
                style: TextStyle(
                  color: _idAvailable
                      ? AppColors.scoreExcellent
                      : AppColors.error,
                  fontSize: 12,
                ),
              ),
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
            validator: (v) =>
                v == null || v.length < 6 ? s.minSixChars : null,
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
              if (v != _signUpPasswordCtrl.text) {
                return s.passwordMismatch;
              }
              return null;
            },
          ),
          const SizedBox(height: 28),

          // ─ 개인 정보 ────────────────────────────────────────────────────────
          _sectionLabel(s.personalInfo, theme),
          const SizedBox(height: 12),

          // 이름
          _buildField(
            controller: _nameCtrl,
            label: s.fullName,
            icon: Icons.badge_outlined,
            validator: (v) =>
                v == null || v.isEmpty ? s.nameRequired : null,
          ),
          const SizedBox(height: 16),

          // 성별 (선택)
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
                    _selectedGender =
                        _selectedGender == 'male' ? null : 'male'),
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

          // ─ 신체 정보 ────────────────────────────────────────────────────────
          _sectionLabel(s.bodyStats, theme),
          const SizedBox(height: 12),
          Row(
            children: [
              Expanded(
                child: _buildField(
                  controller: _heightCtrl,
                  label: s.heightCm,
                  icon: Icons.height_rounded,
                  keyboardType: const TextInputType.numberWithOptions(
                      decimal: true),
                  inputFormatters: [
                    FilteringTextInputFormatter.allow(
                        RegExp(r'[\d.]'))
                  ],
                  validator: (v) =>
                      v == null || v.isEmpty ? s.required : null,
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: _buildField(
                  controller: _weightCtrl,
                  label: s.weightKg,
                  icon: Icons.monitor_weight_outlined,
                  keyboardType: const TextInputType.numberWithOptions(
                      decimal: true),
                  inputFormatters: [
                    FilteringTextInputFormatter.allow(
                        RegExp(r'[\d.]'))
                  ],
                  validator: (v) =>
                      v == null || v.isEmpty ? s.required : null,
                ),
              ),
            ],
          ),
          const SizedBox(height: 28),

          // ─ 운동 목적 ────────────────────────────────────────────────────────
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
          if (auth.error != null) _buildErrorBox(auth.error!),
          const SizedBox(height: 28),
          _buildCTA(auth, s),
        ],
      ),
    );
  }

  // ── Helpers ────────────────────────────────────────────────────────────────
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
          style: theme.textTheme.titleSmall
              ?.copyWith(fontWeight: FontWeight.w700),
        ),
      ],
    );
  }

  Widget _buildErrorBox(String error) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: AppColors.error.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(10),
        border:
            Border.all(color: AppColors.error.withValues(alpha: 0.3)),
      ),
      child: Row(
        children: [
          const Icon(Icons.error_outline,
              color: AppColors.error, size: 18),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              error,
              style: const TextStyle(
                  color: AppColors.error, fontSize: 13),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildLogo(s) {
    return Row(
      children: [
        Container(
          width: 48,
          height: 48,
          decoration: BoxDecoration(
            gradient: AppColors.primaryGradient,
            borderRadius: BorderRadius.circular(14),
          ),
          child: const Icon(Icons.fitness_center_rounded,
              color: Colors.white, size: 26),
        ),
        const SizedBox(width: 12),
        Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'BPT',
              style: TextStyle(
                fontSize: 22,
                fontWeight: FontWeight.w800,
                letterSpacing: 1.5,
                color: AppColors.primary,
              ),
            ),
            Text(
              s.appTagline,
              style: const TextStyle(
                  fontSize: 11,
                  color: AppColors.lightTextSecondary),
            ),
          ],
        ),
      ],
    );
  }

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

  Widget _buildCTA(AuthNotifier auth, s) {
    return SizedBox(
      width: double.infinity,
      child: ElevatedButton(
        onPressed: auth.isLoading ? null : () => _submit(s),
        child: auth.isLoading
            ? const SizedBox(
                height: 20,
                width: 20,
                child: CircularProgressIndicator(
                    strokeWidth: 2.5, color: Colors.white),
              )
            : Text(_isSignUp ? s.createAccount : s.signIn),
      ),
    );
  }

  Widget _buildToggle(ThemeData theme, s) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        Text(
          _isSignUp ? s.alreadyHaveAccount : s.noAccount,
          style: theme.textTheme.bodyMedium?.copyWith(
            color:
                theme.colorScheme.onSurface.withValues(alpha: 0.55),
          ),
        ),
        GestureDetector(
          onTap: _toggleMode,
          child: Text(
            _isSignUp ? s.signIn : s.signUp,
            style: const TextStyle(
              color: AppColors.primary,
              fontWeight: FontWeight.w700,
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildDivider(ThemeData theme) {
    return Row(
      children: [
        Expanded(child: Divider(color: theme.dividerColor)),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 12),
          child: Text(
            'or',
            style: TextStyle(
                color: theme.colorScheme.onSurface.withValues(alpha: 0.4),
                fontSize: 13),
          ),
        ),
        Expanded(child: Divider(color: theme.dividerColor)),
      ],
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
