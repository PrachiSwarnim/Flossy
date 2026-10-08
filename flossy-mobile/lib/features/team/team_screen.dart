import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:url_launcher/url_launcher.dart';
import '../../core/theme/app_theme.dart';

class TeamScreen extends StatelessWidget {
  const TeamScreen({super.key});

  static const _team = [
    {
      'name': 'Dr. Shagufta Jawaid',
      'desc': 'A compassionate and skilled dentist, Dr. Jawaid is known for her patient-first approach and dedication to advanced dental technologies.',
      'link': 'https://www.linkedin.com/in/dr-shagufta-jawaid-53604b203/',
      'initials': 'SJ',
    },
    {
      'name': 'Dr. Shruti Choudhary',
      'desc': 'With her gentle and friendly approach, Dr. Choudhary makes dental care stress-free and enjoyable while ensuring precision and comfort.',
      'link': 'https://www.linkedin.com/in/shruti-choudhary01/',
      'initials': 'SC',
    },
    {
      'name': 'Dr. Aishwarya Singh',
      'desc': 'An expert in smile design, Dr. Singh\'s artistry and attention to detail bring out radiant, confident smiles with every treatment.',
      'link': 'https://www.linkedin.com/in/dr-aishwarya-singh/',
      'initials': 'AS',
    },
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.bgDark,
      appBar: AppBar(
        backgroundColor: const Color(0xFF141414),
        title: Text(
          'Meet the Team',
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
          padding: const EdgeInsets.all(16),
          child: Column(
            children: [
              // Header
              Column(
                children: [
                  RichText(
                    textAlign: TextAlign.center,
                    text: TextSpan(
                      style: GoogleFonts.playfairDisplay(),
                      children: [
                          const TextSpan(
                            text: 'Meet the ',
                            style: TextStyle(color: Colors.white, fontSize: 26, fontWeight: FontWeight.w700),
                          ),
                          TextSpan(
                            text: 'Team',
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
                    'The Smile Artists team is built on friendship, expertise, and empathy — three dentists united by a shared passion for creating brighter, healthier smiles.',
                    textAlign: TextAlign.center,
                    style: TextStyle(
                      color: Colors.white.withOpacity(0.5),
                      fontSize: 13,
                      height: 1.7,
                    ),
                  ),
                ],
              ),

              const SizedBox(height: 24),

              // Team cards
              ..._team.asMap().entries.map((e) {
                final i = e.key;
                final t = e.value;
                return Container(
                  margin: const EdgeInsets.only(bottom: 16),
                  decoration: BoxDecoration(
                    color: AppTheme.bgCard,
                    borderRadius: BorderRadius.circular(20),
                    border: Border.all(color: Colors.white.withOpacity(0.05)),
                  ),
                  child: Column(
                    children: [
                      // Avatar area
                      Container(
                        width: double.infinity,
                        height: 160,
                        decoration: BoxDecoration(
                          borderRadius: const BorderRadius.only(
                            topLeft: Radius.circular(20),
                            topRight: Radius.circular(20),
                          ),
                          gradient: LinearGradient(
                            begin: Alignment.topLeft,
                            end: Alignment.bottomRight,
                            colors: [
                              AppTheme.gold.withOpacity(0.15),
                              AppTheme.bgCard,
                            ],
                          ),
                        ),
                        child: Center(
                          child: Container(
                            width: 90,
                            height: 90,
                            decoration: BoxDecoration(
                              shape: BoxShape.circle,
                              color: AppTheme.gold.withOpacity(0.15),
                              border: Border.all(
                                color: AppTheme.gold.withOpacity(0.4),
                                width: 2,
                              ),
                            ),
                            child: Center(
                              child: Text(
                                t['initials']!,
                                style: GoogleFonts.playfairDisplay(
                                  color: AppTheme.gold,
                                  fontSize: 28,
                                  fontWeight: FontWeight.w700,
                                ),
                              ),
                            ),
                          ),
                        ),
                      ),
                      // Info
                      Padding(
                        padding: const EdgeInsets.all(16),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              t['name']!,
                              style: GoogleFonts.playfairDisplay(
                                color: Colors.white,
                                fontSize: 17,
                                fontWeight: FontWeight.w700,
                              ),
                            ),
                            const SizedBox(height: 8),
                            Text(
                              t['desc']!,
                              style: TextStyle(
                                color: Colors.white.withOpacity(0.5),
                                fontSize: 13,
                                height: 1.6,
                              ),
                            ),
                            const SizedBox(height: 12),
                            GestureDetector(
                              onTap: () => launchUrl(Uri.parse(t['link']!)),
                              child: Row(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  Icon(Icons.open_in_new, color: AppTheme.gold, size: 14),
                                  const SizedBox(width: 6),
                                  Text(
                                    'View LinkedIn',
                                    style: TextStyle(
                                      color: AppTheme.gold,
                                      fontSize: 13,
                                      fontWeight: FontWeight.w600,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ).animate().fadeIn(delay: (i * 150).ms).slideY(begin: 0.1, end: 0);
              }),

              const SizedBox(height: 16),

              GestureDetector(
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
                      'Book with Our Team →',
                      style: TextStyle(
                        color: AppTheme.bgDark,
                        fontWeight: FontWeight.w700,
                        fontSize: 15,
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
