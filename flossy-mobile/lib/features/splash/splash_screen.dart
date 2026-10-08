import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:go_router/go_router.dart';
import 'package:flutter_animate/flutter_animate.dart';
import '../../core/providers/auth_provider.dart';
import '../../core/theme/app_theme.dart';

class SplashScreen extends StatefulWidget {
  const SplashScreen({super.key});

  @override
  State<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends State<SplashScreen> {
  @override
  void initState() {
    super.initState();
    _navigate();
  }

  Future<void> _navigate() async {
    await Future.delayed(const Duration(seconds: 2));
    if (!mounted) return;

    final auth = context.read<AuthProvider>();

    if (auth.status == AuthStatus.loading) {
      // Wait a bit more
      await Future.delayed(const Duration(seconds: 1));
    }

    if (!mounted) return;

    if (auth.isAuthenticated) {
      final role = auth.user?.role ?? 'patient';
      if (role == 'dentist') {
        context.go('/dentist');
      } else if (role == 'receptionist') {
        context.go('/receptionist');
      } else {
        context.go('/patient');
      }
    } else {
      context.go('/');
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.bgDark,
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            // Logo circle
            Container(
              width: 90,
              height: 90,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                border: Border.all(
                  color: AppTheme.gold.withOpacity(0.5),
                  width: 2,
                ),
                color: AppTheme.bgCard,
              ),
              child: const Icon(
                Icons.medical_services_rounded,
                color: AppTheme.gold,
                size: 42,
              ),
            )
                .animate()
                .fadeIn(duration: 600.ms)
                .scale(begin: const Offset(0.7, 0.7)),
            const SizedBox(height: 20),
            Text(
              'Smile Artists',
              style: TextStyle(
                fontFamily: 'PlayfairDisplay',
                fontSize: 30,
                fontWeight: FontWeight.w700,
                color: Colors.white,
                letterSpacing: 0.5,
              ),
            )
                .animate()
                .fadeIn(delay: 300.ms, duration: 600.ms)
                .slideY(begin: 0.3, end: 0),
            const SizedBox(height: 6),
            Text(
              '...crafting smiles',
              style: TextStyle(
                fontSize: 14,
                color: AppTheme.gold.withOpacity(0.8),
                fontStyle: FontStyle.italic,
              ),
            ).animate().fadeIn(delay: 500.ms, duration: 600.ms),
            const SizedBox(height: 50),
            SizedBox(
              width: 28,
              height: 28,
              child: CircularProgressIndicator(
                strokeWidth: 2,
                color: AppTheme.gold.withOpacity(0.7),
              ),
            ).animate().fadeIn(delay: 700.ms),
          ],
        ),
      ),
    );
  }
}
