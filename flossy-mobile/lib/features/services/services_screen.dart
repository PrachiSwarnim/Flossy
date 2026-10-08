import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:google_fonts/google_fonts.dart';
import '../../core/theme/app_theme.dart';

const _services = [
  {
    'title': 'Routine Dental Checkup',
    'desc': 'Get your teeth cleaned, checked, and protected with fluoride to stop problems before they start. We also help with gum care and implant checkups.',
    'icon': Icons.search_rounded,
  },
  {
    'title': 'Preventive Care & Cosmetic Dentistry',
    'desc': 'We keep your teeth healthy and also help improve your smile with gentle, modern cosmetic treatments.',
    'icon': Icons.auto_awesome_rounded,
  },
  {
    'title': 'Dental Fillings',
    'desc': 'Traditional or laser fillings repair cavities quickly and comfortably to keep your teeth strong.',
    'icon': Icons.construction_rounded,
  },
  {
    'title': 'Emergency Care & Oral Surgery',
    'desc': 'For chipped teeth, injuries, or sudden pain, our team is ready with fast, skilled, and caring treatment.',
    'icon': Icons.emergency_rounded,
  },
  {
    'title': 'Painless Root Canal Treatments',
    'desc': 'Using advanced methods, we offer almost pain-free, same-day root canals. A crown afterward keeps your tooth extra strong.',
    'icon': Icons.healing_rounded,
  },
  {
    'title': 'Hollywood Smile Makeover',
    'desc': 'A complete smile transformation that blends art and dental science for a bright, confident look.',
    'icon': Icons.star_rounded,
  },
  {
    'title': 'Immediate Implants',
    'desc': 'Replace missing teeth in just 48 hours with natural-looking, long-lasting implants.',
    'icon': Icons.add_circle_rounded,
  },
  {
    'title': 'Kids Dentistry',
    'desc': 'We make dental visits fun and easy for children, helping them build strong, healthy smiles from the start.',
    'icon': Icons.child_friendly_rounded,
  },
  {
    'title': 'Dental Crowns & Bridges',
    'desc': 'Ceramic crowns and bridges fix damaged or missing teeth so you can smile and chew confidently again.',
    'icon': Icons.architecture_rounded,
  },
  {
    'title': 'Teeth Whitening',
    'desc': 'Brighten your smile by several shades in just one hour with safe, effective whitening.',
    'icon': Icons.light_mode_rounded,
  },
  {
    'title': 'Wisdom Tooth Removal',
    'desc': 'Gentle removal of wisdom teeth to prevent pain, infections, and crowding.',
    'icon': Icons.remove_circle_rounded,
  },
  {
    'title': 'Braces & Aligners',
    'desc': 'Choose metal, ceramic, or clear aligners to straighten your teeth comfortably and confidently.',
    'icon': Icons.straighten_rounded,
  },
  {
    'title': 'Dentures',
    'desc': 'Durable, natural-looking partial or full dentures to replace missing teeth and restore your smile with ease.',
    'icon': Icons.face_rounded,
  },
];

class ServicesScreen extends StatelessWidget {
  const ServicesScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.bgDark,
      appBar: AppBar(
        backgroundColor: const Color(0xFF141414),
        title: Text(
          'Our Services',
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
        child: CustomScrollView(
          slivers: [
            // Hero
            SliverToBoxAdapter(
              child: Container(
                padding: const EdgeInsets.all(20),
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
                        'WHAT WE OFFER',
                        style: TextStyle(
                          color: AppTheme.gold,
                          fontSize: 9,
                          fontWeight: FontWeight.w700,
                          letterSpacing: 1.5,
                        ),
                      ),
                    ),
                    const SizedBox(height: 12),
                    RichText(
                      textAlign: TextAlign.center,
                      text: TextSpan(
                        style: GoogleFonts.playfairDisplay(),
                        children: [
                            const TextSpan(
                              text: 'World-Class ',
                              style: TextStyle(color: Colors.white, fontSize: 26, fontWeight: FontWeight.w700),
                            ),
                            TextSpan(
                              text: 'Dental Care',
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
                      'We offer a comprehensive range of dental treatments using the latest technology, delivered by India\'s top 1% specialists.',
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
            ),

            // Services grid
            SliverPadding(
              padding: const EdgeInsets.all(16),
              sliver: SliverList(
                delegate: SliverChildBuilderDelegate(
                  (context, index) {
                    final s = _services[index];
                    return Container(
                      margin: const EdgeInsets.only(bottom: 12),
                      padding: const EdgeInsets.all(18),
                      decoration: BoxDecoration(
                        color: AppTheme.bgCard,
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
                            child: Icon(
                              s['icon'] as IconData,
                              color: AppTheme.gold,
                              size: 20,
                            ),
                          ),
                          const SizedBox(width: 14),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  s['title'] as String,
                                  style: GoogleFonts.playfairDisplay(
                                    color: Colors.white,
                                    fontSize: 15,
                                    fontWeight: FontWeight.w600,
                                  ),
                                ),
                                const SizedBox(height: 6),
                                Text(
                                  s['desc'] as String,
                                  style: TextStyle(
                                    color: Colors.white.withOpacity(0.5),
                                    fontSize: 12,
                                    height: 1.6,
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ],
                      ),
                    ).animate().fadeIn(delay: (index * 50).ms).slideX(begin: -0.05, end: 0);
                  },
                  childCount: _services.length,
                ),
              ),
            ),

            // CTA
            SliverToBoxAdapter(
              child: Padding(
                padding: const EdgeInsets.fromLTRB(16, 0, 16, 32),
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
            ),
          ],
        ),
      ),
    );
  }
}
