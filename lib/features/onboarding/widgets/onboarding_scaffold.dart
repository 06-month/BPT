import 'package:flutter/material.dart';

import '../../../core/theme/app_colors.dart';
import '../../auth/widgets/auth_dark_form.dart';

/// Shared layout for every onboarding step: a fixed back arrow + step
/// progress bar on top, scrollable [body] content in the middle, and a
/// pinned "다음" CTA at the bottom so it never needs scrolling to reach.
class OnboardingScaffold extends StatelessWidget {
  const OnboardingScaffold({
    super.key,
    required this.step,
    required this.totalSteps,
    required this.onBack,
    required this.body,
    required this.onNext,
    this.nextLabel = '다음',
  });

  final int step;
  final int totalSteps;
  final VoidCallback onBack;
  final List<Widget> body;
  final VoidCallback? onNext;
  final String nextLabel;

  @override
  Widget build(BuildContext context) => Theme(
        data: ThemeData.dark().copyWith(
          textTheme: ThemeData.dark().textTheme.apply(fontFamily: 'Pretendard'),
          scaffoldBackgroundColor: AppColors.black,
        ),
        child: Scaffold(
          backgroundColor: AppColors.black,
          body: SafeArea(
            child: GestureDetector(
              // Tapping anywhere that isn't a field/button (empty space,
              // labels, a disabled button) should still blur a focused
              // inline-edit field — see AuthScrollScaffold for the same fix.
              behavior: HitTestBehavior.opaque,
              onTap: () => FocusScope.of(context).unfocus(),
              child: Column(
                children: [
                  Padding(
                    padding: const EdgeInsets.fromLTRB(22, 4, 22, 0),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        SizedBox(
                          height: 40,
                          child: Align(
                            alignment: Alignment.centerLeft,
                            child: IconButton(
                              padding: EdgeInsets.zero,
                              tooltip: '뒤로 가기',
                              onPressed: onBack,
                              icon: const Icon(Icons.arrow_back_ios_new_rounded,
                                  size: 22),
                            ),
                          ),
                        ),
                        const SizedBox(height: 20),
                        Row(
                          children: [
                            for (var i = 0; i < totalSteps; i++) ...[
                              if (i > 0) const SizedBox(width: 6),
                              Expanded(
                                child: ClipRRect(
                                  borderRadius: BorderRadius.circular(3),
                                  child: LinearProgressIndicator(
                                    value: i < step ? 1 : 0,
                                    minHeight: 5,
                                    backgroundColor: AppColors.grey,
                                    valueColor: const AlwaysStoppedAnimation(
                                        AppColors.green),
                                  ),
                                ),
                              ),
                            ],
                          ],
                        ),
                        const SizedBox(height: 12),
                        Text('STEP $step / $totalSteps',
                            style: const TextStyle(
                                color: AppColors.green,
                                fontSize: 13,
                                fontWeight: FontWeight.w800,
                                letterSpacing: 0.5)),
                      ],
                    ),
                  ),
                  Expanded(
                    child: SingleChildScrollView(
                      padding: const EdgeInsets.fromLTRB(22, 12, 22, 16),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: body,
                      ),
                    ),
                  ),
                  Padding(
                    padding: const EdgeInsets.fromLTRB(22, 0, 22, 20),
                    child: SizedBox(
                      width: double.infinity,
                      child: AuthPillButton(
                        label: nextLabel,
                        onTap: onNext,
                        background: AppColors.green,
                        foreground: AppColors.black,
                        disabledBackground:
                            AppColors.green.withValues(alpha: 0.3),
                        disabledForeground:
                            AppColors.black.withValues(alpha: 0.5),
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      );
}
