import 'package:flutter/foundation.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:flutter_dotenv/flutter_dotenv.dart';

class AuthUser {
  final String id;
  final String email;
  final String firstName;
  final String lastName;
  final String role;
  final String? imageUrl;

  AuthUser({
    required this.id,
    required this.email,
    required this.firstName,
    required this.lastName,
    required this.role,
    this.imageUrl,
  });

  String get fullName => '$firstName $lastName'.trim();
  String get name => fullName.isNotEmpty ? fullName : (email.isNotEmpty ? email.split('@')[0] : 'User');

  factory AuthUser.fromJson(Map<String, dynamic> json) {
    return AuthUser(
      id: json['id'] ?? '',
      email: json['email'] ?? '',
      firstName: json['first_name'] ?? json['firstName'] ?? '',
      lastName: json['last_name'] ?? json['lastName'] ?? '',
      role: json['role'] ?? 'patient',
      imageUrl: json['image_url'] ?? json['imageUrl'],
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'email': email,
      'first_name': firstName,
      'last_name': lastName,
      'role': role,
      'image_url': imageUrl,
    };
  }
}

enum AuthStatus { loading, authenticated, unauthenticated }

class AuthProvider extends ChangeNotifier {
  final _storage = const FlutterSecureStorage();

  AuthStatus _status = AuthStatus.loading;
  AuthUser? _user;
  String? _token;
  String? _error;

  AuthStatus get status => _status;
  AuthUser? get user => _user;
  String? get token => _token;
  String? get error => _error;
  bool get isAuthenticated => _status == AuthStatus.authenticated;

  String get apiBase =>
      dotenv.env['API_BASE_URL'] ?? 'https://flossy-backend-422640267680.asia-south1.run.app';

  AuthProvider() {
    _loadStoredAuth();
  }

  Future<void> _loadStoredAuth() async {
    try {
      final token = await _storage.read(key: 'flossy_token');
      final userJson = await _storage.read(key: 'flossy_user');

      if (token != null && userJson != null) {
        _token = token;
        _user = AuthUser.fromJson(json.decode(userJson));
        _status = AuthStatus.authenticated;
      } else {
        _status = AuthStatus.unauthenticated;
      }
    } catch (e) {
      _status = AuthStatus.unauthenticated;
    }
    notifyListeners();
  }

  Future<bool> signIn(String email, String password) async {
    _error = null;
    notifyListeners();

    try {
      // Use Clerk's sign-in endpoint
      final clerkFrontendApi = dotenv.env['CLERK_FRONTEND_API'] ?? 'smileartistsdentalstudio.clerk.accounts.dev';
      
      // Step 1: Create sign-in attempt
      final createRes = await http.post(
        Uri.parse('https://$clerkFrontendApi/v1/client/sign_ins'),
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
        body: json.encode({
          'identifier': email,
        }),
      );

      if (createRes.statusCode != 200) {
        final errBody = json.decode(createRes.body);
        _error = errBody['errors']?[0]?['message'] ?? 'Sign in failed';
        notifyListeners();
        return false;
      }

      final createData = json.decode(createRes.body);
      final signInId = createData['response']?['id'];
      
      if (signInId == null) {
        _error = 'Failed to initialize sign in';
        notifyListeners();
        return false;
      }

      // Step 2: Attempt password
      final attemptRes = await http.post(
        Uri.parse('https://$clerkFrontendApi/v1/client/sign_ins/$signInId/attempt_first_factor'),
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
        body: json.encode({
          'strategy': 'password',
          'password': password,
        }),
      );

      if (attemptRes.statusCode != 200) {
        final errBody = json.decode(attemptRes.body);
        _error = errBody['errors']?[0]?['message'] ?? 'Invalid credentials';
        notifyListeners();
        return false;
      }

      final attemptData = json.decode(attemptRes.body);
      final session = attemptData['client']?['sessions']?[0];
      final sessionToken = session?['last_active_token']?['jwt'];

      if (sessionToken == null) {
        _error = 'Failed to get session token';
        notifyListeners();
        return false;
      }

      // Step 3: Post login to backend
      return await _postLogin(sessionToken, email);
    } catch (e) {
      _error = 'Connection error: $e';
      notifyListeners();
      return false;
    }
  }

  Future<bool> _postLogin(String sessionToken, String email) async {
    try {
      final res = await http.post(
        Uri.parse('$apiBase/api/auth/post_login'),
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer $sessionToken',
        },
        body: json.encode({
          'email_hint': email,
        }),
      );

      if (res.ok) {
        final data = json.decode(res.body);
        final userRole = data['user']?['role'] ?? 'patient';

        _token = sessionToken;
        _user = AuthUser(
          id: data['user']?['id'] ?? '',
          email: email,
          firstName: data['user']?['first_name'] ?? '',
          lastName: data['user']?['last_name'] ?? '',
          role: userRole,
        );

        await _storage.write(key: 'flossy_token', value: sessionToken);
        await _storage.write(
            key: 'flossy_user', value: json.encode(_user!.toJson()));

        _status = AuthStatus.authenticated;
        notifyListeners();
        return true;
      } else {
        _error = 'Backend authentication failed';
        notifyListeners();
        return false;
      }
    } catch (e) {
      _error = 'Network error: $e';
      notifyListeners();
      return false;
    }
  }

  Future<bool> signUp(String email, String password, String firstName, String lastName) async {
    _error = null;
    notifyListeners();

    try {
      final clerkFrontendApi = dotenv.env['CLERK_FRONTEND_API'] ?? 'smileartistsdentalstudio.clerk.accounts.dev';

      final res = await http.post(
        Uri.parse('https://$clerkFrontendApi/v1/client/sign_ups'),
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
        body: json.encode({
          'email_address': email,
          'password': password,
          'first_name': firstName,
          'last_name': lastName,
        }),
      );

      if (res.statusCode == 200 || res.statusCode == 201) {
        final data = json.decode(res.body);
        final session = data['client']?['sessions']?[0];
        final sessionToken = session?['last_active_token']?['jwt'];

        if (sessionToken != null) {
          return await _postLogin(sessionToken, email);
        }
      }

      final errBody = json.decode(res.body);
      _error = errBody['errors']?[0]?['message'] ?? 'Sign up failed';
      notifyListeners();
      return false;
    } catch (e) {
      _error = 'Connection error: $e';
      notifyListeners();
      return false;
    }
  }

  Future<void> signOut() async {
    await _storage.deleteAll();
    _user = null;
    _token = null;
    _status = AuthStatus.unauthenticated;
    notifyListeners();
  }

  void clearError() {
    _error = null;
    notifyListeners();
  }
}

extension on http.Response {
  bool get ok => statusCode >= 200 && statusCode < 300;
}
