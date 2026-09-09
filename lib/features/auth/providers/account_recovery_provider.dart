import 'package:flutter_riverpod/flutter_riverpod.dart';

/// UI preview only. Never grants a Firebase session or changes credentials.
const recoveryPreviewCode = '418320';

class AccountRecoveryState {
  const AccountRecoveryState({
    this.email = '',
    this.sent = false,
    this.verified = false,
    this.error,
  });

  final String email;
  final bool sent;
  final bool verified;
  final String? error;

  String get maskedId {
    final parts = email.split('@');
    final name = parts.first;
    final visible = name.length > 3 ? name.substring(0, 3) : name[0];
    return '$visible***@${parts.last}';
  }
}

class AccountRecoveryNotifier extends StateNotifier<AccountRecoveryState> {
  AccountRecoveryNotifier() : super(const AccountRecoveryState());

  void changeEmail(String email) {
    if (email.trim() == state.email) return;
    // Editing the address invalidates the old code and recovered account.
    state = AccountRecoveryState(email: email.trim());
  }

  bool sendCode() {
    if (!RegExp(r'^[^\s@]+@[^\s@]+\.[^\s@]+$').hasMatch(state.email)) {
      state = AccountRecoveryState(
        email: state.email,
        error: '올바른 이메일을 입력해줘.',
      );
      return false;
    }
    state = AccountRecoveryState(email: state.email, sent: true);
    return true;
  }

  void verifyCode(String code) {
    if (!state.sent || state.verified) return;
    state = AccountRecoveryState(
      email: state.email,
      sent: true,
      verified: code == recoveryPreviewCode,
      error: code == recoveryPreviewCode ? null : '인증 코드가 맞지 않아. 다시 확인해줘.',
    );
  }
}

final accountRecoveryProvider = StateNotifierProvider.autoDispose<
    AccountRecoveryNotifier, AccountRecoveryState>(
  (ref) => AccountRecoveryNotifier(),
);
