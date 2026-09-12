import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../features/auth/providers/auth_provider.dart';
import '../../../models/user_model.dart';

// Delegates to auth — keeps a single source of truth for the current user.
final profileUserProvider = Provider<UserModel?>((ref) {
  return ref.watch(authNotifierProvider).currentUser;
});

final notificationsEnabledProvider = StateProvider<bool>((ref) => true);
final darkModeEnabledProvider = StateProvider<bool>((ref) => false);
final soundEnabledProvider = StateProvider<bool>((ref) => true);
final hapticEnabledProvider = StateProvider<bool>((ref) => true);
