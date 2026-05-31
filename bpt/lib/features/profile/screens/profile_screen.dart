import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:cloud_firestore/cloud_firestore.dart';
import '../../../core/i18n/locale_provider.dart';
import '../../../core/theme/app_colors.dart';
import '../../../features/auth/providers/auth_provider.dart';
import '../../../features/home/providers/home_provider.dart';
import '../providers/profile_provider.dart';

class ProfileScreen extends ConsumerWidget {
  const ProfileScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final s = ref.watch(appStringsProvider);
    final user = ref.watch(profileUserProvider);

    if (user == null) return const Scaffold(body: Center(child: CircularProgressIndicator()));

    return Scaffold(
      appBar: AppBar(title: Text(s.profile)),
      body: SingleChildScrollView(
        padding: const EdgeInsets.fromLTRB(20, 0, 20, 100),
        child: Column(
          children: [
            const SizedBox(height: 20),
            _UserHeader(user: user, strings: s),
            const SizedBox(height: 24),
            _StatsRow(user: user, strings: s),
            const SizedBox(height: 24),
            _SettingsSection(strings: s),
            const SizedBox(height: 24),
            _WorkoutHistorySection(strings: s),
            const SizedBox(height: 24),
            _LogoutButton(strings: s),
            const SizedBox(height: 40),
          ],
        ),
      ),
    );
  }
}

// ── User Header ────────────────────────────────────────────────────────────
class _UserHeader extends ConsumerWidget {
  const _UserHeader({required this.user, required this.strings});
  final dynamic user;
  final dynamic strings;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;
    final s = strings;

    return Container(
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        color: isDark ? AppColors.darkCard : AppColors.lightCard,
        borderRadius: BorderRadius.circular(20),
      ),
      child: Column(
        children: [
          Container(
            width: 80,
            height: 80,
            decoration: const BoxDecoration(
              gradient: AppColors.primaryGradient,
              shape: BoxShape.circle,
            ),
            child: Center(
              child: Text(
                user.avatarInitials,
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 28,
                  fontWeight: FontWeight.w800,
                ),
              ),
            ),
          ),
          const SizedBox(height: 14),
          Text(
            user.name,
            style: theme.textTheme.titleLarge
                ?.copyWith(fontWeight: FontWeight.w800),
          ),
          const SizedBox(height: 4),
          Text(
            user.email,
            style: theme.textTheme.bodySmall?.copyWith(
              color: theme.colorScheme.onSurface.withValues(alpha: 0.5),
            ),
          ),
          const SizedBox(height: 16),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceEvenly,
            children: [
              _HeaderStat(
                value: user.age == 0 ? '-' : '${user.age}세',
                label: s.age,
              ),
              _HDivider(),
              _HeaderStat(
                value: user.weightKg == 0 ? '-' : '${user.weightKg.round()}kg',
                label: s.weight,
              ),
              _HDivider(),
              _HeaderStat(
                value: user.heightCm == 0 ? '-' : '${user.heightCm.round()}cm',
                label: s.height,
              ),
            ],
          ),
          const SizedBox(height: 16),
          OutlinedButton.icon(
            onPressed: () => _showEditSheet(context, ref, user, s),
            icon: const Icon(Icons.edit_outlined, size: 16),
            label: Text(s.editProfile),
            style: OutlinedButton.styleFrom(
              minimumSize: const Size(double.infinity, 40),
              shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(10)),
            ),
          ),
        ],
      ),
    );
  }

  void _showEditSheet(
      BuildContext context, WidgetRef ref, dynamic user, dynamic s) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      builder: (_) => _EditProfileSheet(user: user, strings: s),
    );
  }
}

// ── Edit Profile Bottom Sheet ──────────────────────────────────────────────
class _EditProfileSheet extends ConsumerStatefulWidget {
  const _EditProfileSheet({required this.user, required this.strings});
  final dynamic user;
  final dynamic strings;

  @override
  ConsumerState<_EditProfileSheet> createState() => _EditProfileSheetState();
}

class _EditProfileSheetState extends ConsumerState<_EditProfileSheet> {
  late final TextEditingController _nameCtrl;
  late final TextEditingController _ageCtrl;
  late final TextEditingController _weightCtrl;
  late final TextEditingController _heightCtrl;
  final _formKey = GlobalKey<FormState>();

  @override
  void initState() {
    super.initState();
    _nameCtrl = TextEditingController(text: widget.user.name as String);
    _ageCtrl = TextEditingController(text: '${widget.user.age}');
    _weightCtrl = TextEditingController(text: '${widget.user.weightKg}');
    _heightCtrl = TextEditingController(text: '${widget.user.heightCm}');
  }

  @override
  void dispose() {
    _nameCtrl.dispose();
    _ageCtrl.dispose();
    _weightCtrl.dispose();
    _heightCtrl.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    if (!_formKey.currentState!.validate()) return;
    final current = ref.read(profileUserProvider);
    if (current == null) return;
    final name = _nameCtrl.text.trim();
    final initials = name.isNotEmpty ? name[0].toUpperCase() : current.avatarInitials;
    final newAge = int.tryParse(_ageCtrl.text) ?? 0;
    final newWeight = double.tryParse(_weightCtrl.text) ?? 0.0;
    final newHeight = double.tryParse(_heightCtrl.text) ?? 0.0;

    final updated = current.copyWith(
      name: name,
      avatarInitials: initials,
      age: newAge,
      weightKg: newWeight,
      heightCm: newHeight,
    );

    final firebaseUser = FirebaseAuth.instance.currentUser;
    if (firebaseUser != null) {
      try {
        await FirebaseFirestore.instance
            .collection('users')
            .doc(firebaseUser.uid)
            .update({
          'name': name,
          'avatarInitials': initials,
          'age': newAge,
          'weightKg': newWeight,
          'heightCm': newHeight,
        });
      } catch (_) {
        // 네트워크/권한 오류여도 인메모리 상태는 항상 반영
      }
    }

    await ref.read(authNotifierProvider).updateProfile(updated);
    if (mounted) Navigator.pop(context);
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;
    final s = widget.strings;

    return Padding(
      padding: EdgeInsets.only(
        left: 24,
        right: 24,
        top: 24,
        bottom: MediaQuery.of(context).viewInsets.bottom + 32,
      ),
      child: Form(
        key: _formKey,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Text(s.editProfile,
                    style: theme.textTheme.titleMedium
                        ?.copyWith(fontWeight: FontWeight.w700)),
                const Spacer(),
                IconButton(
                  onPressed: () => Navigator.pop(context),
                  icon: const Icon(Icons.close_rounded),
                ),
              ],
            ),
            const SizedBox(height: 20),
            _Field(
              controller: _nameCtrl,
              label: s.name,
              icon: Icons.person_outline_rounded,
              isDark: isDark,
              validator: (v) =>
                  (v == null || v.trim().isEmpty) ? s.nameRequired : null,
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  child: _Field(
                    controller: _ageCtrl,
                    label: s.age,
                    icon: Icons.cake_outlined,
                    isDark: isDark,
                    keyboardType: TextInputType.number,
                    inputFormatters: [FilteringTextInputFormatter.digitsOnly],
                    validator: (v) {
                      if (v == null || v.isEmpty) return null;
                      final n = int.tryParse(v);
                      if (n == null || n < 0 || n > 120) return '0–120';
                      return null;
                    },
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: _Field(
                    controller: _weightCtrl,
                    label: '${s.weight} (kg)',
                    icon: Icons.monitor_weight_outlined,
                    isDark: isDark,
                    keyboardType:
                        const TextInputType.numberWithOptions(decimal: true),
                    validator: (v) {
                      final n = double.tryParse(v ?? '');
                      if (n == null || n < 20 || n > 300) return '20–300';
                      return null;
                    },
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            _Field(
              controller: _heightCtrl,
              label: '${s.height} (cm)',
              icon: Icons.height_rounded,
              isDark: isDark,
              keyboardType:
                  const TextInputType.numberWithOptions(decimal: true),
              validator: (v) {
                final n = double.tryParse(v ?? '');
                if (n == null || n < 50 || n > 250) return '50–250';
                return null;
              },
            ),
            const SizedBox(height: 24),
            ElevatedButton(
              onPressed: _save,
              style: ElevatedButton.styleFrom(
                minimumSize: const Size(double.infinity, 52),
                shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(14)),
              ),
              child: Text(s.save,
                  style: const TextStyle(fontWeight: FontWeight.w700)),
            ),
          ],
        ),
      ),
    );
  }
}

class _Field extends StatelessWidget {
  const _Field({
    required this.controller,
    required this.label,
    required this.icon,
    required this.isDark,
    this.keyboardType,
    this.inputFormatters,
    this.validator,
  });
  final TextEditingController controller;
  final String label;
  final IconData icon;
  final bool isDark;
  final TextInputType? keyboardType;
  final List<TextInputFormatter>? inputFormatters;
  final String? Function(String?)? validator;

  @override
  Widget build(BuildContext context) {
    return TextFormField(
      controller: controller,
      keyboardType: keyboardType,
      inputFormatters: inputFormatters,
      validator: validator,
      decoration: InputDecoration(
        labelText: label,
        prefixIcon: Icon(icon, size: 20),
        filled: true,
        fillColor: isDark
            ? AppColors.darkBackground
            : AppColors.lightInputFill,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: BorderSide.none,
        ),
        contentPadding:
            const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
      ),
    );
  }
}

class _HeaderStat extends StatelessWidget {
  const _HeaderStat({required this.value, required this.label});
  final String value;
  final String label;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Column(
      children: [
        Text(value,
            style: theme.textTheme.titleMedium
                ?.copyWith(fontWeight: FontWeight.w800)),
        const SizedBox(height: 2),
        Text(label,
            style: theme.textTheme.bodySmall?.copyWith(
              color: theme.colorScheme.onSurface.withValues(alpha: 0.45),
            )),
      ],
    );
  }
}

class _HDivider extends StatelessWidget {
  @override
  Widget build(BuildContext context) => Container(
        height: 30,
        width: 1,
        color: Theme.of(context).dividerColor,
      );
}

// ── Stats Row ──────────────────────────────────────────────────────────────
class _StatsRow extends ConsumerWidget {
  const _StatsRow({required this.user, required this.strings});
  final dynamic user;
  final dynamic strings;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final s = strings;
    final totalWorkouts = ref.watch(allRecordsProvider).length;
    final streak = ref.watch(streakDaysProvider);
    return Row(
      children: [
        Expanded(
            child: _StatCard(
                label: s.totalWorkouts,
                value: '$totalWorkouts',
                icon: Icons.fitness_center_rounded,
                color: AppColors.primary)),
        const SizedBox(width: 12),
        Expanded(
            child: _StatCard(
                label: s.dayStreak,
                value: '$streak',
                icon: Icons.local_fire_department_rounded,
                color: AppColors.secondary)),
        const SizedBox(width: 12),
        Expanded(
            child: _StatCard(
                label: s.since,
                value: '${user.joinedAt.year}',
                icon: Icons.calendar_month_outlined,
                color: AppColors.info)),
      ],
    );
  }
}

class _StatCard extends StatelessWidget {
  const _StatCard({
    required this.label,
    required this.value,
    required this.icon,
    required this.color,
  });
  final String label;
  final String value;
  final IconData icon;
  final Color color;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: isDark ? AppColors.darkCard : AppColors.lightCard,
        borderRadius: BorderRadius.circular(14),
      ),
      child: Column(
        children: [
          Icon(icon, color: color, size: 20),
          const SizedBox(height: 6),
          Text(value,
              style: TextStyle(
                  color: color,
                  fontWeight: FontWeight.w800,
                  fontSize: 16)),
          const SizedBox(height: 2),
          Text(
            label,
            style: theme.textTheme.labelSmall?.copyWith(
              color: theme.colorScheme.onSurface.withValues(alpha: 0.45),
              fontSize: 10,
            ),
            textAlign: TextAlign.center,
          ),
        ],
      ),
    );
  }
}

// ── Settings Section ───────────────────────────────────────────────────────
class _SettingsSection extends ConsumerWidget {
  const _SettingsSection({required this.strings});
  final dynamic strings;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;
    final s = strings;

    final notifications = ref.watch(notificationsEnabledProvider);
    final darkMode = ref.watch(darkModeEnabledProvider);
    final sound = ref.watch(soundEnabledProvider);
    final haptic = ref.watch(hapticEnabledProvider);
    final lang = ref.watch(selectedLanguageProvider);

    return Container(
      decoration: BoxDecoration(
        color: isDark ? AppColors.darkCard : AppColors.lightCard,
        borderRadius: BorderRadius.circular(16),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
            child: Text(s.settings,
                style: theme.textTheme.titleSmall
                    ?.copyWith(fontWeight: FontWeight.w700)),
          ),
          _LanguageTile(
            label: s.language,
            current: lang,
            onChanged: (v) =>
                ref.read(selectedLanguageProvider.notifier).state = v,
          ),
          Divider(height: 1, indent: 56, color: theme.dividerColor),
          _ToggleTile(
            icon: Icons.dark_mode_outlined,
            label: s.darkMode,
            value: darkMode,
            onChanged: (v) {
              ref.read(darkModeEnabledProvider.notifier).state = v;
              ref.read(themeModeProvider.notifier).state =
                  v ? ThemeMode.dark : ThemeMode.light;
            },
          ),
          Divider(height: 1, indent: 56, color: theme.dividerColor),
          _ToggleTile(
            icon: Icons.notifications_outlined,
            label: s.pushNotifications,
            value: notifications,
            onChanged: (v) =>
                ref.read(notificationsEnabledProvider.notifier).state = v,
          ),
          Divider(height: 1, indent: 56, color: theme.dividerColor),
          _ToggleTile(
            icon: Icons.volume_up_outlined,
            label: s.soundEffects,
            value: sound,
            onChanged: (v) =>
                ref.read(soundEnabledProvider.notifier).state = v,
          ),
          Divider(height: 1, indent: 56, color: theme.dividerColor),
          _ToggleTile(
            icon: Icons.vibration_rounded,
            label: s.hapticFeedback,
            value: haptic,
            isLast: true,
            onChanged: (v) =>
                ref.read(hapticEnabledProvider.notifier).state = v,
          ),
        ],
      ),
    );
  }
}

// ── Language Tile ──────────────────────────────────────────────────────────
class _LanguageTile extends StatelessWidget {
  const _LanguageTile({
    required this.label,
    required this.current,
    required this.onChanged,
  });
  final String label;
  final String current;
  final ValueChanged<String> onChanged;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return ListTile(
      leading: Container(
        padding: const EdgeInsets.all(8),
        decoration: BoxDecoration(
          color: AppColors.primary.withValues(alpha: 0.1),
          borderRadius: BorderRadius.circular(8),
        ),
        child: const Icon(Icons.language_rounded,
            color: AppColors.primary, size: 18),
      ),
      title: Text(label, style: theme.textTheme.bodyMedium),
      trailing: _LanguageToggle(current: current, onChanged: onChanged),
    );
  }
}

class _LanguageToggle extends StatelessWidget {
  const _LanguageToggle({required this.current, required this.onChanged});
  final String current;
  final ValueChanged<String> onChanged;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: Theme.of(context).brightness == Brightness.dark
            ? AppColors.darkBackground
            : AppColors.lightInputFill,
        borderRadius: BorderRadius.circular(10),
      ),
      padding: const EdgeInsets.all(3),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          _LangChip(
            label: '한국어',
            selected: current == 'ko',
            onTap: () => onChanged('ko'),
          ),
          const SizedBox(width: 3),
          _LangChip(
            label: 'EN',
            selected: current == 'en',
            onTap: () => onChanged('en'),
          ),
        ],
      ),
    );
  }
}

class _LangChip extends StatelessWidget {
  const _LangChip({
    required this.label,
    required this.selected,
    required this.onTap,
  });
  final String label;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
        decoration: BoxDecoration(
          color: selected ? AppColors.primary : Colors.transparent,
          borderRadius: BorderRadius.circular(7),
          boxShadow: selected
              ? [
                  BoxShadow(
                    color: AppColors.primary.withValues(alpha: 0.3),
                    blurRadius: 8,
                    offset: const Offset(0, 2),
                  )
                ]
              : null,
        ),
        child: Text(
          label,
          style: TextStyle(
            color: selected ? Colors.white : AppColors.lightTextSecondary,
            fontSize: 12,
            fontWeight: FontWeight.w700,
          ),
        ),
      ),
    );
  }
}

// ── Toggle Tile ────────────────────────────────────────────────────────────
class _ToggleTile extends StatelessWidget {
  const _ToggleTile({
    required this.icon,
    required this.label,
    required this.value,
    required this.onChanged,
    this.isLast = false,
  });
  final IconData icon;
  final String label;
  final bool value;
  final ValueChanged<bool> onChanged;
  final bool isLast;

  @override
  Widget build(BuildContext context) {
    return ListTile(
      leading: Container(
        padding: const EdgeInsets.all(8),
        decoration: BoxDecoration(
          color: AppColors.primary.withValues(alpha: 0.1),
          borderRadius: BorderRadius.circular(8),
        ),
        child: Icon(icon, color: AppColors.primary, size: 18),
      ),
      title: Text(label, style: Theme.of(context).textTheme.bodyMedium),
      trailing: Switch.adaptive(
        value: value,
        onChanged: onChanged,
        activeColor: AppColors.primary,
      ),
    );
  }
}

// ── Workout History ────────────────────────────────────────────────────────
class _WorkoutHistorySection extends ConsumerWidget {
  const _WorkoutHistorySection({required this.strings});
  final dynamic strings;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;
    final s = strings;
    final records = ref.watch(allRecordsProvider).take(4).toList();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(s.recentActivity,
            style: theme.textTheme.titleMedium
                ?.copyWith(fontWeight: FontWeight.w700)),
        const SizedBox(height: 12),
        Container(
          decoration: BoxDecoration(
            color: isDark ? AppColors.darkCard : AppColors.lightCard,
            borderRadius: BorderRadius.circular(16),
          ),
          child: records.isEmpty
              ? Padding(
                  padding: const EdgeInsets.symmetric(vertical: 28),
                  child: Center(
                    child: Text(
                      s.locale == 'ko' ? '아직 운동 기록이 없어요' : 'No workouts yet',
                      style: theme.textTheme.bodyMedium?.copyWith(
                        color: theme.colorScheme.onSurface.withValues(alpha: 0.4),
                      ),
                    ),
                  ),
                )
              : Column(
                  children: records.asMap().entries.map((e) {
                    final r = e.value;
                    final isLast = e.key == records.length - 1;
                    return Column(
                      children: [
                        ListTile(
                          leading: Container(
                            width: 40,
                            height: 40,
                            decoration: BoxDecoration(
                              color: AppColors.primary.withValues(alpha: 0.1),
                              borderRadius: BorderRadius.circular(10),
                            ),
                            child: const Icon(Icons.fitness_center_rounded,
                                color: AppColors.primary, size: 18),
                          ),
                          title: Text(r.exerciseName,
                              style: theme.textTheme.bodyMedium
                                  ?.copyWith(fontWeight: FontWeight.w600)),
                          subtitle: Text(
                            r.totalReps > 0
                                ? '${r.totalReps} ${s.reps}  •  ${r.durationFormatted}'
                                : r.durationFormatted,
                            style: TextStyle(
                              fontSize: 12,
                              color: theme.colorScheme.onSurface
                                  .withValues(alpha: 0.45),
                            ),
                          ),
                          trailing: Text(
                            '${r.postureScore.toInt()}%',
                            style: TextStyle(
                              color: r.postureScore >= 90
                                  ? AppColors.scoreExcellent
                                  : r.postureScore >= 75
                                      ? AppColors.scoreGood
                                      : AppColors.scoreFair,
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                        ),
                        if (!isLast)
                          Divider(
                              height: 1, indent: 56, color: theme.dividerColor),
                      ],
                    );
                  }).toList(),
                ),
        ),
      ],
    );
  }
}

// ── Logout ─────────────────────────────────────────────────────────────────
class _LogoutButton extends ConsumerWidget {
  const _LogoutButton({required this.strings});
  final dynamic strings;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final s = strings;
    return OutlinedButton.icon(
      onPressed: () {
        showDialog(
          context: context,
          builder: (dialogCtx) => AlertDialog(
            title: Text(s.signOutConfirmTitle),
            content: Text(s.signOutConfirmMsg),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(dialogCtx),
                child: Text(s.cancel),
              ),
              TextButton(
                onPressed: () async {
                  Navigator.pop(dialogCtx);
                  await ref.read(authNotifierProvider).logout();
                },
                child: Text(s.signOut,
                    style: const TextStyle(color: AppColors.error)),
              ),
            ],
          ),
        );
      },
      icon: const Icon(Icons.logout_rounded, color: AppColors.error),
      label: Text(s.signOut),
      style: OutlinedButton.styleFrom(
        foregroundColor: AppColors.error,
        side: const BorderSide(color: AppColors.error),
        minimumSize: const Size(double.infinity, 52),
        shape:
            RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
      ),
    );
  }
}
