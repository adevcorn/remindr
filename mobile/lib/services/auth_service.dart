"""Authentication service for Google OAuth and session management."""
import 'dart:convert';
import 'package:google_sign_in/google_sign_in.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:http/http.dart' as http;

class AuthService {
  final String baseUrl;
  final FlutterSecureStorage _secureStorage = const FlutterSecureStorage();
  final GoogleSignIn _googleSignIn = GoogleSignIn(
    scopes: [
      'email',
      'profile',
      'https://www.googleapis.com/auth/tasks',
      'https://www.googleapis.com/auth/calendar',
    ],
  );

  String? _sessionToken;
  String? _userId;
  String? _email;
  String? _name;

  AuthService({this.baseUrl = 'http://localhost:8000/api/v1'});

  // Getters
  String? get sessionToken => _sessionToken;
  String? get userId => _userId;
  String? get email => _email;
  String? get name => _name;
  bool get isAuthenticated => _sessionToken != null && _userId != null;

  /// Initialize auth service and restore session if available
  Future<bool> initialize() async {
    try {
      _sessionToken = await _secureStorage.read(key: 'session_token');
      _userId = await _secureStorage.read(key: 'user_id');
      _email = await _secureStorage.read(key: 'email');
      _name = await _secureStorage.read(key: 'name');

      if (_sessionToken != null) {
        // Verify token is still valid
        final isValid = await _verifyToken();
        if (!isValid) {
          await clearSession();
          return false;
        }
        return true;
      }
      return false;
    } catch (e) {
      return false;
    }
  }

  /// Sign in with Google OAuth
  Future<bool> signInWithGoogle() async {
    try {
      // Sign in with Google
      final GoogleSignInAccount? googleUser = await _googleSignIn.signIn();
      if (googleUser == null) {
        return false; // User canceled
      }

      // Get auth code
      final GoogleSignInAuthentication googleAuth = await googleUser.authentication;
      
      // Get authorization URL from backend
      final loginResponse = await http.get(
        Uri.parse('$baseUrl/auth/login'),
      );

      if (loginResponse.statusCode != 200) {
        throw Exception('Failed to get authorization URL');
      }

      final loginData = jsonDecode(loginResponse.body);
      final state = loginData['state'];

      // Exchange code for session token via backend
      // Note: In production, this should use proper OAuth flow
      // For now, we'll use the serverAuthCode if available
      final serverAuthCode = googleAuth.serverAuthCode;
      if (serverAuthCode == null) {
        throw Exception('No server auth code received');
      }

      final callbackResponse = await http.get(
        Uri.parse('$baseUrl/auth/callback?code=$serverAuthCode&state=$state'),
      );

      if (callbackResponse.statusCode == 200) {
        final authData = jsonDecode(callbackResponse.body);
        
        // Store session data
        _sessionToken = authData['session_token'];
        _userId = authData['user_id'];
        _email = authData['email'];
        _name = authData['name'];

        await _secureStorage.write(key: 'session_token', value: _sessionToken);
        await _secureStorage.write(key: 'user_id', value: _userId);
        await _secureStorage.write(key: 'email', value: _email);
        if (_name != null) {
          await _secureStorage.write(key: 'name', value: _name);
        }

        return true;
      } else {
        throw Exception('OAuth callback failed: ${callbackResponse.body}');
      }
    } catch (e) {
      print('Sign in error: $e');
      return false;
    }
  }

  /// Sign out and clear session
  Future<void> signOut() async {
    try {
      // Call backend logout endpoint
      if (_sessionToken != null) {
        await http.post(
          Uri.parse('$baseUrl/auth/logout'),
          headers: {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer $_sessionToken',
          },
        );
      }

      // Sign out from Google
      await _googleSignIn.signOut();
    } catch (e) {
      print('Sign out error: $e');
    } finally {
      // Clear local session regardless of backend response
      await clearSession();
    }
  }

  /// Clear local session data
  Future<void> clearSession() async {
    _sessionToken = null;
    _userId = null;
    _email = null;
    _name = null;

    await _secureStorage.delete(key: 'session_token');
    await _secureStorage.delete(key: 'user_id');
    await _secureStorage.delete(key: 'email');
    await _secureStorage.delete(key: 'name');
  }

  /// Verify token is still valid
  Future<bool> _verifyToken() async {
    if (_sessionToken == null) return false;

    try {
      final response = await http.get(
        Uri.parse('$baseUrl/auth/me'),
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer $_sessionToken',
        },
      );

      return response.statusCode == 200;
    } catch (e) {
      return false;
    }
  }

  /// Handle 401 errors by clearing session
  Future<void> handleUnauthorized() async {
    await clearSession();
  }
}
