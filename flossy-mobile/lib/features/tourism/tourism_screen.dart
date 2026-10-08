import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:url_launcher/url_launcher.dart';
import '../../core/theme/app_theme.dart';

class TourismScreen extends StatelessWidget {
  const TourismScreen({super.key});

  static const _benefits = [
    {'icon': Icons.savings_rounded, 'title': 'Save up to 70%', 'desc': 'World-class dental care at a fraction of Western prices'},
    {'icon': Icons.star_rounded, 'title': 'Top 1% Specialists', 'desc': 'India\'s finest dentists with international training'},
    {'icon': Icons.flight_takeoff_rounded, 'title': 'Full Concierge', 'desc': 'We arrange travel, hotel, and entire dental plan'},
    {'icon': Icons.verified_rounded, 'title': 'ISO Certified', 'desc': 'International safety and hygiene standards'},
  ];

  static const _process = [
    {
      'step': '01',
      'title': 'Virtual Consultation',
      'desc': 'Share your dental X-rays or reports online. Our specialists review and create your personal treatment plan.',
    },
    {
      'step': '02',
      'title': 'Travel & Accommodation',
      'desc': 'We coordinate your flights and hotel in Gurugram — India\'s medical tourism capital.',
    },
    {
      'step': '03',
      'title': 'World-Class Treatment',
      'desc': 'Receive premium dental care at our modern clinic using the latest technology.',
    },
    {
      'step': '04',
      'title': 'Aftercare Support',
      'desc': 'We provide comprehensive remote aftercare and follow-up consultations after you return home.',
    },
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.bgDark,
      appBar: AppBar(
        backgroundColor: const Color(0xFF141414),
        title: Text(
          'Dental Tourism',
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
                padding: const EdgeInsets.all(24),
                color: const Color(0xFF111111),
                child: Column(
                  children: [
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                      decoration: BoxDecoration(
                        color: AppTheme.gold.withOpacity(0.1),
                        borderRadius: BorderRadius.circular(20),
                        border: Border.all(color: AppTheme.gold.withOpacity(0.2)),
                      ),
                      child: Text(
                        '✈ INTERNATIONAL DENTAL CARE',
                        style: TextStyle(
                          color: AppTheme.gold,
                          fontSize: 9,
                          fontWeight: FontWeight.w700,
                          letterSpacing: 1.5,
                        ),
                      ),
                    ),
                    const SizedBox(height: 14),
                    RichText(
                      textAlign: TextAlign.center,
                      text: TextSpan(
                        style: GoogleFonts.playfairDisplay(),
                        children: [
                            const TextSpan(
                              text: 'World-Class Dental Care in ',
                              style: TextStyle(color: Colors.white, fontSize: 24, fontWeight: FontWeight.w700),
                            ),
                            TextSpan(
                              text: 'India',
                              style: TextStyle(
                                color: AppTheme.gold,
                                fontSize: 24,
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
                      'Combine a visit to incredible India with premium dental care at a fraction of the cost you\'d pay at home. Our dental tourism package includes everything.',
                      textAlign: TextAlign.center,
                      style: TextStyle(
                        color: Colors.white.withOpacity(0.5),
                        fontSize: 13,
                        height: 1.7,
                      ),
                    ),
                    const SizedBox(height: 20),
                    GestureDetector(
                      onTap: () => launchUrl(Uri.parse('https://wa.me/918507213999?text=I\'m interested in Dental Tourism')),
                      child: Container(
                        width: double.infinity,
                        padding: const EdgeInsets.symmetric(vertical: 14),
                        decoration: BoxDecoration(
                          color: AppTheme.gold,
                          borderRadius: BorderRadius.circular(10),
                          boxShadow: [
                            BoxShadow(
                              color: AppTheme.gold.withOpacity(0.3),
                              blurRadius: 16,
                              offset: const Offset(0, 4),
                            ),
                          ],
                        ),
                        child: Center(
                          child: Text(
                            'Enquire via WhatsApp →',
                            style: TextStyle(
                              color: AppTheme.bgDark,
                              fontWeight: FontWeight.w700,
                              fontSize: 14,
                            ),
                          ),
                        ),
                      ),
                    ),
                  ],
                ),
              ).animate().fadeIn(duration: 600.ms),

              // Benefits
              Container(
                padding: const EdgeInsets.all(16),
                color: AppTheme.bgDark,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Why Choose Us?',
                      style: GoogleFonts.playfairDisplay(
                        color: Colors.white,
                        fontSize: 20,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    const SizedBox(height: 16),
                    GridView.count(
                      crossAxisCount: 2,
                      shrinkWrap: true,
                      physics: const NeverScrollableScrollPhysics(),
                      crossAxisSpacing: 12,
                      mainAxisSpacing: 12,
                      childAspectRatio: 1.3,
                      children: _benefits.asMap().entries.map((e) {
                        final i = e.key;
                        final b = e.value;
                        return Container(
                          padding: const EdgeInsets.all(14),
                          decoration: BoxDecoration(
                            color: const Color(0xFF1A1A1A),
                            borderRadius: BorderRadius.circular(16),
                            border: Border.all(color: Colors.white.withOpacity(0.06)),
                          ),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Icon(b['icon'] as IconData, color: AppTheme.gold, size: 22),
                              const SizedBox(height: 8),
                              Text(
                                b['title'] as String,
                                style: GoogleFonts.playfairDisplay(
                                  color: Colors.white,
                                  fontSize: 13,
                                  fontWeight: FontWeight.w600,
                                ),
                              ),
                              const SizedBox(height: 4),
                              Expanded(
                                child: Text(
                                  b['desc'] as String,
                                  style: TextStyle(
                                    color: Colors.white.withOpacity(0.4),
                                    fontSize: 11,
                                    height: 1.4,
                                  ),
                                  maxLines: 2,
                                  overflow: TextOverflow.ellipsis,
                                ),
                              ),
                            ],
                          ),
                        ).animate().fadeIn(delay: (i * 100).ms);
                      }).toList(),
                    ),
                  ],
                ),
              ),

              // Process
              Container(
                padding: const EdgeInsets.all(16),
                color: const Color(0xFF111111),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'The Process',
                      style: GoogleFonts.playfairDisplay(
                        color: Colors.white,
                        fontSize: 20,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    const SizedBox(height: 16),
                    ..._process.asMap().entries.map((e) {
                      final i = e.key;
                      final p = e.value;
                      return Container(
                        margin: const EdgeInsets.only(bottom: 12),
                        padding: const EdgeInsets.all(16),
                        decoration: BoxDecoration(
                          color: AppTheme.bgCard,
                          borderRadius: BorderRadius.circular(16),
                          border: Border.all(color: Colors.white.withOpacity(0.05)),
                        ),
                        child: Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Container(
                              width: 36,
                              height: 36,
                              decoration: BoxDecoration(
                                color: AppTheme.gold.withOpacity(0.15),
                                borderRadius: BorderRadius.circular(10),
                                border: Border.all(color: AppTheme.gold.withOpacity(0.3)),
                              ),
                              child: Center(
                                child: Text(
                                  p['step']!,
                                  style: GoogleFonts.playfairDisplay(
                                    color: AppTheme.gold,
                                    fontSize: 12,
                                    fontWeight: FontWeight.w700,
                                  ),
                                ),
                              ),
                            ),
                            const SizedBox(width: 12),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    p['title']!,
                                    style: GoogleFonts.playfairDisplay(
                                      color: Colors.white,
                                      fontSize: 14,
                                      fontWeight: FontWeight.w600,
                                    ),
                                  ),
                                  const SizedBox(height: 4),
                                  Text(
                                    p['desc']!,
                                    style: TextStyle(
                                      color: Colors.white.withOpacity(0.5),
                                      fontSize: 12,
                                      height: 1.5,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ],
                        ),
                      ).animate().fadeIn(delay: (i * 100).ms).slideX(begin: -0.05, end: 0);
                    }),
                  ],
                ),
              ),

              // CTA
              Padding(
                padding: const EdgeInsets.all(16),
                child: GestureDetector(
                  onTap: () => launchUrl(Uri.parse('https://wa.me/918507213999?text=I\'m interested in Dental Tourism')),
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
                        'Start My Dental Journey →',
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

              const SizedBox(height: 16),
            ],
          ),
        ),
      ),
    );
  }
}
