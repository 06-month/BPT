import 'package:bpt/core/constants/route_constants.dart';
import 'package:bpt/core/router/app_router.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test(
      'signed-out users are not bounced away from login, recovery, sign-up, or onboarding',
      () {
    for (final loc in [
      RouteConstants.login,
      RouteConstants.accountRecovery,
      RouteConstants.signUp,
      RouteConstants.onboardingGender,
      RouteConstants.onboardingBody,
    ]) {
      expect(resolveAuthRedirect(loggedIn: false, location: loc), isNull,
          reason: loc);
    }
  });

  test('signed-out users are sent to login from protected routes', () {
    expect(resolveAuthRedirect(loggedIn: false, location: RouteConstants.home),
        RouteConstants.login);
  });

  test('splash never redirects, regardless of auth state', () {
    expect(
        resolveAuthRedirect(loggedIn: false, location: RouteConstants.splash),
        isNull);
    expect(resolveAuthRedirect(loggedIn: true, location: RouteConstants.splash),
        isNull);
  });

  test('signed-in users are bounced from login to home', () {
    expect(resolveAuthRedirect(loggedIn: true, location: RouteConstants.login),
        RouteConstants.home);
  });
}
