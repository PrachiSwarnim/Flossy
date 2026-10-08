import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:go_router/go_router.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:http/http.dart' as http;
import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:url_launcher/url_launcher.dart';
import '../../../../core/theme/app_theme.dart';
import '../../../../core/providers/auth_provider.dart';
import '../../../../shared/widgets/app_header.dart';

class ReceptionistDashboard extends StatefulWidget {
  const ReceptionistDashboard({super.key});

  @override
  State<ReceptionistDashboard> createState() => _ReceptionistDashboardState();
}

class _ReceptionistDashboardState extends State<ReceptionistDashboard> with SingleTickerProviderStateMixin {
  late TabController _tabController;
  bool _isLoading = true;

  List<dynamic> _appointments = [];
  List<dynamic> _patients = [];
  List<dynamic> _invoices = [];
  String _searchQuery = '';
  String _statusFilter = 'All';

  // New Appointment Form State
  final _patientNameController = TextEditingController();
  final _phoneController = TextEditingController();
  final _emailController = TextEditingController();
  String _selectedService = 'Teeth Cleaning';
  String _selectedDentist = 'Dr. Sarah Jenkins';
  DateTime _selectedDate = DateTime.now();
  String _selectedTime = '10:00 AM';
  bool _isBooking = false;

  final List<String> _services = [
    'Teeth Cleaning',
    'Root Canal Treatment',
    'Dental Implants',
    'Teeth Whitening',
    'Braces & Aligners',
    'Tooth Extraction',
    'Pediatric Dentistry',
  ];

  final List<String> _dentists = [
    'Dr. Sarah Jenkins',
    'Dr. Michael Chen',
    'Dr. Elena Rostova',
  ];

  final List<String> _timeSlots = [
    '09:00 AM', '10:00 AM', '11:00 AM', '12:00 PM',
    '02:00 PM', '03:00 PM', '04:00 PM', '05:00 PM'
  ];

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 3, vsync: this);
    _fetchData();
  }

  @override
  void dispose() {
    _tabController.dispose();
    _patientNameController.dispose();
    _phoneController.dispose();
    _emailController.dispose();
    super.dispose();
  }

  Future<void> _fetchData() async {
    setState(() => _isLoading = true);
    final auth = context.read<AuthProvider>();
    final token = auth.token;
    final apiBase = dotenv.env['API_BASE_URL'] ?? 'https://flossy-backend.onrender.com';

    try {
      final headers = {
        if (token != null) 'Authorization': 'Bearer $token',
        'Content-Type': 'application/json',
      };

      final apptRes = await http.get(Uri.parse('$apiBase/api/appointments'), headers: headers);
      if (apptRes.statusCode == 200) {
        setState(() => _appointments = jsonDecode(apptRes.body));
      }

      final patRes = await http.get(Uri.parse('$apiBase/api/patients'), headers: headers);
      if (patRes.statusCode == 200) {
        setState(() => _patients = jsonDecode(patRes.body));
      }

      final invRes = await http.get(Uri.parse('$apiBase/api/invoices'), headers: headers);
      if (invRes.statusCode == 200) {
        setState(() => _invoices = jsonDecode(invRes.body));
      }
    } catch (e) {
      debugPrint('Error fetching receptionist data: $e');
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Future<void> _updateApptStatus(dynamic apptId, String newStatus) async {
    final auth = context.read<AuthProvider>();
    final token = auth.token;
    final apiBase = dotenv.env['API_BASE_URL'] ?? 'https://flossy-backend.onrender.com';

    try {
      final res = await http.patch(
        Uri.parse('$apiBase/api/appointments/$apptId'),
        headers: {
          if (token != null) 'Authorization': 'Bearer $token',
          'Content-Type': 'application/json',
        },
        body: jsonEncode({'status': newStatus}),
      );

      if (res.statusCode == 200) {
        _fetchData();
      }
    } catch (e) {
      debugPrint('Error updating appt status: $e');
    }
  }

  Future<void> _bookAppointment() async {
    if (_patientNameController.text.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please enter patient name')),
      );
      return;
    }

    setState(() => _isBooking = true);
    final auth = context.read<AuthProvider>();
    final token = auth.token;
    final apiBase = dotenv.env['API_BASE_URL'] ?? 'https://flossy-backend.onrender.com';

    try {
      final dateStr = "${_selectedDate.year}-${_selectedDate.month.toString().padLeft(2, '0')}-${_selectedDate.day.toString().padLeft(2, '0')}";
      final body = jsonEncode({
        'patient_name': _patientNameController.text.trim(),
        'phone': _phoneController.text.trim(),
        'email': _emailController.text.trim(),
        'service': _selectedService,
        'dentist_name': _selectedDentist,
        'date': dateStr,
        'time': _selectedTime,
        'status': 'Confirmed',
      });

      final res = await http.post(
        Uri.parse('$apiBase/api/appointments/create'),
        headers: {
          if (token != null) 'Authorization': 'Bearer $token',
          'Content-Type': 'application/json',
        },
        body: body,
      );

      if (res.statusCode == 200 || res.statusCode == 201) {
        if (!mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Appointment booked & patient registered!')),
        );
        _patientNameController.clear();
        _phoneController.clear();
        _emailController.clear();
        _fetchData();
      } else {
        throw Exception('Failed to book appointment');
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error: $e')),
        );
      }
    } finally {
      if (mounted) setState(() => _isBooking = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthProvider>();
    final user = auth.user;

    return Scaffold(
      backgroundColor: AppTheme.midnightBlue,
      appBar: PreferredSize(
        preferredSize: const Size.fromHeight(70),
        child: Container(
          color: AppTheme.midnightBlue,
          child: const SafeArea(child: AppHeader()),
        ),
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator(color: AppTheme.cyanHighlight))
          : Column(
              children: [
                // Top Header Card
                Container(
                  width: double.infinity,
                  margin: const EdgeInsets.all(16),
                  padding: const EdgeInsets.all(20),
                  decoration: BoxDecoration(
                    gradient: LinearGradient(
                      colors: [
                        AppTheme.cyanHighlight.withOpacity(0.15),
                        AppTheme.deepBlueVariant,
                      ],
                    ),
                    borderRadius: BorderRadius.circular(20),
                    border: Border.all(color: AppTheme.cyanHighlight.withOpacity(0.2)),
                  ),
                  child: Row(
                    children: [
                      CircleAvatar(
                        radius: 26,
                        backgroundColor: AppTheme.cyanHighlight.withOpacity(0.2),
                        child: const Icon(Icons.desk_rounded, color: AppTheme.cyanHighlight),
                      ),
                      const SizedBox(width: 14),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              'Reception Console',
                              style: GoogleFonts.outfit(
                                fontSize: 20,
                                fontWeight: FontWeight.bold,
                                color: Colors.white,
                              ),
                            ),
                            Text(
                              'Manage Clinic Schedule, Check-Ins & Invoicing',
                              style: GoogleFonts.plusJakartaSans(
                                fontSize: 13,
                                color: AppTheme.silverText,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ).animate().fadeIn().slideY(begin: -0.1),

                // Navigation Tabs
                Container(
                  margin: const EdgeInsets.horizontal(16),
                  decoration: BoxDecoration(
                    color: AppTheme.deepBlueVariant,
                    borderRadius: BorderRadius.circular(14),
                  ),
                  child: TabBar(
                    controller: _tabController,
                    indicatorColor: AppTheme.cyanHighlight,
                    labelColor: AppTheme.cyanHighlight,
                    unselectedLabelColor: AppTheme.silverText,
                    indicatorSize: TabBarIndicatorSize.tab,
                    tabs: const [
                      Tab(icon: Icon(Icons.event_note), text: 'Appointments'),
                      Tab(icon: Icon(Icons.person_add), text: 'New Booking'),
                      Tab(icon: Icon(Icons.folder_shared), text: 'Patients'),
                    ],
                  ),
                ),

                const SizedBox(height: 12),

                // Content
                Expanded(
                  child: TabBarView(
                    controller: _tabController,
                    children: [
                      _buildAppointmentsView(),
                      _buildNewBookingView(),
                      _buildPatientsView(),
                    ],
                  ),
                ),
              ],
            ),
    );
  }

  Widget _buildAppointmentsView() {
    final filtered = _appointments.where((a) {
      final name = (a['patient_name'] ?? a['user_name'] ?? '').toString().toLowerCase();
      final matchesSearch = name.contains(_searchQuery.toLowerCase());
      if (_statusFilter == 'All') return matchesSearch;
      return matchesSearch && a['status'] == _statusFilter;
    }).toList();

    return Column(
      children: [
        // Search & Filter bar
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16),
          child: Row(
            children: [
              Expanded(
                child: TextField(
                  onChanged: (val) => setState(() => _searchQuery = val),
                  style: GoogleFonts.plusJakartaSans(color: Colors.white, fontSize: 14),
                  decoration: InputDecoration(
                    hintText: 'Search patient...',
                    hintStyle: const TextStyle(color: Colors.white38),
                    prefixIcon: const Icon(Icons.search, color: AppTheme.cyanHighlight),
                    filled: true,
                    fillColor: AppTheme.deepBlueVariant,
                    contentPadding: const EdgeInsets.symmetric(vertical: 10),
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(12),
                      borderSide: BorderSide.none,
                    ),
                  ),
                ),
              ),
              const SizedBox(width: 10),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 12),
                decoration: BoxDecoration(
                  color: AppTheme.deepBlueVariant,
                  borderRadius: BorderRadius.circular(12),
                ),
                child: DropdownButtonHideUnderline(
                  child: DropdownButton<String>(
                    value: _statusFilter,
                    dropdownColor: AppTheme.deepBlueVariant,
                    style: GoogleFonts.plusJakartaSans(color: Colors.white, fontSize: 13),
                    items: ['All', 'Confirmed', 'Checked In', 'Completed', 'Cancelled']
                        .map((s) => DropdownMenuItem(value: s, child: Text(s)))
                        .toList(),
                    onChanged: (val) => setState(() => _statusFilter = val!),
                  ),
                ),
              ),
            ],
          ),
        ),

        const SizedBox(height: 12),

        // List
        Expanded(
          child: filtered.isEmpty
              ? Center(
                  child: Text(
                    'No appointments found.',
                    style: GoogleFonts.plusJakartaSans(color: AppTheme.silverText),
                  ),
                )
              : ListView.builder(
                  padding: const EdgeInsets.all(16),
                  itemCount: filtered.length,
                  itemBuilder: (context, index) {
                    final appt = filtered[index];
                    final name = appt['patient_name'] ?? appt['user_name'] ?? 'Patient';
                    final phone = appt['phone'] ?? 'N/A';
                    final service = appt['service'] ?? 'Consultation';
                    final dentist = appt['dentist_name'] ?? 'Dr. Jenkins';
                    final date = appt['date'] ?? 'Today';
                    final time = appt['time'] ?? '10:00 AM';
                    final status = appt['status'] ?? 'Confirmed';
                    final id = appt['id'] ?? appt['_id'];

                    return Container(
                      margin: const EdgeInsets.only(bottom: 12),
                      padding: const EdgeInsets.all(16),
                      decoration: BoxDecoration(
                        color: AppTheme.deepBlueVariant,
                        borderRadius: BorderRadius.circular(16),
                        border: Border.all(color: Colors.white.withOpacity(0.05)),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            children: [
                              Text(
                                name,
                                style: GoogleFonts.outfit(
                                  fontSize: 17,
                                  fontWeight: FontWeight.bold,
                                  color: Colors.white,
                                ),
                              ),
                              PopupMenuButton<String>(
                                icon: const Icon(Icons.more_vert, color: Colors.white70),
                                color: AppTheme.deepBlueVariant,
                                onSelected: (st) => _updateApptStatus(id, st),
                                itemBuilder: (context) => [
                                  const PopupMenuItem(value: 'Checked In', child: Text('Mark Checked In', style: TextStyle(color: Colors.white))),
                                  const PopupMenuItem(value: 'Completed', child: Text('Mark Completed', style: TextStyle(color: Colors.white))),
                                  const PopupMenuItem(value: 'Cancelled', child: Text('Cancel Appt', style: TextStyle(color: Colors.redAccent))),
                                ],
                              ),
                            ],
                          ),
                          const SizedBox(height: 4),
                          Text(
                            '$service • $dentist',
                            style: GoogleFonts.plusJakartaSans(
                              fontSize: 13,
                              color: AppTheme.cyanHighlight,
                            ),
                          ),
                          const SizedBox(height: 4),
                          Row(
                            children: [
                              Icon(Icons.calendar_today, size: 14, color: AppTheme.silverText),
                              const SizedBox(width: 6),
                              Text('$date at $time', style: GoogleFonts.plusJakartaSans(fontSize: 12, color: AppTheme.silverText)),
                              const Spacer(),
                              Container(
                                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                                decoration: BoxDecoration(
                                  color: status == 'Completed'
                                      ? Colors.blue.withOpacity(0.2)
                                      : status == 'Checked In'
                                          ? Colors.green.withOpacity(0.2)
                                          : Colors.orange.withOpacity(0.2),
                                  borderRadius: BorderRadius.circular(8),
                                ),
                                child: Text(
                                  status,
                                  style: GoogleFonts.plusJakartaSans(
                                    fontSize: 12,
                                    fontWeight: FontWeight.bold,
                                    color: status == 'Completed'
                                        ? Colors.blueAccent
                                        : status == 'Checked In'
                                            ? Colors.greenAccent
                                            : Colors.orangeAccent,
                                  ),
                                ),
                              ),
                            ],
                          ),

                          const SizedBox(height: 12),
                          Row(
                            children: [
                              OutlinedButton.icon(
                                onPressed: () async {
                                  final uri = Uri.parse('tel:$phone');
                                  if (await canLaunchUrl(uri)) launchUrl(uri);
                                },
                                icon: const Icon(Icons.phone, size: 16, color: AppTheme.cyanHighlight),
                                label: Text('Call', style: GoogleFonts.plusJakartaSans(color: AppTheme.cyanHighlight, fontSize: 12)),
                                style: OutlinedButton.styleFrom(
                                  side: BorderSide(color: AppTheme.cyanHighlight.withOpacity(0.4)),
                                ),
                              ),
                              const SizedBox(width: 8),
                              OutlinedButton.icon(
                                onPressed: () async {
                                  final cleanPhone = phone.replaceAll(RegExp(r'[^\d]'), '');
                                  final uri = Uri.parse('https://wa.me/$cleanPhone');
                                  if (await canLaunchUrl(uri)) launchUrl(uri);
                                },
                                icon: const Icon(Icons.chat_bubble, size: 16, color: Colors.greenAccent),
                                label: Text('WhatsApp', style: GoogleFonts.plusJakartaSans(color: Colors.greenAccent, fontSize: 12)),
                                style: OutlinedButton.styleFrom(
                                  side: BorderSide(color: Colors.greenAccent.withOpacity(0.4)),
                                ),
                              ),
                            ],
                          ),
                        ],
                      ),
                    );
                  },
                ),
        ),
      ],
    );
  }

  Widget _buildNewBookingView() {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Register & Schedule Patient',
            style: GoogleFonts.outfit(
              fontSize: 20,
              fontWeight: FontWeight.bold,
              color: Colors.white,
            ),
          ),
          const SizedBox(height: 16),

          _buildField('Patient Full Name *', _patientNameController),
          const SizedBox(height: 14),
          _buildField('Phone Number', _phoneController, keyboardType: TextInputType.phone),
          const SizedBox(height: 14),
          _buildField('Email Address', _emailController, keyboardType: TextInputType.emailAddress),
          const SizedBox(height: 16),

          Text('Select Service', style: GoogleFonts.plusJakartaSans(color: Colors.white70, fontSize: 13)),
          const SizedBox(height: 6),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 14),
            decoration: BoxDecoration(
              color: AppTheme.deepBlueVariant,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: Colors.white10),
            ),
            child: DropdownButtonHideUnderline(
              child: DropdownButton<String>(
                value: _selectedService,
                dropdownColor: AppTheme.deepBlueVariant,
                isExpanded: true,
                items: _services.map((s) => DropdownMenuItem(value: s, child: Text(s, style: const TextStyle(color: Colors.white)))).toList(),
                onChanged: (val) => setState(() => _selectedService = val!),
              ),
            ),
          ),

          const SizedBox(height: 16),

          Text('Assigned Dentist', style: GoogleFonts.plusJakartaSans(color: Colors.white70, fontSize: 13)),
          const SizedBox(height: 6),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 14),
            decoration: BoxDecoration(
              color: AppTheme.deepBlueVariant,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: Colors.white10),
            ),
            child: DropdownButtonHideUnderline(
              child: DropdownButton<String>(
                value: _selectedDentist,
                dropdownColor: AppTheme.deepBlueVariant,
                isExpanded: true,
                items: _dentists.map((d) => DropdownMenuItem(value: d, child: Text(d, style: const TextStyle(color: Colors.white)))).toList(),
                onChanged: (val) => setState(() => _selectedDentist = val!),
              ),
            ),
          ),

          const SizedBox(height: 16),

          Text('Time Slot', style: GoogleFonts.plusJakartaSans(color: Colors.white70, fontSize: 13)),
          const SizedBox(height: 6),
          Wrap(
            spacing: 8,
            children: _timeSlots.map((slot) {
              final isSelected = _selectedTime == slot;
              return ChoiceChip(
                label: Text(slot),
                selected: isSelected,
                selectedColor: AppTheme.cyanHighlight,
                backgroundColor: AppTheme.deepBlueVariant,
                labelStyle: TextStyle(
                  color: isSelected ? Colors.black : Colors.white,
                  fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
                ),
                onSelected: (sel) => setState(() => _selectedTime = slot),
              );
            }).toList(),
          ),

          const SizedBox(height: 24),

          SizedBox(
            width: double.infinity,
            height: 50,
            child: ElevatedButton(
              onPressed: _isBooking ? null : _bookAppointment,
              style: ElevatedButton.styleFrom(
                backgroundColor: AppTheme.cyanHighlight,
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
              ),
              child: _isBooking
                  ? const CircularProgressIndicator(color: Colors.black)
                  : Text(
                      'Confirm Appointment',
                      style: GoogleFonts.outfit(
                        fontSize: 16,
                        fontWeight: FontWeight.bold,
                        color: Colors.black,
                      ),
                    ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildPatientsView() {
    return ListView.builder(
      padding: const EdgeInsets.all(16),
      itemCount: _patients.length,
      itemBuilder: (context, index) {
        final pat = _patients[index];
        final name = pat['name'] ?? pat['full_name'] ?? 'Patient';
        final phone = pat['phone'] ?? pat['phone_number'] ?? 'N/A';
        final email = pat['email'] ?? 'N/A';

        return Container(
          margin: const EdgeInsets.only(bottom: 12),
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: AppTheme.deepBlueVariant,
            borderRadius: BorderRadius.circular(14),
            border: Border.all(color: Colors.white.withOpacity(0.05)),
          ),
          child: Row(
            children: [
              CircleAvatar(
                backgroundColor: AppTheme.cyanHighlight.withOpacity(0.2),
                child: Text(
                  name.isNotEmpty ? name[0].toUpperCase() : 'P',
                  style: GoogleFonts.outfit(color: AppTheme.cyanHighlight, fontWeight: FontWeight.bold),
                ),
              ),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(name, style: GoogleFonts.outfit(fontSize: 16, color: Colors.white, fontWeight: FontWeight.bold)),
                    Text('$email • $phone', style: GoogleFonts.plusJakartaSans(fontSize: 12, color: AppTheme.silverText)),
                  ],
                ),
              ),
            ],
          ),
        );
      },
    );
  }

  Widget _buildField(String label, TextEditingController controller, {TextInputType keyboardType = TextInputType.text}) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: GoogleFonts.plusJakartaSans(color: Colors.white70, fontSize: 13)),
        const SizedBox(height: 6),
        TextField(
          controller: controller,
          keyboardType: keyboardType,
          style: GoogleFonts.plusJakartaSans(color: Colors.white, fontSize: 14),
          decoration: InputDecoration(
            filled: true,
            fillColor: AppTheme.deepBlueVariant,
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
              borderSide: const BorderSide(color: AppTheme.cyanHighlight),
            ),
          ),
        ),
      ],
    );
  }
}
