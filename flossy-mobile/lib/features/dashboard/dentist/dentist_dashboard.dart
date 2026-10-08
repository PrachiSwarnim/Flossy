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

class DentistDashboard extends StatefulWidget {
  const DentistDashboard({super.key});

  @override
  State<DentistDashboard> createState() => _DentistDashboardState();
}

class _DentistDashboardState extends State<DentistDashboard> with SingleTickerProviderStateMixin {
  late TabController _tabController;
  bool _isLoading = true;

  // Data state
  List<dynamic> _todayAppointments = [];
  List<dynamic> _upcomingAppointments = [];
  List<dynamic> _historyAppointments = [];
  List<dynamic> _patients = [];
  List<dynamic> _prescriptions = [];
  List<dynamic> _invoices = [];

  // Prescription Form State
  String? _selectedPatient;
  final _chiefComplaintController = TextEditingController();
  final _diagnosisController = TextEditingController();
  final _treatmentPlanController = TextEditingController();
  final _recommendationsController = TextEditingController();
  final List<Map<String, String>> _medications = [
    {'name': '', 'dosage': '', 'duration': ''}
  ];
  bool _isPrescSubmitting = false;
  String _patientSearchQuery = '';

  // AI Chat State
  bool _isAiOpen = false;
  final List<Map<String, String>> _aiMessages = [];
  final _aiInputController = TextEditingController();
  bool _isAiTyping = false;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 4, vsync: this);
    _loadAllData();
  }

  @override
  void dispose() {
    _tabController.dispose();
    _chiefComplaintController.dispose();
    _diagnosisController.dispose();
    _treatmentPlanController.dispose();
    _recommendationsController.dispose();
    _aiInputController.dispose();
    super.dispose();
  }

  Future<void> _loadAllData() async {
    setState(() => _isLoading = true);
    final auth = context.read<AuthProvider>();
    final token = auth.token;
    final apiBase = dotenv.env['API_BASE_URL'] ?? 'https://flossy-backend.onrender.com';

    try {
      final headers = {
        if (token != null) 'Authorization': 'Bearer $token',
        'Content-Type': 'application/json',
      };

      // Fetch appointments
      final apptRes = await http.get(Uri.parse('$apiBase/api/appointments'), headers: headers);
      if (apptRes.statusCode == 200) {
        final List<dynamic> allAppts = jsonDecode(apptRes.body);
        final now = DateTime.now();
        final todayStr = "${now.year}-${now.month.toString().padLeft(2, '0')}-${now.day.toString().padLeft(2, '0')}";

        setState(() {
          _todayAppointments = allAppts.where((a) => (a['date'] ?? '').toString().startsWith(todayStr)).toList();
          _upcomingAppointments = allAppts.where((a) {
            final d = a['date'] ?? '';
            return d.compareTo(todayStr) > 0 && a['status'] != 'Cancelled';
          }).toList();
          _historyAppointments = allAppts.where((a) {
            final d = a['date'] ?? '';
            return d.compareTo(todayStr) < 0 || a['status'] == 'Completed' || a['status'] == 'Cancelled';
          }).toList();
        });
      }

      // Fetch patients
      final patRes = await http.get(Uri.parse('$apiBase/api/patients'), headers: headers);
      if (patRes.statusCode == 200) {
        setState(() => _patients = jsonDecode(patRes.body));
      }

      // Fetch prescriptions
      final prescRes = await http.get(Uri.parse('$apiBase/api/prescriptions'), headers: headers);
      if (prescRes.statusCode == 200) {
        setState(() => _prescriptions = jsonDecode(prescRes.body));
      }

      // Fetch invoices
      final invRes = await http.get(Uri.parse('$apiBase/api/invoices'), headers: headers);
      if (invRes.statusCode == 200) {
        setState(() => _invoices = jsonDecode(invRes.body));
      }
    } catch (e) {
      debugPrint('Error loading dentist data: $e');
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Future<void> _submitPrescription() async {
    if (_selectedPatient == null || _selectedPatient!.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please select a patient')),
      );
      return;
    }

    setState(() => _isPrescSubmitting = true);
    final auth = context.read<AuthProvider>();
    final token = auth.token;
    final apiBase = dotenv.env['API_BASE_URL'] ?? 'https://flossy-backend.onrender.com';

    try {
      final validMeds = _medications.where((m) => m['name']!.isNotEmpty).toList();
      final body = jsonEncode({
        'patient_name': _selectedPatient,
        'details': _chiefComplaintController.text,
        'diagnosis': _diagnosisController.text,
        'treatment_plan': _treatmentPlanController.text,
        'recommendations': _recommendationsController.text,
        'medications': validMeds,
        'doctor_name': auth.user?.name ?? 'Dr. Dentist',
        'created_at': DateTime.now().toIso8601String(),
      });

      final res = await http.post(
        Uri.parse('$apiBase/api/prescriptions/create'),
        headers: {
          if (token != null) 'Authorization': 'Bearer $token',
          'Content-Type': 'application/json',
        },
        body: body,
      );

      if (res.statusCode == 200 || res.statusCode == 201) {
        if (!mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Prescription created successfully!')),
        );
        _chiefComplaintController.clear();
        _diagnosisController.clear();
        _treatmentPlanController.clear();
        _recommendationsController.clear();
        setState(() {
          _selectedPatient = null;
          _medications.clear();
          _medications.add({'name': '', 'dosage': '', 'duration': ''});
        });
        _loadAllData();
      } else {
        throw Exception('Failed to create prescription');
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error: $e')),
        );
      }
    } finally {
      if (mounted) setState(() => _isPrescSubmitting = false);
    }
  }

  Future<void> _sendAiMessage() async {
    final text = _aiInputController.text.trim();
    if (text.isEmpty) return;

    setState(() {
      _aiMessages.add({'role': 'user', 'content': text});
      _aiInputController.clear();
      _isAiTyping = true;
    });

    final apiBase = dotenv.env['API_BASE_URL'] ?? 'https://flossy-backend.onrender.com';
    try {
      final res = await http.post(
        Uri.parse('$apiBase/api/ai/chat'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'messages': _aiMessages,
          'user_role': 'dentist',
        }),
      );

      if (res.statusCode == 200) {
        final data = jsonDecode(res.body);
        setState(() {
          _aiMessages.add({
            'role': 'assistant',
            'content': data['reply'] ?? data['response'] ?? 'Clinical insights retrieved.',
          });
        });
      } else {
        setState(() {
          _aiMessages.add({
            'role': 'assistant',
            'content': 'Dr. Flossy AI is processing your clinical query. System response: ${res.statusCode}',
          });
        });
      }
    } catch (e) {
      setState(() {
        _aiMessages.add({
          'role': 'assistant',
          'content': 'Unable to connect to Dental AI Assistant right now.',
        });
      });
    } finally {
      if (mounted) setState(() => _isAiTyping = false);
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
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => setState(() => _isAiOpen = true),
        backgroundColor: AppTheme.cyanHighlight,
        icon: const Icon(Icons.smart_toy_rounded, color: Colors.black),
        label: Text(
          'Clinical AI Assistant',
          style: GoogleFonts.outfit(color: Colors.black, fontWeight: FontWeight.bold),
        ),
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator(color: AppTheme.cyanHighlight))
          : Column(
              children: [
                // Top Welcome Card
                Container(
                  width: double.infinity,
                  margin: const EdgeInsets.all(16),
                  padding: const EdgeInsets.all(20),
                  decoration: BoxDecoration(
                    gradient: LinearGradient(
                      colors: [
                        AppTheme.electricTeal.withOpacity(0.2),
                        AppTheme.deepBlueVariant,
                      ],
                    ),
                    borderRadius: BorderRadius.circular(20),
                    border: Border.all(color: AppTheme.cyanHighlight.withOpacity(0.2)),
                  ),
                  child: Row(
                    children: [
                      CircleAvatar(
                        radius: 28,
                        backgroundColor: AppTheme.cyanHighlight.withOpacity(0.2),
                        child: Text(
                          user?.name.isNotEmpty == true ? user!.name[0].toUpperCase() : 'D',
                          style: GoogleFonts.outfit(
                            fontSize: 24,
                            fontWeight: FontWeight.bold,
                            color: AppTheme.cyanHighlight,
                          ),
                        ),
                      ),
                      const SizedBox(width: 16),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              'Dr. ${user?.name ?? "Dentist"}',
                              style: GoogleFonts.outfit(
                                fontSize: 22,
                                fontWeight: FontWeight.bold,
                                color: Colors.white,
                              ),
                            ),
                            Text(
                              'Clinical Dashboard & Digital Prescriptions',
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

                // Tab Bar
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
                      Tab(icon: Icon(Icons.calendar_month), text: 'Appts'),
                      Tab(icon: Icon(Icons.edit_note), text: 'Prescribe'),
                      Tab(icon: Icon(Icons.people_alt), text: 'Patients'),
                      Tab(icon: Icon(Icons.receipt_long), text: 'Invoices'),
                    ],
                  ),
                ),

                const SizedBox(height: 12),

                // Tab Bar View
                Expanded(
                  child: TabBarView(
                    controller: _tabController,
                    children: [
                      _buildAppointmentsTab(),
                      _buildPrescribeTab(),
                      _buildPatientsTab(),
                      _buildInvoicesTab(),
                    ],
                  ),
                ),
              ],
            ),
      bottomSheet: _isAiOpen ? _buildAiBottomSheet() : null,
    );
  }

  Widget _buildAppointmentsTab() {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _buildSectionHeader('Today\'s Appointments', _todayAppointments.length),
          const SizedBox(height: 10),
          if (_todayAppointments.isEmpty)
            _buildEmptyCard('No appointments scheduled for today.')
          else
            ..._todayAppointments.map((a) => _buildApptCard(a, isToday: true)),

          const SizedBox(height: 24),

          _buildSectionHeader('Upcoming Appointments', _upcomingAppointments.length),
          const SizedBox(height: 10),
          if (_upcomingAppointments.isEmpty)
            _buildEmptyCard('No upcoming appointments.')
          else
            ..._upcomingAppointments.map((a) => _buildApptCard(a)),

          const SizedBox(height: 24),

          _buildSectionHeader('History', _historyAppointments.length),
          const SizedBox(height: 10),
          if (_historyAppointments.isEmpty)
            _buildEmptyCard('No past history.')
          else
            ..._historyAppointments.map((a) => _buildApptCard(a)),
        ],
      ),
    );
  }

  Widget _buildSectionHeader(String title, int count) {
    return Row(
      children: [
        Text(
          title,
          style: GoogleFonts.outfit(
            fontSize: 18,
            fontWeight: FontWeight.bold,
            color: Colors.white,
          ),
        ),
        const SizedBox(width: 8),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
          decoration: BoxDecoration(
            color: AppTheme.cyanHighlight.withOpacity(0.2),
            borderRadius: BorderRadius.circular(10),
          ),
          child: Text(
            '$count',
            style: GoogleFonts.outfit(
              fontSize: 12,
              fontWeight: FontWeight.bold,
              color: AppTheme.cyanHighlight,
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildEmptyCard(String text) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: AppTheme.deepBlueVariant.withOpacity(0.5),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: Colors.white10),
      ),
      child: Text(
        text,
        textAlign: TextAlign.center,
        style: GoogleFonts.plusJakartaSans(color: AppTheme.silverText),
      ),
    );
  }

  Widget _buildApptCard(dynamic appt, {bool isToday = false}) {
    final patientName = appt['patient_name'] ?? appt['user_name'] ?? 'Patient';
    final service = appt['service'] ?? 'General Checkup';
    final time = appt['time'] ?? '10:00 AM';
    final status = appt['status'] ?? 'Confirmed';

    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppTheme.deepBlueVariant,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: isToday ? AppTheme.cyanHighlight.withOpacity(0.5) : Colors.white.withOpacity(0.05),
        ),
      ),
      child: Row(
        children: [
          CircleAvatar(
            backgroundColor: AppTheme.electricTeal.withOpacity(0.2),
            child: const Icon(Icons.person, color: AppTheme.cyanHighlight),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  patientName,
                  style: GoogleFonts.outfit(
                    fontSize: 16,
                    fontWeight: FontWeight.bold,
                    color: Colors.white,
                  ),
                ),
                Text(
                  '$service • $time',
                  style: GoogleFonts.plusJakartaSans(
                    fontSize: 13,
                    color: AppTheme.silverText,
                  ),
                ),
              ],
            ),
          ),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
            decoration: BoxDecoration(
              color: status == 'Confirmed'
                  ? Colors.green.withOpacity(0.2)
                  : Colors.orange.withOpacity(0.2),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Text(
              status,
              style: GoogleFonts.plusJakartaSans(
                fontSize: 12,
                fontWeight: FontWeight.bold,
                color: status == 'Confirmed' ? Colors.greenAccent : Colors.orangeAccent,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildPrescribeTab() {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'New Rx Prescription',
            style: GoogleFonts.outfit(
              fontSize: 20,
              fontWeight: FontWeight.bold,
              color: Colors.white,
            ),
          ),
          const SizedBox(height: 16),

          // Select Patient Dropdown
          Text('Select Patient *', style: GoogleFonts.plusJakartaSans(color: Colors.white70)),
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
                value: _selectedPatient,
                dropdownColor: AppTheme.deepBlueVariant,
                hint: Text('Choose Patient', style: GoogleFonts.plusJakartaSans(color: Colors.white38)),
                isExpanded: true,
                items: _patients.map<DropdownMenuItem<String>>((p) {
                  final name = p['name'] ?? p['full_name'] ?? 'Unknown';
                  return DropdownMenuItem(
                    value: name,
                    child: Text(name, style: GoogleFonts.plusJakartaSans(color: Colors.white)),
                  );
                }).toList(),
                onChanged: (val) => setState(() => _selectedPatient = val),
              ),
            ),
          ),

          const SizedBox(height: 16),

          // Chief Complaint
          _buildTextField('Chief Complaint / Symptoms', _chiefComplaintController, maxLines: 2),
          const SizedBox(height: 16),

          // Diagnosis
          _buildTextField('Diagnosis / Clinical Findings', _diagnosisController, maxLines: 2),
          const SizedBox(height: 16),

          // Treatment Plan
          _buildTextField('Treatment Plan', _treatmentPlanController, maxLines: 2),
          const SizedBox(height: 20),

          // Medications List
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                'Prescribed Medications',
                style: GoogleFonts.outfit(fontSize: 16, fontWeight: FontWeight.bold, color: Colors.white),
              ),
              IconButton(
                icon: const Icon(Icons.add_circle, color: AppTheme.cyanHighlight),
                onPressed: () {
                  setState(() {
                    _medications.add({'name': '', 'dosage': '', 'duration': ''});
                  });
                },
              ),
            ],
          ),

          ..._medications.asMap().entries.map((entry) {
            final idx = entry.key;
            final med = entry.value;
            return Container(
              margin: const EdgeInsets.only(bottom: 10),
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: AppTheme.deepBlueVariant,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: Colors.white10),
              ),
              child: Row(
                children: [
                  Expanded(
                    flex: 2,
                    child: TextField(
                      style: GoogleFonts.plusJakartaSans(color: Colors.white, fontSize: 13),
                      decoration: const InputDecoration(
                        hintText: 'Medicine (e.g. Amoxicillin)',
                        hintStyle: TextStyle(color: Colors.white38),
                        border: InputBorder.none,
                      ),
                      onChanged: (val) => med['name'] = val,
                    ),
                  ),
                  Expanded(
                    child: TextField(
                      style: GoogleFonts.plusJakartaSans(color: Colors.white, fontSize: 13),
                      decoration: const InputDecoration(
                        hintText: 'Dosage',
                        hintStyle: TextStyle(color: Colors.white38),
                        border: InputBorder.none,
                      ),
                      onChanged: (val) => med['dosage'] = val,
                    ),
                  ),
                  if (_medications.length > 1)
                    IconButton(
                      icon: const Icon(Icons.remove_circle, color: Colors.redAccent, size: 20),
                      onPressed: () => setState(() => _medications.removeAt(idx)),
                    ),
                ],
              ),
            );
          }),

          const SizedBox(height: 20),

          // Recommendations
          _buildTextField('Advice / Special Instructions', _recommendationsController, maxLines: 2),

          const SizedBox(height: 24),

          // Submit Button
          SizedBox(
            width: double.infinity,
            height: 50,
            child: ElevatedButton(
              onPressed: _isPrescSubmitting ? null : _submitPrescription,
              style: ElevatedButton.styleFrom(
                backgroundColor: AppTheme.cyanHighlight,
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
              ),
              child: _isPrescSubmitting
                  ? const CircularProgressIndicator(color: Colors.black)
                  : Text(
                      'Issue & Save Prescription',
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

  Widget _buildTextField(String label, TextEditingController controller, {int maxLines = 1}) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: GoogleFonts.plusJakartaSans(color: Colors.white70, fontSize: 13)),
        const SizedBox(height: 6),
        TextField(
          controller: controller,
          maxLines: maxLines,
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

  Widget _buildPatientsTab() {
    final filtered = _patients.where((p) {
      final name = (p['name'] ?? p['full_name'] ?? '').toString().toLowerCase();
      return name.contains(_patientSearchQuery.toLowerCase());
    }).toList();

    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
          child: TextField(
            onChanged: (val) => setState(() => _patientSearchQuery = val),
            style: GoogleFonts.plusJakartaSans(color: Colors.white),
            decoration: InputDecoration(
              hintText: 'Search patients...',
              hintStyle: const TextStyle(color: Colors.white38),
              prefixIcon: const Icon(Icons.search, color: AppTheme.cyanHighlight),
              filled: true,
              fillColor: AppTheme.deepBlueVariant,
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(14),
                borderSide: BorderSide.none,
              ),
            ),
          ),
        ),
        Expanded(
          child: ListView.builder(
            padding: const EdgeInsets.all(16),
            itemCount: filtered.length,
            itemBuilder: (context, index) {
              final pat = filtered[index];
              final name = pat['name'] ?? pat['full_name'] ?? 'Patient';
              final email = pat['email'] ?? 'No email';
              final phone = pat['phone'] ?? pat['phone_number'] ?? 'No phone';

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
          ),
        ),
      ],
    );
  }

  Widget _buildInvoicesTab() {
    return ListView.builder(
      padding: const EdgeInsets.all(16),
      itemCount: _invoices.length,
      itemBuilder: (context, index) {
        final inv = _invoices[index];
        final invNum = inv['invoice_number'] ?? '#INV-${index + 1}';
        final name = inv['patient_name'] ?? 'Patient';
        final amount = inv['amount'] ?? inv['total'] ?? 0;
        final status = inv['status'] ?? 'Paid';

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
              const Icon(Icons.receipt, color: AppTheme.cyanHighlight, size: 28),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(invNum, style: GoogleFonts.outfit(color: AppTheme.cyanHighlight, fontWeight: FontWeight.bold)),
                    Text(name, style: GoogleFonts.outfit(fontSize: 16, color: Colors.white)),
                  ],
                ),
              ),
              Column(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  Text('\$$amount', style: GoogleFonts.outfit(fontSize: 16, color: Colors.white, fontWeight: FontWeight.bold)),
                  Text(status, style: GoogleFonts.plusJakartaSans(fontSize: 12, color: Colors.greenAccent)),
                ],
              ),
            ],
          ),
        );
      },
    );
  }

  Widget _buildAiBottomSheet() {
    return Container(
      height: MediaQuery.of(context).size.height * 0.7,
      decoration: const BoxDecoration(
        color: AppTheme.midnightBlue,
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      child: Column(
        children: [
          // Header
          Container(
            padding: const EdgeInsets.all(16),
            decoration: const BoxDecoration(
              border: Border(bottom: BorderSide(color: Colors.white10)),
            ),
            child: Row(
              children: [
                const Icon(Icons.smart_toy_rounded, color: AppTheme.cyanHighlight),
                const SizedBox(width: 10),
                Text(
                  'Dr. Flossy AI Assistant',
                  style: GoogleFonts.outfit(fontSize: 18, color: Colors.white, fontWeight: FontWeight.bold),
                ),
                const Spacer(),
                IconButton(
                  icon: const Icon(Icons.close, color: Colors.white70),
                  onPressed: () => setState(() => _isAiOpen = false),
                ),
              ],
            ),
          ),

          // Chat messages
          Expanded(
            child: ListView.builder(
              padding: const EdgeInsets.all(16),
              itemCount: _aiMessages.length,
              itemBuilder: (context, index) {
                final msg = _aiMessages[index];
                final isUser = msg['role'] == 'user';
                return Align(
                  alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
                  child: Container(
                    margin: const EdgeInsets.only(bottom: 12),
                    padding: const EdgeInsets.all(14),
                    constraints: BoxConstraints(maxWidth: MediaQuery.of(context).size.width * 0.75),
                    decoration: BoxDecoration(
                      color: isUser ? AppTheme.cyanHighlight : AppTheme.deepBlueVariant,
                      borderRadius: BorderRadius.circular(16),
                    ),
                    child: Text(
                      msg['content'] ?? '',
                      style: GoogleFonts.plusJakartaSans(
                        color: isUser ? Colors.black : Colors.white,
                        fontSize: 14,
                      ),
                    ),
                  ),
                );
              },
            ),
          ),

          if (_isAiTyping)
            const Padding(
              padding: EdgeInsets.all(8.0),
              child: CircularProgressIndicator(color: AppTheme.cyanHighlight),
            ),

          // Input field
          Container(
            padding: const EdgeInsets.all(16),
            decoration: const BoxDecoration(
              border: Border(top: BorderSide(color: Colors.white10)),
            ),
            child: Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _aiInputController,
                    style: GoogleFonts.plusJakartaSans(color: Colors.white),
                    decoration: InputDecoration(
                      hintText: 'Ask about dosage, treatment, or guidelines...',
                      hintStyle: const TextStyle(color: Colors.white38),
                      filled: true,
                      fillColor: AppTheme.deepBlueVariant,
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(14),
                        borderSide: BorderSide.none,
                      ),
                    ),
                  ),
                ),
                const SizedBox(width: 10),
                IconButton(
                  icon: const Icon(Icons.send_rounded, color: AppTheme.cyanHighlight),
                  onPressed: _sendAiMessage,
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
