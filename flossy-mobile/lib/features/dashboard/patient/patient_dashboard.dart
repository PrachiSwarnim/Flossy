import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:go_router/go_router.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'package:intl/intl.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/providers/auth_provider.dart';
import '../shared/dashboard_widgets.dart';

class PatientDashboard extends StatefulWidget {
  const PatientDashboard({super.key});

  @override
  State<PatientDashboard> createState() => _PatientDashboardState();
}

class _PatientDashboardState extends State<PatientDashboard> {
  int _selectedTab = 0;
  bool _isLoading = true;

  List _today = [];
  List _upcoming = [];
  List _history = [];
  List _prescriptions = [];
  Map? _profile;
  String _aiSuggestion = 'Checking your history for the best recommendation...';

  bool _isBookingOpen = false;
  bool _aiOpen = false;
  final _aiMessages = <Map<String, String>>[];
  final _aiInputCtrl = TextEditingController();
  bool _aiTyping = false;
  final _chatScrollCtrl = ScrollController();

  // Booking form
  final _bookingReasonCtrl = TextEditingController();
  String _bookingDate = '';
  String _bookingTime = '';

  @override
  void initState() {
    super.initState();
    _loadAll();
  }

  @override
  void dispose() {
    _aiInputCtrl.dispose();
    _bookingReasonCtrl.dispose();
    _chatScrollCtrl.dispose();
    super.dispose();
  }

  String get _apiBase {
    return context.read<AuthProvider>().apiBase;
  }

  Map<String, String> get _headers {
    final token = context.read<AuthProvider>().token;
    return {
      'Content-Type': 'application/json',
      'Authorization': 'Bearer $token',
    };
  }

  Future<void> _loadAll() async {
    await Future.wait([
      _loadAppointments(),
      _loadPrescriptions(),
      _loadProfile(),
      _loadAiSuggestion(),
    ]);
    if (mounted) setState(() => _isLoading = false);
  }

  Future<void> _loadAppointments() async {
    try {
      final res = await http.get(Uri.parse('$_apiBase/api/appointments/my'), headers: _headers);
      if (res.statusCode == 200) {
        final List<dynamic> raw = data['appointments'] ?? [];
        final all = raw.map((item) => Map<String, dynamic>.from(item)).toList();
        final now = DateTime.now();
        final today = DateFormat('yyyy-MM-dd').format(now);

        if (mounted) {
          setState(() {
            _today = all.where((a) => (a['date'] ?? '').toString().startsWith(today)).toList();
            _upcoming = all.where((a) {
              try {
                final d = DateTime.parse(a['date'] ?? '');
                return d.isAfter(now) && !d.day.toString().startsWith(today);
              } catch (_) {
                return false;
              }
            }).toList();
            _history = all.where((a) {
              try {
                final d = DateTime.parse(a['date'] ?? '');
                return d.isBefore(now);
              } catch (_) {
                return false;
              }
            }).toList();
          });
        }
      }
    } catch (_) {}
  }

  Future<void> _loadPrescriptions() async {
    try {
      final res = await http.get(Uri.parse('$_apiBase/api/prescriptions/my'), headers: _headers);
      if (res.statusCode == 200) {
        final data = json.decode(res.body);
        if (mounted) setState(() => _prescriptions = data['prescriptions'] ?? []);
      }
    } catch (_) {}
  }

  Future<void> _loadProfile() async {
    try {
      final res = await http.get(Uri.parse('$_apiBase/api/patients/me'), headers: _headers);
      if (res.statusCode == 200) {
        if (mounted) setState(() => _profile = json.decode(res.body));
      }
    } catch (_) {}
  }

  Future<void> _loadAiSuggestion() async {
    try {
      final res = await http.get(Uri.parse('$_apiBase/api/ai/ai_suggestion'), headers: _headers);
      if (res.statusCode == 200) {
        final data = json.decode(res.body);
        if (mounted) setState(() => _aiSuggestion = data['suggestion'] ?? _aiSuggestion);
      }
    } catch (_) {}
  }

  Future<void> _sendAiMessage(String msg) async {
    setState(() {
      _aiMessages.add({'role': 'user', 'content': msg});
      _aiTyping = true;
      _aiInputCtrl.clear();
    });

    try {
      final res = await http.post(
        Uri.parse('$_apiBase/api/ai/chat'),
        headers: _headers,
        body: json.encode({
          'message': msg,
          'history': _aiMessages.map((m) => {'role': m['role'], 'content': m['content']}).toList(),
        }),
      );

      if (res.statusCode == 200) {
        final data = json.decode(res.body);
        setState(() {
          _aiMessages.add({'role': 'assistant', 'content': data['reply'] ?? 'Sorry, I could not process that.'});
        });
      }
    } catch (_) {
      setState(() {
        _aiMessages.add({'role': 'assistant', 'content': 'Sorry, I\'m having trouble connecting. Please try again.'});
      });
    }

    setState(() => _aiTyping = false);

    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_chatScrollCtrl.hasClients) {
        _chatScrollCtrl.animateTo(
          _chatScrollCtrl.position.maxScrollExtent,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOut,
        );
      }
    });
  }

  Future<void> _bookAppointment() async {
    if (_bookingReasonCtrl.text.isEmpty || _bookingDate.isEmpty) return;

    try {
      final res = await http.post(
        Uri.parse('$_apiBase/api/appointments/request'),
        headers: _headers,
        body: json.encode({
          'reason': _bookingReasonCtrl.text,
          'preferred_date': _bookingDate,
          'preferred_time': _bookingTime,
        }),
      );

      if (mounted) {
        if (res.statusCode == 200 || res.statusCode == 201) {
          setState(() => _isBookingOpen = false);
          _bookingReasonCtrl.clear();
          _bookingDate = '';
          _bookingTime = '';
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: const Text('Appointment requested successfully!'),
              backgroundColor: Colors.green.shade800,
              behavior: SnackBarBehavior.floating,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
            ),
          );
          _loadAppointments();
        } else {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Failed to request appointment')),
          );
        }
      }
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Network error')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthProvider>();
    final user = auth.user;

    if (_isLoading) {
      return const Scaffold(
        backgroundColor: AppTheme.bgDark,
        body: Center(
          child: CircularProgressIndicator(color: AppTheme.gold),
        ),
      );
    }

    return Scaffold(
      backgroundColor: AppTheme.bgDark,
      body: Stack(
        children: [
          Column(
            children: [
              // Dashboard header
              DashboardHeader(
                userName: user?.fullName ?? 'Patient',
                role: 'Patient',
                onSignOut: () async {
                  await auth.signOut();
                  if (mounted) context.go('/');
                },
              ),

              // Tabs
              Container(
                color: const Color(0xFF141414),
                padding: const EdgeInsets.symmetric(horizontal: 16),
                child: Row(
                  children: [
                    _Tab('Overview', 0, _selectedTab, () => setState(() => _selectedTab = 0)),
                    _Tab('Appointments', 1, _selectedTab, () => setState(() => _selectedTab = 1)),
                    _Tab('Prescriptions', 2, _selectedTab, () => setState(() => _selectedTab = 2)),
                  ],
                ),
              ),

              // Tab content
              Expanded(
                child: _selectedTab == 0
                    ? _buildOverview(user)
                    : _selectedTab == 1
                        ? _buildAppointments()
                        : _buildPrescriptions(),
              ),
            ],
          ),

          // AI Chat overlay
          if (_aiOpen) _buildAIOverlay(),

          // Booking overlay
          if (_isBookingOpen) _buildBookingOverlay(),
        ],
      ),
      floatingActionButton: Column(
        mainAxisAlignment: MainAxisAlignment.end,
        children: [
          // FlossyAI FAB
          FloatingActionButton.small(
            heroTag: 'ai',
            onPressed: () => setState(() => _aiOpen = true),
            backgroundColor: AppTheme.bgCard,
            child: const Icon(Icons.psychology_rounded, color: AppTheme.gold, size: 20),
          ),
          const SizedBox(height: 10),
          // Book Appointment FAB
          FloatingActionButton.extended(
            heroTag: 'book',
            onPressed: () => setState(() => _isBookingOpen = true),
            backgroundColor: AppTheme.gold,
            icon: Icon(Icons.add, color: AppTheme.bgDark),
            label: Text(
              'Book',
              style: TextStyle(color: AppTheme.bgDark, fontWeight: FontWeight.w700),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildOverview(AuthUser? user) {
    return RefreshIndicator(
      color: AppTheme.gold,
      onRefresh: _loadAll,
      child: SingleChildScrollView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Welcome card
            Container(
              padding: const EdgeInsets.all(20),
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  colors: [const Color(0xFF1A1A1A), AppTheme.bgCard],
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                ),
                borderRadius: BorderRadius.circular(20),
                border: Border.all(color: AppTheme.gold.withOpacity(0.1)),
              ),
              child: Row(
                children: [
                  Container(
                    width: 52,
                    height: 52,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      color: AppTheme.gold.withOpacity(0.15),
                      border: Border.all(color: AppTheme.gold.withOpacity(0.3)),
                    ),
                    child: Center(
                      child: Text(
                        (user?.firstName?.isNotEmpty == true ? user!.firstName[0] : 'P').toUpperCase(),
                        style: GoogleFonts.playfairDisplay(
                          color: AppTheme.gold,
                          fontSize: 22,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(width: 14),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Welcome back,',
                          style: TextStyle(
                            color: Colors.white.withOpacity(0.5),
                            fontSize: 12,
                          ),
                        ),
                        Text(
                          user?.fullName ?? 'Patient',
                          style: GoogleFonts.playfairDisplay(
                            color: Colors.white,
                            fontSize: 18,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                        Text(
                          user?.email ?? '',
                          style: TextStyle(
                            color: Colors.white.withOpacity(0.3),
                            fontSize: 11,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ).animate().fadeIn(duration: 500.ms),

            const SizedBox(height: 16),

            // AI Suggestion card
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: AppTheme.gold.withOpacity(0.08),
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: AppTheme.gold.withOpacity(0.2)),
              ),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Icon(Icons.psychology_rounded, color: AppTheme.gold, size: 20),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'FlossyAI Suggestion',
                          style: TextStyle(
                            color: AppTheme.gold,
                            fontSize: 11,
                            fontWeight: FontWeight.w600,
                            letterSpacing: 0.5,
                          ),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          _aiSuggestion,
                          style: TextStyle(
                            color: Colors.white.withOpacity(0.8),
                            fontSize: 13,
                            height: 1.5,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ).animate().fadeIn(delay: 100.ms),

            const SizedBox(height: 20),

            // Stats row
            Row(
              children: [
                _StatCard('Today', _today.length.toString(), Icons.today_rounded),
                const SizedBox(width: 10),
                _StatCard('Upcoming', _upcoming.length.toString(), Icons.calendar_month_rounded),
                const SizedBox(width: 10),
                _StatCard('Prescriptions', _prescriptions.length.toString(), Icons.medication_rounded),
              ],
            ).animate().fadeIn(delay: 200.ms),

            const SizedBox(height: 20),

            // Today's appointments
            if (_today.isNotEmpty) ...[
              Text(
                "Today's Appointments",
                style: GoogleFonts.playfairDisplay(
                  color: Colors.white,
                  fontSize: 16,
                  fontWeight: FontWeight.w700,
                ),
              ),
              const SizedBox(height: 12),
              ..._today.map((a) => AppointmentCard(appt: a)).toList(),
              const SizedBox(height: 16),
            ],

            // Upcoming
            if (_upcoming.isNotEmpty) ...[
              Text(
                'Upcoming Appointments',
                style: GoogleFonts.playfairDisplay(
                  color: Colors.white,
                  fontSize: 16,
                  fontWeight: FontWeight.w700,
                ),
              ),
              const SizedBox(height: 12),
              ..._upcoming.take(3).map((a) => AppointmentCard(appt: a)).toList(),
            ],

            if (_today.isEmpty && _upcoming.isEmpty)
              Center(
                child: Padding(
                  padding: const EdgeInsets.all(32),
                  child: Column(
                    children: [
                      Icon(Icons.calendar_today_rounded, color: Colors.white.withOpacity(0.2), size: 48),
                      const SizedBox(height: 12),
                      Text(
                        'No appointments yet',
                        style: TextStyle(color: Colors.white.withOpacity(0.5), fontSize: 14),
                      ),
                      const SizedBox(height: 8),
                      Text(
                        'Tap "Book" to schedule your first appointment',
                        textAlign: TextAlign.center,
                        style: TextStyle(color: Colors.white.withOpacity(0.3), fontSize: 12),
                      ),
                    ],
                  ),
                ),
              ),

            const SizedBox(height: 80),
          ],
        ),
      ),
    );
  }

  Widget _buildAppointments() {
    return RefreshIndicator(
      color: AppTheme.gold,
      onRefresh: _loadAppointments,
      child: SingleChildScrollView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (_today.isNotEmpty) ...[
              _SectionHeader("Today"),
              ..._today.map((a) => AppointmentCard(appt: a)),
              const SizedBox(height: 16),
            ],
            if (_upcoming.isNotEmpty) ...[
              _SectionHeader('Upcoming'),
              ..._upcoming.map((a) => AppointmentCard(appt: a)),
              const SizedBox(height: 16),
            ],
            if (_history.isNotEmpty) ...[
              _SectionHeader('History'),
              ..._history.take(10).map((a) => AppointmentCard(appt: a, isHistory: true)),
            ],
            if (_today.isEmpty && _upcoming.isEmpty && _history.isEmpty)
              _EmptyState(
                icon: Icons.calendar_today_rounded,
                title: 'No appointments',
                subtitle: 'Tap Book to get started',
              ),
            const SizedBox(height: 80),
          ],
        ),
      ),
    );
  }

  Widget _buildPrescriptions() {
    return RefreshIndicator(
      color: AppTheme.gold,
      onRefresh: _loadPrescriptions,
      child: _prescriptions.isEmpty
          ? _EmptyState(
              icon: Icons.medication_rounded,
              title: 'No prescriptions',
              subtitle: 'Your prescriptions will appear here',
            )
          : ListView.builder(
              padding: const EdgeInsets.all(16),
              itemCount: _prescriptions.length,
              itemBuilder: (context, i) {
                final p = _prescriptions[i];
                return Container(
                  margin: const EdgeInsets.only(bottom: 12),
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(
                    color: AppTheme.bgCard,
                    borderRadius: BorderRadius.circular(16),
                    border: Border.all(color: Colors.white.withOpacity(0.06)),
                  ),
                  child: Row(
                    children: [
                      Container(
                        width: 44,
                        height: 44,
                        decoration: BoxDecoration(
                          color: AppTheme.gold.withOpacity(0.1),
                          borderRadius: BorderRadius.circular(12),
                          border: Border.all(color: AppTheme.gold.withOpacity(0.2)),
                        ),
                        child: const Icon(Icons.medication_rounded, color: AppTheme.gold, size: 20),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              'Dr. ${p['doctor'] ?? 'Dentist'}',
                              style: GoogleFonts.playfairDisplay(
                                color: Colors.white,
                                fontSize: 14,
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                            Text(
                              p['date'] ?? '',
                              style: TextStyle(
                                color: Colors.white.withOpacity(0.4),
                                fontSize: 11,
                              ),
                            ),
                          ],
                        ),
                      ),
                      Icon(Icons.arrow_forward_ios, color: Colors.white.withOpacity(0.2), size: 14),
                    ],
                  ),
                );
              },
            ),
    );
  }

  Widget _buildAIOverlay() {
    return Container(
      color: Colors.black.withOpacity(0.7),
      child: Align(
        alignment: Alignment.bottomCenter,
        child: Container(
          height: MediaQuery.of(context).size.height * 0.75,
          decoration: const BoxDecoration(
            color: Color(0xFF141414),
            borderRadius: BorderRadius.only(
              topLeft: Radius.circular(24),
              topRight: Radius.circular(24),
            ),
          ),
          child: Column(
            children: [
              // Header
              Padding(
                padding: const EdgeInsets.fromLTRB(20, 16, 16, 12),
                child: Row(
                  children: [
                    Icon(Icons.psychology_rounded, color: AppTheme.gold, size: 20),
                    const SizedBox(width: 8),
                    Text(
                      'FlossyAI Assistant',
                      style: GoogleFonts.playfairDisplay(
                        color: Colors.white,
                        fontSize: 16,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    const Spacer(),
                    GestureDetector(
                      onTap: () => setState(() => _aiOpen = false),
                      child: const Icon(Icons.close, color: Colors.white54, size: 20),
                    ),
                  ],
                ),
              ),
              const Divider(color: AppTheme.borderColor, height: 1),

              // Messages
              Expanded(
                child: _aiMessages.isEmpty
                    ? Center(
                        child: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Icon(Icons.psychology_rounded, color: AppTheme.gold.withOpacity(0.3), size: 48),
                            const SizedBox(height: 12),
                            Text(
                              'How can I help you today?',
                              style: TextStyle(color: Colors.white.withOpacity(0.5), fontSize: 14),
                            ),
                          ],
                        ),
                      )
                    : ListView.builder(
                        controller: _chatScrollCtrl,
                        padding: const EdgeInsets.all(16),
                        itemCount: _aiMessages.length + (_aiTyping ? 1 : 0),
                        itemBuilder: (context, i) {
                          if (_aiTyping && i == _aiMessages.length) {
                            return _ChatBubble(
                              message: '...',
                              isUser: false,
                              isTyping: true,
                            );
                          }
                          final m = _aiMessages[i];
                          return _ChatBubble(
                            message: m['content'] ?? '',
                            isUser: m['role'] == 'user',
                          );
                        },
                      ),
              ),

              // Input
              Container(
                padding: const EdgeInsets.fromLTRB(16, 8, 16, 16),
                decoration: const BoxDecoration(
                  border: Border(top: BorderSide(color: AppTheme.borderColor)),
                ),
                child: Row(
                  children: [
                    Expanded(
                      child: TextField(
                        controller: _aiInputCtrl,
                        style: const TextStyle(color: Colors.white, fontSize: 14),
                        decoration: InputDecoration(
                          hintText: 'Ask FlossyAI...',
                          hintStyle: TextStyle(color: Colors.white.withOpacity(0.3), fontSize: 14),
                          border: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(12),
                            borderSide: BorderSide(color: Colors.white.withOpacity(0.1)),
                          ),
                          enabledBorder: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(12),
                            borderSide: BorderSide(color: Colors.white.withOpacity(0.1)),
                          ),
                          focusedBorder: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(12),
                            borderSide: const BorderSide(color: AppTheme.gold),
                          ),
                          filled: true,
                          fillColor: AppTheme.bgInput,
                          contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                        ),
                        onSubmitted: (v) {
                          if (v.trim().isNotEmpty) _sendAiMessage(v.trim());
                        },
                      ),
                    ),
                    const SizedBox(width: 10),
                    GestureDetector(
                      onTap: () {
                        final msg = _aiInputCtrl.text.trim();
                        if (msg.isNotEmpty) _sendAiMessage(msg);
                      },
                      child: Container(
                        width: 44,
                        height: 44,
                        decoration: BoxDecoration(
                          color: AppTheme.gold,
                          borderRadius: BorderRadius.circular(12),
                        ),
                        child: Icon(Icons.send_rounded, color: AppTheme.bgDark, size: 18),
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildBookingOverlay() {
    return Container(
      color: Colors.black.withOpacity(0.7),
      child: Align(
        alignment: Alignment.bottomCenter,
        child: Container(
          padding: const EdgeInsets.all(20),
          decoration: const BoxDecoration(
            color: Color(0xFF141414),
            borderRadius: BorderRadius.only(
              topLeft: Radius.circular(24),
              topRight: Radius.circular(24),
            ),
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Text(
                    'Request Appointment',
                    style: GoogleFonts.playfairDisplay(
                      color: Colors.white,
                      fontSize: 18,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  const Spacer(),
                  GestureDetector(
                    onTap: () => setState(() => _isBookingOpen = false),
                    child: const Icon(Icons.close, color: Colors.white54, size: 20),
                  ),
                ],
              ),
              const SizedBox(height: 20),
              TextField(
                controller: _bookingReasonCtrl,
                style: const TextStyle(color: Colors.white),
                decoration: const InputDecoration(
                  labelText: 'Reason for visit',
                  prefixIcon: Icon(Icons.medical_services_outlined, color: AppTheme.textMuted, size: 18),
                ),
              ),
              const SizedBox(height: 12),
              TextField(
                readOnly: true,
                style: const TextStyle(color: Colors.white),
                decoration: InputDecoration(
                  labelText: _bookingDate.isEmpty ? 'Preferred date (tap to pick)' : _bookingDate,
                  prefixIcon: const Icon(Icons.calendar_today, color: AppTheme.textMuted, size: 18),
                ),
                onTap: () async {
                  final d = await showDatePicker(
                    context: context,
                    initialDate: DateTime.now().add(const Duration(days: 1)),
                    firstDate: DateTime.now(),
                    lastDate: DateTime.now().add(const Duration(days: 90)),
                    builder: (context, child) => Theme(
                      data: ThemeData.dark().copyWith(
                        colorScheme: const ColorScheme.dark(primary: AppTheme.gold),
                      ),
                      child: child!,
                    ),
                  );
                  if (d != null) {
                    setState(() => _bookingDate = DateFormat('yyyy-MM-dd').format(d));
                  }
                },
              ),
              const SizedBox(height: 20),
              SizedBox(
                width: double.infinity,
                child: ElevatedButton(
                  onPressed: _bookAppointment,
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppTheme.gold,
                    padding: const EdgeInsets.symmetric(vertical: 14),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                  ),
                  child: Text(
                    'Request Appointment',
                    style: TextStyle(
                      color: AppTheme.bgDark,
                      fontWeight: FontWeight.w700,
                      fontSize: 14,
                    ),
                  ),
                ),
              ),
              SizedBox(height: MediaQuery.of(context).viewInsets.bottom + 16),
            ],
          ),
        ),
      ),
    );
  }
}

// ── Shared sub-widgets ──────────────────────────────────

class _Tab extends StatelessWidget {
  final String label;
  final int index;
  final int current;
  final VoidCallback onTap;

  const _Tab(this.label, this.index, this.current, this.onTap);

  @override
  Widget build(BuildContext context) {
    final selected = index == current;
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
        decoration: BoxDecoration(
          border: Border(
            bottom: BorderSide(
              color: selected ? AppTheme.gold : Colors.transparent,
              width: 2,
            ),
          ),
        ),
        child: Text(
          label,
          style: TextStyle(
            color: selected ? AppTheme.gold : Colors.white54,
            fontSize: 13,
            fontWeight: selected ? FontWeight.w600 : FontWeight.w400,
          ),
        ),
      ),
    );
  }
}

class _StatCard extends StatelessWidget {
  final String label;
  final String value;
  final IconData icon;

  const _StatCard(this.label, this.value, this.icon);

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: AppTheme.bgCard,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: Colors.white.withOpacity(0.06)),
        ),
        child: Column(
          children: [
            Icon(icon, color: AppTheme.gold, size: 20),
            const SizedBox(height: 8),
            Text(
              value,
              style: GoogleFonts.playfairDisplay(
                color: Colors.white,
                fontSize: 20,
                fontWeight: FontWeight.w700,
              ),
            ),
            const SizedBox(height: 2),
            Text(
              label,
              textAlign: TextAlign.center,
              style: TextStyle(
                color: Colors.white.withOpacity(0.4),
                fontSize: 10,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _SectionHeader extends StatelessWidget {
  final String title;
  const _SectionHeader(this.title);

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Text(
        title,
        style: GoogleFonts.playfairDisplay(
          color: Colors.white,
          fontSize: 16,
          fontWeight: FontWeight.w700,
        ),
      ),
    );
  }
}

class _EmptyState extends StatelessWidget {
  final IconData icon;
  final String title;
  final String subtitle;

  const _EmptyState({required this.icon, required this.title, required this.subtitle});

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(48),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(icon, color: Colors.white.withOpacity(0.15), size: 56),
            const SizedBox(height: 14),
            Text(title, style: TextStyle(color: Colors.white.withOpacity(0.5), fontSize: 15)),
            const SizedBox(height: 6),
            Text(
              subtitle,
              textAlign: TextAlign.center,
              style: TextStyle(color: Colors.white.withOpacity(0.3), fontSize: 12),
            ),
          ],
        ),
      ),
    );
  }
}

class _ChatBubble extends StatelessWidget {
  final String message;
  final bool isUser;
  final bool isTyping;

  const _ChatBubble({
    required this.message,
    required this.isUser,
    this.isTyping = false,
  });

  @override
  Widget build(BuildContext context) {
    return Align(
      alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
      child: Container(
        margin: const EdgeInsets.only(bottom: 10),
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
        constraints: BoxConstraints(
          maxWidth: MediaQuery.of(context).size.width * 0.75,
        ),
        decoration: BoxDecoration(
          color: isUser ? AppTheme.gold.withOpacity(0.15) : const Color(0xFF1E1E1E),
          borderRadius: BorderRadius.circular(14),
          border: Border.all(
            color: isUser ? AppTheme.gold.withOpacity(0.3) : Colors.white.withOpacity(0.06),
          ),
        ),
        child: isTyping
            ? Row(
                mainAxisSize: MainAxisSize.min,
                children: List.generate(3, (i) {
                  return Container(
                    width: 6,
                    height: 6,
                    margin: const EdgeInsets.symmetric(horizontal: 2),
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      color: AppTheme.gold.withOpacity(0.6),
                    ),
                  );
                }),
              )
            : Text(
                message,
                style: TextStyle(
                  color: isUser ? AppTheme.gold : Colors.white.withOpacity(0.85),
                  fontSize: 13,
                  height: 1.5,
                ),
              ),
      ),
    );
  }
}
