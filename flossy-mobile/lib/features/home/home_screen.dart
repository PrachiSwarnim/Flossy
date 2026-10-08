import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:google_fonts/google_fonts.dart';
import '../../core/theme/app_theme.dart';
import '../../shared/widgets/app_header.dart';

// ── Data ─────────────────────────────────────────
const _stats = [
  {'value': '10,000+', 'label': 'Happy Patients'},
  {'value': '8', 'label': 'Years of Excellence'},
  {'value': 'Top 1%', 'label': 'Specialist Dentists'},
  {'value': '4.9/5', 'label': 'Patient Rating'},
];

const _howSteps = [
  {
    'step': '01',
    'icon': Icons.person_add_rounded,
    'title': 'Create Your Account',
    'desc': 'Sign up in under a minute with just your email. No forms, no hassle.',
  },
  {
    'step': '02',
    'icon': Icons.calendar_month_rounded,
    'title': 'Book Your Appointment',
    'desc': 'Browse available slots and confirm with one click. FlossyAI suggests the best time for you.',
  },
  {
    'step': '03',
    'icon': Icons.sentiment_very_satisfied_rounded,
    'title': 'Visit & Smile',
    'desc': 'Walk in, receive world-class dental care, and walk out with a brighter, healthier smile.',
  },
];

const _features = [
  {'icon': Icons.calendar_today_rounded, 'title': 'Instant Booking', 'desc': 'Confirm in under 60 seconds'},
  {'icon': Icons.medical_services_rounded, 'title': 'Top Specialists', 'desc': 'Top 1% dentists in India'},
  {'icon': Icons.psychology_rounded, 'title': 'FlossyAI', 'desc': 'AI-guided appointment flow'},
  {'icon': Icons.shield_rounded, 'title': 'Safe & Hygienic', 'desc': 'ISO-certified protocols'},
];

const _aiFeatures = [
  {'icon': Icons.access_time_rounded, 'title': '24/7 Availability', 'desc': 'Always here to answer your questions, day or night.'},
  {'icon': Icons.calendar_month_rounded, 'title': 'Smart Booking', 'desc': 'Effortless AI-assisted appointment scheduling.'},
  {'icon': Icons.bolt_rounded, 'title': 'Instant Answers', 'desc': 'Get immediate dental information on demand.'},
  {'icon': Icons.favorite_rounded, 'title': 'Symptom Analysis', 'desc': 'AI-driven triage to guide your next step.'},
];

const _services = [
  {'title': 'Routine Dental Checkup', 'icon': Icons.search_rounded},
  {'title': 'Preventive Care & Cosmetic', 'icon': Icons.auto_awesome_rounded},
  {'title': 'Dental Fillings', 'icon': Icons.construction_rounded},
  {'title': 'Emergency Care', 'icon': Icons.emergency_rounded},
  {'title': 'Painless Root Canal', 'icon': Icons.healing_rounded},
  {'title': 'Hollywood Smile Makeover', 'icon': Icons.star_rounded},
  {'title': 'Immediate Implants', 'icon': Icons.add_circle_rounded},
  {'title': 'Kids Dentistry', 'icon': Icons.child_friendly_rounded},
  {'title': 'Crowns & Bridges', 'icon': Icons.architecture_rounded},
  {'title': 'Teeth Whitening', 'icon': Icons.light_mode_rounded},
  {'title': 'Wisdom Tooth Removal', 'icon': Icons.remove_circle_rounded},
  {'title': 'Braces & Aligners', 'icon': Icons.straighten_rounded},
  {'title': 'Dentures', 'icon': Icons.face_rounded},
];

// ── Main Screen ──────────────────────────────────
class HomeScreen extends StatelessWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.bgDark,
      body: SafeArea(
        child: CustomScrollView(
          slivers: [
            // App Header
            SliverToBoxAdapter(child: AppHeader()),

            // Hero Section
            SliverToBoxAdapter(child: _HeroSection()),

            // Stats Bar
            SliverToBoxAdapter(child: _StatsBar()),

            // Appointment CTA
            SliverToBoxAdapter(child: _AppointmentCTA()),

            // About Section
            SliverToBoxAdapter(child: _AboutSection()),

            // FlossyAI Section
            SliverToBoxAdapter(child: _FlossyAISection()),

            // How It Works
            SliverToBoxAdapter(child: _HowItWorksSection()),

            // Services
            SliverToBoxAdapter(child: _ServicesSection()),

            // CTA Banner
            SliverToBoxAdapter(child: _CTABanner()),

            // Footer
            SliverToBoxAdapter(child: _Footer()),
          ],
        ),
      ),
    );
  }
}

// ── Hero Section ──────────────────────────────────
class _HeroSection extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Container(
      height: 260,
      margin: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(20),
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            const Color(0xFF1A1A1A),
            const Color(0xFF141414),
            AppTheme.bgDark,
          ],
        ),
        border: Border.all(color: AppTheme.gold.withOpacity(0.12)),
        boxShadow: [
          BoxShadow(
            color: AppTheme.gold.withOpacity(0.04),
            blurRadius: 40,
            spreadRadius: 0,
          ),
        ],
      ),
      child: Stack(
        children: [
          // Glow
          Positioned(
            top: -50,
            right: -50,
            child: Container(
              width: 200,
              height: 200,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                gradient: RadialGradient(
                  colors: [
                    AppTheme.gold.withOpacity(0.06),
                    Colors.transparent,
                  ],
                ),
              ),
            ),
          ),
          Padding(
            padding: const EdgeInsets.all(24),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                  decoration: BoxDecoration(
                    color: AppTheme.gold.withOpacity(0.1),
                    borderRadius: BorderRadius.circular(20),
                    border: Border.all(color: AppTheme.gold.withOpacity(0.2)),
                  ),
                  child: Text(
                    '✦ Premium Dental Care',
                    style: TextStyle(
                      color: AppTheme.gold,
                      fontSize: 10,
                      fontWeight: FontWeight.w600,
                      letterSpacing: 1.2,
                    ),
                  ),
                ),
                const SizedBox(height: 14),
                RichText(
                  text: TextSpan(
                    style: GoogleFonts.playfairDisplay(
                      fontSize: 28,
                      fontWeight: FontWeight.w700,
                      color: Colors.white,
                      height: 1.3,
                    ),
                    children: [
                      const TextSpan(text: 'Your Perfect\n'),
                      TextSpan(
                        text: 'Smile ',
                        style: GoogleFonts.playfairDisplay(
                          color: AppTheme.gold,
                          fontStyle: FontStyle.italic,
                        ),
                      ),
                      const TextSpan(text: 'Starts Here'),
                    ],
                  ),
                ),
                const SizedBox(height: 10),
                Text(
                  'Join thousands of happy patients. Book in under 60 seconds.',
                  style: TextStyle(
                    color: Colors.white.withOpacity(0.5),
                    fontSize: 13,
                    height: 1.5,
                  ),
                ),
                const SizedBox(height: 20),
                Row(
                  children: [
                    Expanded(
                      child: GestureDetector(
                        onTap: () => context.go('/signup'),
                        child: Container(
                          padding: const EdgeInsets.symmetric(vertical: 12),
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
                              'Book Now',
                              style: TextStyle(
                                color: AppTheme.bgDark,
                                fontWeight: FontWeight.w700,
                                fontSize: 13,
                                letterSpacing: 0.5,
                              ),
                            ),
                          ),
                        ),
                      ),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: GestureDetector(
                        onTap: () => context.go('/login'),
                        child: Container(
                          padding: const EdgeInsets.symmetric(vertical: 12),
                          decoration: BoxDecoration(
                            border: Border.all(
                              color: Colors.white.withOpacity(0.2),
                            ),
                            borderRadius: BorderRadius.circular(10),
                          ),
                          child: Center(
                            child: Text(
                              'Sign In',
                              style: TextStyle(
                                color: Colors.white.withOpacity(0.7),
                                fontWeight: FontWeight.w600,
                                fontSize: 13,
                              ),
                            ),
                          ),
                        ),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
    ).animate().fadeIn(duration: 600.ms).slideY(begin: 0.1, end: 0);
  }
}

// ── Stats Bar ──────────────────────────────────
class _StatsBar extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Container(
      color: const Color(0xFF111111),
      padding: const EdgeInsets.symmetric(vertical: 20, horizontal: 16),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceAround,
        children: _stats.asMap().entries.map((e) {
          final i = e.key;
          final s = e.value;
          return Flexible(
            child: Column(
              children: [
                Text(
                  s['value']!,
                  style: GoogleFonts.playfairDisplay(
                    fontSize: 18,
                    fontWeight: FontWeight.w700,
                    color: AppTheme.gold,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  s['label']!,
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    color: Colors.white.withOpacity(0.4),
                    fontSize: 9,
                    letterSpacing: 0.8,
                    fontWeight: FontWeight.w500,
                  ),
                ),
              ],
            ).animate().fadeIn(delay: (i * 100).ms),
          );
        }).toList(),
      ),
    );
  }
}

// ── Appointment CTA ──────────────────────────────────
class _AppointmentCTA extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.all(16),
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(20),
        color: const Color(0xFF1A1A1A),
        border: Border.all(color: AppTheme.gold.withOpacity(0.1)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _SectionLabel('Book an Appointment'),
          const SizedBox(height: 10),
          RichText(
            text: TextSpan(
              style: GoogleFonts.playfairDisplay(),
              children: [
                  const TextSpan(
                    text: 'Your Perfect ',
                    style: TextStyle(
                      color: Colors.white,
                      fontSize: 22,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  TextSpan(
                    text: 'Smile',
                    style: TextStyle(
                      color: AppTheme.gold,
                      fontSize: 22,
                      fontWeight: FontWeight.w700,
                      fontStyle: FontStyle.italic,
                    ),
                  ),
                  const TextSpan(
                    text: ' Starts Here',
                    style: TextStyle(
                      color: Colors.white,
                      fontSize: 22,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 8),
          Text(
            'Join thousands of happy patients. Book in under 60 seconds — no calls, no wait.',
            style: TextStyle(
              color: Colors.white.withOpacity(0.5),
              fontSize: 13,
              height: 1.6,
            ),
          ),
          const SizedBox(height: 16),
          // Feature pills
          GridView.count(
            crossAxisCount: 2,
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            crossAxisSpacing: 10,
            mainAxisSpacing: 10,
            childAspectRatio: 2.2,
            children: _features.map((f) {
              return Container(
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: Colors.white.withOpacity(0.03),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(
                    color: Colors.white.withOpacity(0.07),
                  ),
                ),
                child: Row(
                  children: [
                    Icon(
                      f['icon'] as IconData,
                      color: AppTheme.gold,
                      size: 16,
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        f['title'] as String,
                        style: const TextStyle(
                          color: Colors.white,
                          fontSize: 11,
                          fontWeight: FontWeight.w600,
                        ),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                  ],
                ),
              );
            }).toList(),
          ),
          const SizedBox(height: 16),
          GestureDetector(
            onTap: () => context.go('/signup'),
            child: Container(
              width: double.infinity,
              padding: const EdgeInsets.symmetric(vertical: 14),
              decoration: BoxDecoration(
                color: AppTheme.gold,
                borderRadius: BorderRadius.circular(10),
                boxShadow: [
                  BoxShadow(
                    color: AppTheme.gold.withOpacity(0.25),
                    blurRadius: 20,
                    offset: const Offset(0, 6),
                  ),
                ],
              ),
              child: Center(
                child: Text(
                  'Book Appointment →',
                  style: TextStyle(
                    color: AppTheme.bgDark,
                    fontWeight: FontWeight.w700,
                    fontSize: 14,
                    letterSpacing: 0.5,
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    ).animate().fadeIn(delay: 200.ms, duration: 600.ms).slideY(begin: 0.1, end: 0);
  }
}

// ── About Section ──────────────────────────────────
class _AboutSection extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Container(
      color: const Color(0xFF111111),
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 32),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _SectionLabel('About Us'),
          const SizedBox(height: 10),
          RichText(
            text: TextSpan(
              style: GoogleFonts.playfairDisplay(),
              children: [
                  const TextSpan(
                    text: 'About ',
                    style: TextStyle(color: Colors.white, fontSize: 24, fontWeight: FontWeight.w700),
                  ),
                  TextSpan(
                    text: 'Smile Artists',
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
          const SizedBox(height: 14),
          Text(
            'We are dedicated to providing the finest dental care in a comfortable, modern environment. Our clinic blends art with science to craft smiles that last a lifetime.',
            style: TextStyle(
              color: Colors.white.withOpacity(0.55),
              fontSize: 14,
              height: 1.7,
            ),
          ),
          const SizedBox(height: 10),
          Text(
            'From routine checkups to complex full-mouth rehabilitations, our team of experienced specialists uses cutting-edge technology to deliver treatments tailored precisely to you.',
            style: TextStyle(
              color: Colors.white.withOpacity(0.4),
              fontSize: 13,
              height: 1.7,
            ),
          ),
          const SizedBox(height: 20),
          GestureDetector(
            onTap: () => context.go('/team'),
            child: Row(
              children: [
                Text(
                  'Meet our team',
                  style: TextStyle(
                    color: AppTheme.gold,
                    fontSize: 14,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const SizedBox(width: 6),
                Icon(Icons.arrow_forward, color: AppTheme.gold, size: 16),
              ],
            ),
          ),
        ],
      ),
    ).animate().fadeIn(duration: 600.ms);
  }
}

// ── FlossyAI Section ──────────────────────────────────
class _FlossyAISection extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Container(
      color: AppTheme.bgDark,
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 32),
      child: Column(
        children: [
          _SectionLabel('Powered by AI'),
          const SizedBox(height: 10),
          RichText(
            textAlign: TextAlign.center,
            text: TextSpan(
              style: GoogleFonts.playfairDisplay(),
              children: [
                  const TextSpan(
                    text: 'Powered by ',
                    style: TextStyle(color: Colors.white, fontSize: 24, fontWeight: FontWeight.w700),
                  ),
                  TextSpan(
                    text: 'FlossyAI',
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
          const SizedBox(height: 8),
          Text(
            'Our advanced AI assistant ensures 24/7 care, instant diagnostics, and seamless booking.',
            textAlign: TextAlign.center,
            style: TextStyle(
              color: Colors.white.withOpacity(0.5),
              fontSize: 13,
              height: 1.6,
            ),
          ),
          const SizedBox(height: 20),
          GridView.count(
            crossAxisCount: 2,
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            crossAxisSpacing: 12,
            mainAxisSpacing: 12,
            childAspectRatio: 1.4,
            children: _aiFeatures.asMap().entries.map((e) {
              final i = e.key;
              final f = e.value;
              return Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: const Color(0xFF1F1F1F),
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(
                    color: Colors.white.withOpacity(0.06),
                  ),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Icon(
                      f['icon'] as IconData,
                      color: AppTheme.gold,
                      size: 22,
                    ),
                    const SizedBox(height: 8),
                    Text(
                      f['title'] as String,
                      style: GoogleFonts.playfairDisplay(
                        color: Colors.white,
                        fontSize: 13,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Expanded(
                      child: Text(
                        f['desc'] as String,
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
    );
  }
}

// ── How It Works ──────────────────────────────────
class _HowItWorksSection extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Container(
      color: const Color(0xFF111111),
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 32),
      child: Column(
        children: [
          _SectionLabel('How It Works'),
          const SizedBox(height: 10),
          RichText(
            textAlign: TextAlign.center,
            text: TextSpan(
              style: GoogleFonts.playfairDisplay(),
              children: [
                  const TextSpan(
                    text: 'Get Started in ',
                    style: TextStyle(color: Colors.white, fontSize: 22, fontWeight: FontWeight.w700),
                  ),
                  TextSpan(
                    text: '3 Simple Steps',
                    style: TextStyle(
                      color: AppTheme.gold,
                      fontSize: 22,
                      fontWeight: FontWeight.w700,
                      fontStyle: FontStyle.italic,
                    ),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 20),
          ..._howSteps.asMap().entries.map((e) {
            final i = e.key;
            final s = e.value;
            return Container(
              margin: const EdgeInsets.only(bottom: 12),
              padding: const EdgeInsets.all(18),
              decoration: BoxDecoration(
                color: const Color(0xFF1A1A1A),
                borderRadius: BorderRadius.circular(16),
                border: Border.all(
                  color: Colors.white.withOpacity(0.06),
                ),
              ),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Container(
                    width: 48,
                    height: 48,
                    decoration: BoxDecoration(
                      color: AppTheme.gold.withOpacity(0.1),
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(
                        color: AppTheme.gold.withOpacity(0.2),
                      ),
                    ),
                    child: Icon(
                      s['icon'] as IconData,
                      color: AppTheme.gold,
                      size: 22,
                    ),
                  ),
                  const SizedBox(width: 14),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Step ${s['step']}',
                          style: TextStyle(
                            color: AppTheme.gold.withOpacity(0.7),
                            fontSize: 10,
                            fontWeight: FontWeight.w600,
                            letterSpacing: 1,
                          ),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          s['title'] as String,
                          style: GoogleFonts.playfairDisplay(
                            color: Colors.white,
                            fontSize: 15,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          s['desc'] as String,
                          style: TextStyle(
                            color: Colors.white.withOpacity(0.4),
                            fontSize: 12,
                            height: 1.5,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ).animate().fadeIn(delay: (i * 150).ms).slideX(begin: -0.1, end: 0);
          }),
        ],
      ),
    );
  }
}

// ── Services Section ──────────────────────────────────
class _ServicesSection extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Container(
      color: const Color(0xFF111111),
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 32),
      child: Column(
        children: [
          _SectionLabel('What We Offer'),
          const SizedBox(height: 10),
          RichText(
            textAlign: TextAlign.center,
            text: TextSpan(
              style: GoogleFonts.playfairDisplay(),
              children: [
                  const TextSpan(
                    text: 'Our ',
                    style: TextStyle(color: Colors.white, fontSize: 24, fontWeight: FontWeight.w700),
                  ),
                  TextSpan(
                    text: 'Services',
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
          const SizedBox(height: 20),
          GridView.count(
            crossAxisCount: 2,
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            crossAxisSpacing: 10,
            mainAxisSpacing: 10,
            childAspectRatio: 1.6,
            children: _services.asMap().entries.map((e) {
              final i = e.key;
              final s = e.value;
              return Container(
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                  color: const Color(0xFF1A1A1A),
                  borderRadius: BorderRadius.circular(14),
                  border: Border.all(
                    color: Colors.white.withOpacity(0.06),
                  ),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Icon(s['icon'] as IconData, color: AppTheme.gold, size: 20),
                    const SizedBox(height: 8),
                    Text(
                      s['title'] as String,
                      style: GoogleFonts.playfairDisplay(
                        color: Colors.white,
                        fontSize: 12,
                        fontWeight: FontWeight.w600,
                      ),
                      maxLines: 2,
                    ),
                  ],
                ),
              ).animate().fadeIn(delay: (i * 50).ms);
            }).toList(),
          ),
          const SizedBox(height: 16),
          GestureDetector(
            onTap: () => context.go('/services'),
            child: Container(
              padding: const EdgeInsets.symmetric(vertical: 14),
              decoration: BoxDecoration(
                border: Border.all(color: AppTheme.gold.withOpacity(0.4)),
                borderRadius: BorderRadius.circular(10),
              ),
              child: Center(
                child: Text(
                  'View All Services →',
                  style: TextStyle(
                    color: AppTheme.gold,
                    fontWeight: FontWeight.w600,
                    fontSize: 14,
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

// ── CTA Banner ──────────────────────────────────
class _CTABanner extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.all(16),
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(20),
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            const Color(0xFF1C1A10),
            const Color(0xFF141410),
            const Color(0xFF111111),
          ],
        ),
        border: Border.all(color: AppTheme.gold.withOpacity(0.15)),
      ),
      child: Column(
        children: [
          _SectionLabel('Limited Slots Available'),
          const SizedBox(height: 10),
          RichText(
            textAlign: TextAlign.center,
            text: TextSpan(
              style: GoogleFonts.playfairDisplay(),
              children: [
                  const TextSpan(
                    text: 'Ready to Transform ',
                    style: TextStyle(color: Colors.white, fontSize: 22, fontWeight: FontWeight.w700),
                  ),
                  TextSpan(
                    text: 'Your Smile?',
                    style: TextStyle(
                      color: AppTheme.gold,
                      fontSize: 22,
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
            'Join over 10,000 happy patients who trust Smile Artists for world-class dental care.',
            textAlign: TextAlign.center,
            style: TextStyle(
              color: Colors.white.withOpacity(0.5),
              fontSize: 13,
              height: 1.6,
            ),
          ),
          const SizedBox(height: 20),
          GestureDetector(
            onTap: () => context.go('/signup'),
            child: Container(
              width: double.infinity,
              padding: const EdgeInsets.symmetric(vertical: 14),
              decoration: BoxDecoration(
                color: AppTheme.gold,
                borderRadius: BorderRadius.circular(10),
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
                  'Book Free Consultation →',
                  style: TextStyle(
                    color: AppTheme.bgDark,
                    fontWeight: FontWeight.w700,
                    fontSize: 14,
                  ),
                ),
              ),
            ),
          ),
          const SizedBox(height: 10),
          GestureDetector(
            onTap: () => context.go('/contact'),
            child: Container(
              width: double.infinity,
              padding: const EdgeInsets.symmetric(vertical: 14),
              decoration: BoxDecoration(
                border: Border.all(color: Colors.white.withOpacity(0.2)),
                borderRadius: BorderRadius.circular(10),
              ),
              child: Center(
                child: Text(
                  'Contact Us',
                  style: TextStyle(
                    color: Colors.white.withOpacity(0.7),
                    fontWeight: FontWeight.w600,
                    fontSize: 14,
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

// ── Footer ──────────────────────────────────
class _Footer extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Container(
      color: AppTheme.bgDark,
      padding: const EdgeInsets.all(20),
      child: Column(
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Container(
                width: 32,
                height: 32,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  border: Border.all(color: AppTheme.gold.withOpacity(0.4)),
                  color: AppTheme.bgCard,
                ),
                child: const Icon(
                  Icons.medical_services_rounded,
                  color: AppTheme.gold,
                  size: 16,
                ),
              ),
              const SizedBox(width: 10),
              Text(
                'Smile Artists Dental Studio',
                style: GoogleFonts.playfairDisplay(
                  color: Colors.white.withOpacity(0.7),
                  fontSize: 13,
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            '© 2025 Smile Artists Dental Studio',
            style: TextStyle(
              color: Colors.white.withOpacity(0.3),
              fontSize: 11,
            ),
          ),
          const SizedBox(height: 4),
          RichText(
            text: TextSpan(
              children: [
                TextSpan(
                  text: 'Powered by ',
                  style: TextStyle(
                    color: Colors.white.withOpacity(0.2),
                    fontSize: 11,
                  ),
                ),
                TextSpan(
                  text: 'FlossyAI',
                  style: TextStyle(
                    color: AppTheme.gold.withOpacity(0.6),
                    fontSize: 11,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),
        ],
      ),
    );
  }
}

// ── Shared Section Label ──────────────────────────────────
class _SectionLabel extends StatelessWidget {
  final String text;
  const _SectionLabel(this.text);

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: AppTheme.gold.withOpacity(0.1),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: AppTheme.gold.withOpacity(0.2)),
      ),
      child: Text(
        text.toUpperCase(),
        style: TextStyle(
          color: AppTheme.gold,
          fontSize: 9,
          fontWeight: FontWeight.w700,
          letterSpacing: 1.5,
        ),
      ),
    );
  }
}
