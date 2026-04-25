import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../data/mock_data.dart';
import '../../../models/user_model.dart';

class ProfileNotifier extends StateNotifier<UserModel> {
  ProfileNotifier() : super(mockUser);

  void update({
    String? name,
    int? age,
    double? weightKg,
    double? heightCm,
  }) {
    final initials = name != null && name.trim().isNotEmpty
        ? name.trim().split(' ').map((w) => w[0].toUpperCase()).take(2).join()
        : null;
    state = state.copyWith(
      name: name,
      age: age,
      weightKg: weightKg,
      heightCm: heightCm,
      avatarInitials: initials,
    );
  }
}

final profileUserProvider =
    StateNotifierProvider<ProfileNotifier, UserModel>((ref) => ProfileNotifier());

final notificationsEnabledProvider = StateProvider<bool>((ref) => true);
final darkModeEnabledProvider = StateProvider<bool>((ref) => false);
final soundEnabledProvider = StateProvider<bool>((ref) => true);
final hapticEnabledProvider = StateProvider<bool>((ref) => true);
