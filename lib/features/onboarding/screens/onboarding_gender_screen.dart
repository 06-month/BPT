import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/constants/route_constants.dart';
import '../../../core/theme/app_colors.dart';
import '../providers/onboarding_provider.dart';
import '../widgets/onboarding_scaffold.dart';

class OnboardingGenderScreen extends ConsumerWidget {
  const OnboardingGenderScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final gender = ref.watch(onboardingProvider).gender;
    final notifier = ref.read(onboardingProvider.notifier);

    return OnboardingScaffold(
      step: 1,
      totalSteps: 4,
      onBack: () => context.pop(),
      onNext: gender != null
          ? () => context.push(RouteConstants.onboardingBody)
          : null,
      body: [
        const Text('성별 알려줘!',
            style: TextStyle(
                fontSize: 27,
                height: 1.15,
                fontWeight: FontWeight.w900,
                letterSpacing: -1)),
        const SizedBox(height: 20),
        Row(
          children: [
            Expanded(
              child: _GenderCard(
                label: '남자',
                image: 'assets/images/character/man.png',
                selected: gender == Gender.male,
                onTap: () => notifier.selectGender(Gender.male),
              ),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: _GenderCard(
                label: '여자',
                image: 'assets/images/character/woman.png',
                selected: gender == Gender.female,
                onTap: () => notifier.selectGender(Gender.female),
              ),
            ),
          ],
        ),
        const SizedBox(height: 14),
        _PreferNotToSayButton(
          selected: gender == Gender.preferNotToSay,
          onTap: () => notifier.selectGender(Gender.preferNotToSay),
        ),
      ],
    );
  }
}

class _GenderCard extends StatelessWidget {
  const _GenderCard({
    required this.label,
    required this.image,
    required this.selected,
    required this.onTap,
  });

  final String label;
  final String image;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => GestureDetector(
        onTap: onTap,
        child: AspectRatio(
          aspectRatio: 155 / 230,
          child: Container(
            padding: const EdgeInsets.symmetric(vertical: 20),
            decoration: BoxDecoration(
              color: selected ? AppColors.green : AppColors.grey,
              borderRadius: BorderRadius.circular(24),
            ),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Expanded(
                  child: Image.asset(image,
                      fit: BoxFit.contain, excludeFromSemantics: true),
                ),
                const SizedBox(height: 12),
                Text(label,
                    style: TextStyle(
                        color: selected ? AppColors.black : AppColors.white,
                        fontWeight: FontWeight.w800,
                        fontSize: 16)),
              ],
            ),
          ),
        ),
      );
}

class _PreferNotToSayButton extends StatelessWidget {
  const _PreferNotToSayButton({required this.selected, required this.onTap});

  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => GestureDetector(
        onTap: onTap,
        child: Container(
          width: double.infinity,
          padding: const EdgeInsets.symmetric(vertical: 18),
          decoration: BoxDecoration(
            color: AppColors.grey,
            borderRadius: BorderRadius.circular(18),
            border: selected
                ? Border.all(color: AppColors.green, width: 1.5)
                : null,
          ),
          child: Text('선택하지 않음',
              textAlign: TextAlign.center,
              style: TextStyle(
                  color: selected ? AppColors.green : const Color(0xFF888888),
                  fontWeight: FontWeight.w700,
                  fontSize: 15)),
        ),
      );
}
