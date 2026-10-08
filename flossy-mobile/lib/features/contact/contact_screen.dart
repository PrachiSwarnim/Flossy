import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:url_launcher/url_launcher.dart';
import '../../core/theme/app_theme.dart';

class ContactScreen extends StatelessWidget {
  const ContactScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.bgDark,
      appBar: AppBar(
        backgroundColor: const Color(0xFF141414),
        title: Text(
          'Contact Us',
          style: GoogleFonts.playfairDisplay(
            color: Colors.white,
            fontSize: 18,
            fontWeight: FontWeight.w700,
          ),
        ),
        leading: GestureDetector(
          onTap: () => context.go('/'),
          child: const Icon(Icons.arrow_back, color: Colors.white),
        ),
      ),
      body: SafeArea(
        child: SingleChildScrollView(
          child: Column(
            children: [
              // Hero
              Container(
                padding: const EdgeInsets.all(20),
                color: const Color(0xFF111111),
                child: Column(
                  children: [
                    RichText(
                      textAlign: TextAlign.center,
                      text: TextSpan(
                        style: GoogleFonts.playfairDisplay(),
                        children: [
                            const TextSpan(
                              text: 'Get in ',
                              style: TextStyle(color: Colors.white, fontSize: 26, fontWeight: FontWeight.w700),
                            ),
                            TextSpan(
                              text: 'Touch',
                              style: TextStyle(
                                color: AppTheme.gold,
                                fontSize: 26,
                                fontWeight: FontWeight.w700,
                                fontStyle: FontStyle.italic,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                    const SizedBox(height: 10),
                    Text(
                      'We\'d love to hear from you. Reach out to us any time.',
                      textAlign: TextAlign.center,
                      style: TextStyle(
                        color: Colors.white.withOpacity(0.5),
                        fontSize: 13,
                        height: 1.6,
                      ),
                    ),
                  ],
                ),
              ),

              const SizedBox(height: 16),

              // Contact Cards
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16),
                child: Column(
                  children: [
                    // Call card
                    _ContactCard(
                      icon: Icons.phone_rounded,
                      title: 'Call Us',
                      items: ['+91-8507-213-999', '+91-9693-288-488'],
                      onTap: () => launchUrl(Uri.parse('tel:+918507213999')),
                    ).animate().fadeIn(delay: 100.ms).slideY(begin: 0.1),

                    const SizedBox(height: 12),

                    // Email card
                    _ContactCard(
                      icon: Icons.email_rounded,
                      title: 'Email Us',
                      items: ['info@smileartists.in', 'www.smileartists.in'],
                      onTap: () => launchUrl(Uri.parse('mailto:info@smileartists.in')),
                    ).animate().fadeIn(delay: 200.ms).slideY(begin: 0.1),

                    const SizedBox(height: 12),

                    // Location card
                    _ContactCard(
                      icon: Icons.location_on_rounded,
                      title: 'Visit Us',
                      items: [
                        '573, Smile Artists Dental Studio',
                        'Artemis Hospital Road, Koyal Vihar',
                        'Gurugram – 122003, Haryana, India',
                      ],
                      extra: '10:30 AM – 8:30 PM (Mon–Sun)',
                      onTap: () => launchUrl(Uri.parse(
                          'https://maps.google.com/?q=573,+Smile+Artists+Dental+Studio,+Artemis+Hospital+Road,+Koyal+Vihar,+Gurugram')),
                    ).animate().fadeIn(delay: 300.ms).slideY(begin: 0.1),
                  ],
                ),
              ),

              const SizedBox(height: 24),

              // Social links
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Follow Us',
                      style: GoogleFonts.playfairDisplay(
                        color: Colors.white,
                        fontSize: 16,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    const SizedBox(height: 12),
                    Row(
                      children: [
                        _SocialButton(
                          icon: Icons.facebook_rounded,
                          label: 'Facebook',
                          onTap: () => launchUrl(Uri.parse('https://www.facebook.com/smileartistsdentalstudio')),
                        ),
                        const SizedBox(width: 12),
                        _SocialButton(
                          icon: Icons.photo_camera_rounded,
                          label: 'Instagram',
                          onTap: () => launchUrl(Uri.parse('https://www.instagram.com/smileartistsdentalstudio')),
                        ),
                      ],
                    ),
                  ],
                ),
              ),

              const SizedBox(height: 32),

              // Book Appointment CTA
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16),
                child: GestureDetector(
                  onTap: () => context.go('/signup'),
                  child: Container(
                    width: double.infinity,
                    padding: const EdgeInsets.symmetric(vertical: 16),
                    decoration: BoxDecoration(
                      color: AppTheme.gold,
                      borderRadius: BorderRadius.circular(12),
                      boxShadow: [
                        BoxShadow(
                          color: AppTheme.gold.withOpacity(0.3),
                          blurRadius: 20,
                          offset: const Offset(0, 6),
                        ),
                      ],
                    ),
                    child: Center(
                      child: Text(
                        'Book an Appointment →',
                        style: TextStyle(
                          color: AppTheme.bgDark,
                          fontWeight: FontWeight.w700,
                          fontSize: 15,
                        ),
                      ),
                    ),
                  ),
                ),
              ),

              const SizedBox(height: 32),
            ],
          ),
        ),
      ),
    );
  }
}

class _ContactCard extends StatelessWidget {
  final IconData icon;
  final String title;
  final List<String> items;
  final String? extra;
  final VoidCallback onTap;

  const _ContactCard({
    required this.icon,
    required this.title,
    required this.items,
    this.extra,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: const Color(0xFF1A1A1A),
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: Colors.white.withOpacity(0.06)),
        ),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              width: 44,
              height: 44,
              decoration: BoxDecoration(
                color: AppTheme.gold.withOpacity(0.1),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: AppTheme.gold.withOpacity(0.2)),
              ),
              child: Icon(icon, color: AppTheme.gold, size: 20),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    style: GoogleFonts.playfairDisplay(
                      color: Colors.white,
                      fontSize: 15,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  const SizedBox(height: 6),
                  ...items.map((item) => Padding(
                        padding: const EdgeInsets.only(bottom: 2),
                        child: Text(
                          item,
                          style: TextStyle(
                            color: Colors.white.withOpacity(0.5),
                            fontSize: 13,
                          ),
                        ),
                      )),
                  if (extra != null) ...[
                    const SizedBox(height: 6),
                    Row(
                      children: [
                        Icon(Icons.access_time, color: AppTheme.gold.withOpacity(0.7), size: 12),
                        const SizedBox(width: 4),
                        Text(
                          extra!,
                          style: TextStyle(
                            color: AppTheme.gold.withOpacity(0.7),
                            fontSize: 11,
                          ),
                        ),
                      ],
                    ),
                  ],
                ],
              ),
            ),
            Icon(Icons.arrow_forward_ios, color: Colors.white.withOpacity(0.2), size: 14),
          ],
        ),
      ),
    );
  }
}

class _SocialButton extends StatelessWidget {
  final IconData icon;
  final String label;
  final VoidCallback onTap;

  const _SocialButton({required this.icon, required this.label, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        decoration: BoxDecoration(
          color: const Color(0xFF1A1A1A),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: Colors.white.withOpacity(0.08)),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, color: AppTheme.gold, size: 18),
            const SizedBox(width: 8),
            Text(
              label,
              style: TextStyle(
                color: Colors.white.withOpacity(0.7),
                fontSize: 13,
                fontWeight: FontWeight.w500,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
