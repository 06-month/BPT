import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../features/auth/providers/auth_provider.dart';
import '../../features/auth/screens/login_screen.dart';
import '../../features/home/screens/home_screen.dart';
import '../../features/profile/screens/profile_screen.dart';
import '../../features/report/screens/report_screen.dart';
import '../../features/splash/splash_screen.dart';
import '../../features/workout/screens/exercise_selection_screen.dart';
import '../../features/workout/screens/native_pose_workout_screen.dart';
import '../../features/workout/screens/workout_result_screen.dart';
import '../../features/workout/screens/workout_screen.dart';
import '../constants/route_constants.dart';
import '../shell/main_shell.dart';

final appRouterProvider = Provider<GoRouter>((ref) {
  // ref.read (not watch) so GoRouter is not recreated on auth change.
  // refreshListenable handles dynamic redirects instead.
  final authNotifier = ref.read(authNotifierProvider);

  return GoRouter(
    initialLocation: RouteConstants.splash,
    refreshListenable: authNotifier,
    redirect: (BuildContext context, GoRouterState state) {
      final loggedIn = authNotifier.isLoggedIn;
      final loc = state.matchedLocation;

      if (loc == RouteConstants.splash) return null;

      if (!loggedIn && loc != RouteConstants.login) return RouteConstants.login;
      if (loggedIn && loc == RouteConstants.login) return RouteConstants.home;
      return null;
    },
    routes: [
      GoRoute(
        path: RouteConstants.splash,
        pageBuilder: (context, state) => _fadePage(state, const SplashScreen()),
      ),
      GoRoute(
        path: RouteConstants.login,
        pageBuilder: (context, state) => _fadePage(
          state,
          const LoginScreen(),
        ),
      ),
      ShellRoute(
        builder: (context, state, child) => MainShell(child: child),
        routes: [
          GoRoute(
            path: RouteConstants.home,
            pageBuilder: (context, state) =>
                _fadePage(state, const HomeScreen()),
          ),
          GoRoute(
            path: RouteConstants.report,
            pageBuilder: (context, state) =>
                _fadePage(state, const ReportScreen()),
          ),
          GoRoute(
            path: RouteConstants.profile,
            pageBuilder: (context, state) =>
                _fadePage(state, const ProfileScreen()),
          ),
        ],
      ),
      GoRoute(
        path: RouteConstants.exerciseSelection,
        pageBuilder: (context, state) =>
            _slidePage(state, const ExerciseSelectionScreen()),
      ),
      GoRoute(
        path: RouteConstants.workout,
        pageBuilder: (context, state) {
          final exerciseId = state.extra as String? ?? 'squat';
          return _slidePage(state, WorkoutScreen(exerciseId: exerciseId));
        },
      ),
      GoRoute(
        path: RouteConstants.nativePoseWorkout,
        pageBuilder: (context, state) {
          final extra = state.extra;
          var exerciseId = 'squat';
          var targetReps = 15;
          var targetSets = 3;
          if (extra is Map) {
            exerciseId = extra['exerciseId'] as String? ?? exerciseId;
            targetReps = extra['targetReps'] as int? ?? targetReps;
            targetSets = extra['targetSets'] as int? ?? targetSets;
          } else if (extra is String) {
            exerciseId = extra;
          }
          return _slidePage(
            state,
            NativePoseWorkoutScreen(
              exerciseId: exerciseId,
              targetReps: targetReps,
              targetSets: targetSets,
            ),
          );
        },
      ),
      GoRoute(
        path: RouteConstants.workoutResult,
        pageBuilder: (context, state) {
          final result = state.extra as Map<String, dynamic>? ?? const {};
          return _slidePage(state, WorkoutResultScreen(result: result));
        },
      ),
    ],
  );
});

CustomTransitionPage<void> _fadePage(GoRouterState state, Widget child) {
  return CustomTransitionPage<void>(
    key: state.pageKey,
    child: child,
    transitionDuration: const Duration(milliseconds: 250),
    transitionsBuilder: (_, animation, __, c) =>
        FadeTransition(opacity: animation, child: c),
  );
}

CustomTransitionPage<void> _slidePage(GoRouterState state, Widget child) {
  return CustomTransitionPage<void>(
    key: state.pageKey,
    child: child,
    transitionDuration: const Duration(milliseconds: 300),
    transitionsBuilder: (_, animation, __, c) {
      final tween = Tween(
        begin: const Offset(1.0, 0.0),
        end: Offset.zero,
      ).chain(CurveTween(curve: Curves.easeOutCubic));
      return SlideTransition(position: animation.drive(tween), child: c);
    },
  );
}
