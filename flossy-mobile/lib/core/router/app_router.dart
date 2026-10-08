import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import '../providers/auth_provider.dart';
import '../../features/home/home_screen.dart';
import '../../features/auth/login_screen.dart';
import '../../features/auth/signup_screen.dart';
import '../../features/services/services_screen.dart';
import '../../features/contact/contact_screen.dart';
import '../../features/tourism/tourism_screen.dart';
import '../../features/team/team_screen.dart';
import '../../features/dashboard/patient/patient_dashboard.dart';
import '../../features/dashboard/dentist/dentist_dashboard.dart';
import '../../features/dashboard/receptionist/receptionist_dashboard.dart';
import '../../features/splash/splash_screen.dart';

class AppRouter {
  static final _rootNavigatorKey = GlobalKey<NavigatorState>();

  static GoRouter get router => GoRouter(
        navigatorKey: _rootNavigatorKey,
        initialLocation: '/splash',
        redirect: (context, state) {
          final authProvider = context.read<AuthProvider>();
          final isAuth = authProvider.isAuthenticated;
          final isLoading = authProvider.status == AuthStatus.loading;

          final path = state.uri.path;

          if (isLoading) return '/splash';

          // Redirect authenticated users away from auth screens
          if (isAuth &&
              (path == '/login' ||
                  path == '/signup' ||
                  path == '/splash')) {
            final role = authProvider.user?.role ?? 'patient';
            if (role == 'dentist') return '/dentist';
            if (role == 'receptionist') return '/receptionist';
            return '/patient';
          }

          // Redirect unauthenticated users from protected routes
          final protectedRoutes = ['/patient', '/dentist', '/receptionist'];
          if (!isAuth && protectedRoutes.contains(path)) {
            return '/login';
          }

          return null;
        },
        routes: [
          GoRoute(
            path: '/splash',
            builder: (context, state) => const SplashScreen(),
          ),
          GoRoute(
            path: '/',
            builder: (context, state) => const HomeScreen(),
          ),
          GoRoute(
            path: '/login',
            builder: (context, state) => const LoginScreen(),
          ),
          GoRoute(
            path: '/signup',
            builder: (context, state) => const SignupScreen(),
          ),
          GoRoute(
            path: '/services',
            builder: (context, state) => const ServicesScreen(),
          ),
          GoRoute(
            path: '/contact',
            builder: (context, state) => const ContactScreen(),
          ),
          GoRoute(
            path: '/tourism',
            builder: (context, state) => const TourismScreen(),
          ),
          GoRoute(
            path: '/team',
            builder: (context, state) => const TeamScreen(),
          ),
          GoRoute(
            path: '/patient',
            builder: (context, state) => const PatientDashboard(),
          ),
          GoRoute(
            path: '/dentist',
            builder: (context, state) => const DentistDashboard(),
          ),
          GoRoute(
            path: '/receptionist',
            builder: (context, state) => const ReceptionistDashboard(),
          ),
        ],
      );
}
