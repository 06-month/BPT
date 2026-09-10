import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/constants/route_constants.dart';
import '../../../core/theme/app_colors.dart';
import '../providers/onboarding_provider.dart';
import '../widgets/onboarding_scaffold.dart';

const _heightMin = 140.0;
const _heightMax = 200.0;
const _weightMin = 35.0;
const _weightMax = 120.0;

class OnboardingBodyScreen extends ConsumerStatefulWidget {
  const OnboardingBodyScreen({super.key});

  @override
  ConsumerState<OnboardingBodyScreen> createState() =>
      _OnboardingBodyScreenState();
}

class _OnboardingBodyScreenState extends ConsumerState<OnboardingBodyScreen> {
  final _heightController = TextEditingController();
  final _weightController = TextEditingController();
  final _heightFocus = FocusNode();
  final _weightFocus = FocusNode();

  bool _editingHeight = false;
  bool _editingWeight = false;

  @override
  void initState() {
    super.initState();
    _heightFocus.addListener(() {
      if (!_heightFocus.hasFocus) _commitHeight();
    });
    _weightFocus.addListener(() {
      if (!_weightFocus.hasFocus) _commitWeight();
    });
  }

  @override
  void dispose() {
    _heightController.dispose();
    _weightController.dispose();
    _heightFocus.dispose();
    _weightFocus.dispose();
    super.dispose();
  }

  void _startEditingHeight(double current) {
    _heightController.text = current.round().toString();
    setState(() => _editingHeight = true);
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) _heightFocus.requestFocus();
    });
  }

  void _startEditingWeight(double current) {
    _weightController.text = current.toStringAsFixed(1);
    setState(() => _editingWeight = true);
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) _weightFocus.requestFocus();
    });
  }

  void _commitHeight() {
    if (!_editingHeight) return;
    final parsed = double.tryParse(_heightController.text);
    if (parsed != null) {
      ref
          .read(onboardingProvider.notifier)
          .setHeight(parsed.clamp(_heightMin, _heightMax));
    }
    setState(() => _editingHeight = false);
  }

  void _commitWeight() {
    if (!_editingWeight) return;
    final parsed = double.tryParse(_weightController.text);
    if (parsed != null) {
      ref
          .read(onboardingProvider.notifier)
          .setWeight(parsed.clamp(_weightMin, _weightMax));
    }
    setState(() => _editingWeight = false);
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(onboardingProvider);
    final notifier = ref.read(onboardingProvider.notifier);

    return OnboardingScaffold(
      step: 2,
      totalSteps: 4,
      onBack: () => context.pop(),
      onNext: () => context.push(RouteConstants.onboardingGoal),
      headline: const Text('키랑 몸무게도\n알려줘!',
          style: TextStyle(
              fontSize: 27,
              height: 1.15,
              fontWeight: FontWeight.w900,
              letterSpacing: -1)),
      body: [
        _MeasurementCard(
          label: '키',
          unit: 'cm',
          value: state.heightCm,
          min: _heightMin,
          max: _heightMax,
          sliderColor: AppColors.green,
          valueText: state.heightCm.round().toString(),
          isEditing: _editingHeight,
          controller: _heightController,
          focus: _heightFocus,
          onTapValue: () => _startEditingHeight(state.heightCm),
          onEditSubmitted: (_) => _heightFocus.unfocus(),
          onSliderChanged: notifier.setHeight,
        ),
        const SizedBox(height: 14),
        _MeasurementCard(
          label: '몸무게',
          unit: 'kg',
          value: state.weightKg,
          min: _weightMin,
          max: _weightMax,
          sliderColor: AppColors.purple,
          valueText: state.weightKg.toStringAsFixed(1),
          isEditing: _editingWeight,
          controller: _weightController,
          focus: _weightFocus,
          onTapValue: () => _startEditingWeight(state.weightKg),
          onEditSubmitted: (_) => _weightFocus.unfocus(),
          onSliderChanged: notifier.setWeight,
          allowDecimal: true,
        ),
        const SizedBox(height: 14),
        IntrinsicHeight(
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Expanded(
                child: Container(
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(
                    color: AppColors.green,
                    borderRadius: BorderRadius.circular(20),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text('BMI',
                          style: TextStyle(
                              color: Color(0xFF3F5518),
                              fontSize: 13,
                              fontWeight: FontWeight.w700)),
                      const SizedBox(height: 6),
                      Text(state.bmi.toStringAsFixed(1),
                          style: const TextStyle(
                              color: AppColors.black,
                              fontSize: 28,
                              fontWeight: FontWeight.w900)),
                    ],
                  ),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Container(
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(
                    color: AppColors.grey,
                    borderRadius: BorderRadius.circular(20),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text('판정',
                          style: TextStyle(
                              color: Color(0xFF888888),
                              fontSize: 13,
                              fontWeight: FontWeight.w700)),
                      const SizedBox(height: 6),
                      Text(state.bmiCategoryLabel,
                          style: const TextStyle(
                              color: AppColors.white,
                              fontSize: 17,
                              fontWeight: FontWeight.w900)),
                      const SizedBox(height: 12),
                      _BmiIndicatorBar(bmi: state.bmi),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 14),
        Row(
          children: [
            Expanded(
                child: _BmiCategoryChip(
                    label: '저체중',
                    range: '18.5 이하',
                    selected: state.bmiCategory == BmiCategory.underweight)),
            const SizedBox(width: 8),
            Expanded(
                child: _BmiCategoryChip(
                    label: '정상',
                    range: '18.5-23',
                    selected: state.bmiCategory == BmiCategory.normal)),
            const SizedBox(width: 8),
            Expanded(
                child: _BmiCategoryChip(
                    label: '과체중',
                    range: '23-25',
                    selected: state.bmiCategory == BmiCategory.overweight)),
            const SizedBox(width: 8),
            Expanded(
                child: _BmiCategoryChip(
                    label: '비만',
                    range: '25 이상',
                    selected: state.bmiCategory == BmiCategory.obese)),
          ],
        ),
      ],
    );
  }
}

class _MeasurementCard extends StatelessWidget {
  const _MeasurementCard({
    required this.label,
    required this.unit,
    required this.value,
    required this.min,
    required this.max,
    required this.sliderColor,
    required this.valueText,
    required this.isEditing,
    required this.controller,
    required this.focus,
    required this.onTapValue,
    required this.onEditSubmitted,
    required this.onSliderChanged,
    this.allowDecimal = false,
  });

  final String label;
  final String unit;
  final double value;
  final double min;
  final double max;
  final Color sliderColor;
  final String valueText;
  final bool isEditing;
  final TextEditingController controller;
  final FocusNode focus;
  final VoidCallback onTapValue;
  final ValueChanged<String> onEditSubmitted;
  final ValueChanged<double> onSliderChanged;
  final bool allowDecimal;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.all(18),
        decoration: BoxDecoration(
          color: AppColors.grey,
          borderRadius: BorderRadius.circular(20),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Row(
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                Text(label,
                    style: const TextStyle(
                        color: Color(0xFF888888),
                        fontSize: 14,
                        fontWeight: FontWeight.w600)),
                const Spacer(),
                if (isEditing)
                  SizedBox(
                    width: 90,
                    child: TextField(
                      controller: controller,
                      focusNode: focus,
                      autofocus: true,
                      textAlign: TextAlign.right,
                      keyboardType: TextInputType.numberWithOptions(
                          decimal: allowDecimal),
                      inputFormatters: [
                        FilteringTextInputFormatter.allow(allowDecimal
                            ? RegExp(r'[0-9.]')
                            : RegExp(r'[0-9]')),
                      ],
                      onSubmitted: onEditSubmitted,
                      style: const TextStyle(
                          color: AppColors.white,
                          fontSize: 32,
                          fontWeight: FontWeight.w900),
                      decoration: const InputDecoration(
                        isDense: true,
                        contentPadding: EdgeInsets.zero,
                        border: InputBorder.none,
                      ),
                    ),
                  )
                else
                  GestureDetector(
                    onTap: onTapValue,
                    child: Text(valueText,
                        style: const TextStyle(
                            color: AppColors.white,
                            fontSize: 32,
                            fontWeight: FontWeight.w900)),
                  ),
                const SizedBox(width: 4),
                Padding(
                  padding: const EdgeInsets.only(bottom: 4),
                  child: Text(unit,
                      style: const TextStyle(
                          color: Color(0xFF888888),
                          fontSize: 15,
                          fontWeight: FontWeight.w600)),
                ),
              ],
            ),
            SliderTheme(
              data: SliderTheme.of(context).copyWith(
                trackHeight: 6,
                thumbShape: const RoundSliderThumbShape(enabledThumbRadius: 11),
                overlayShape: const RoundSliderOverlayShape(overlayRadius: 18),
                activeTrackColor: sliderColor,
                inactiveTrackColor: const Color(0xFF3A3A3A),
                thumbColor: Colors.white,
              ),
              child: Slider(
                value: value.clamp(min, max),
                min: min,
                max: max,
                onChanged: onSliderChanged,
              ),
            ),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 4),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(min.round().toString(),
                      style: const TextStyle(
                          color: Color(0xFF666666), fontSize: 12)),
                  Text(max.round().toString(),
                      style: const TextStyle(
                          color: Color(0xFF666666), fontSize: 12)),
                ],
              ),
            ),
          ],
        ),
      );
}

class _BmiIndicatorBar extends StatelessWidget {
  const _BmiIndicatorBar({required this.bmi});

  final double bmi;

  @override
  Widget build(BuildContext context) {
    const scaleMin = 15.0;
    const scaleMax = 30.0;
    final fraction = ((bmi - scaleMin) / (scaleMax - scaleMin)).clamp(0.0, 1.0);
    // Avoid LayoutBuilder here: it can't report intrinsic dimensions, which
    // breaks the IntrinsicHeight-based row this card sits in. Align's
    // fractional alignment (-1..1) positions the dot without needing to
    // know the track's pixel width up front.
    return SizedBox(
      width: double.infinity,
      height: 12,
      child: Stack(
        alignment: Alignment.centerLeft,
        children: [
          Container(
            height: 4,
            decoration: BoxDecoration(
              color: const Color(0xFF3A3A3A),
              borderRadius: BorderRadius.circular(2),
            ),
          ),
          Align(
            alignment: Alignment(fraction * 2 - 1, 0),
            child: Container(
              width: 12,
              height: 12,
              decoration: const BoxDecoration(
                color: AppColors.green,
                shape: BoxShape.circle,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _BmiCategoryChip extends StatelessWidget {
  const _BmiCategoryChip({
    required this.label,
    required this.range,
    required this.selected,
  });

  final String label;
  final String range;
  final bool selected;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(vertical: 10),
        decoration: BoxDecoration(
          color: selected ? AppColors.green : Colors.transparent,
          borderRadius: BorderRadius.circular(14),
        ),
        child: Column(
          children: [
            Text(label,
                textAlign: TextAlign.center,
                style: TextStyle(
                    color: selected ? AppColors.black : const Color(0xFF888888),
                    fontSize: 13,
                    fontWeight: FontWeight.w800)),
            const SizedBox(height: 2),
            Text(range,
                textAlign: TextAlign.center,
                style: TextStyle(
                    color: selected
                        ? const Color(0xFF3F5518)
                        : const Color(0xFF666666),
                    fontSize: 11)),
          ],
        ),
      );
}
