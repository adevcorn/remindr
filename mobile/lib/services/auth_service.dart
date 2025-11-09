// Authentication service for Google OAuth and session management.
import 'dart:convert';
import 'package:google_sign_in/google_sign_in.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:http/http.dart' as http;

class AuthService {
  /// Set the session token (used for testing)
  void setAuthToken(String token) {
    _sessionToken = token;
  }
   final String baseUrl;
   final FlutterSecureStorage _secureStorage;
   final GoogleSignIn _googleSignIn;
   final http.Client _client;


   AuthService({
     this.baseUrl = 'http://localhost:8000/api/v1',
     FlutterSecureStorage? secureStorage,
     GoogleSignIn? googleSignIn,
     http.Client? client,
   })  : _secureStorage = secureStorage ?? const FlutterSecureStorage(),
         _googleSignIn = googleSignIn ?? GoogleSignIn(
           scopes: [
             'email',
             'profile',
             'https://www.googleapis.com/auth/tasks',
             'https://www.googleapis.com/auth/calendar',
           ],
         ),
         _client = client ?? http.Client();

  String? _sessionToken;
  String? _userId;
  String? _email;
  String? _name;


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
  /// 
  /// This implements a mobile-friendly OAuth flow:
  /// 1. Google Sign-In SDK handles authentication client-side
  /// 2. We extract the ID token from the authentication result
  /// 3. We send the ID token to our backend for verification
  /// 4. Backend verifies the token with Google and returns a session token
  /// 5. We store the session token for future API calls
  /// 
  /// Session tokens expire after 30 days. When expired, users must sign in again.
  Future<bool> signInWithGoogle() async {
    try {
      // Sign in with Google using the SDK
      final GoogleSignInAccount? googleUser = await _googleSignIn.signIn();
      if (googleUser == null) {
        return false; // User canceled
      }

      // Get authentication details including ID token
      final GoogleSignInAuthentication googleAuth = await googleUser.authentication;
      
      // Extract ID token
      final idToken = googleAuth.idToken;
      if (idToken == null) {
        throw Exception('No ID token received from Google');
      }

      // Send ID token to backend for verification
       final response = await _client.post(
         Uri.parse('$baseUrl/auth/google-token'),
         headers: {
           'Content-Type': 'application/json',
         },
         body: jsonEncode({
           'id_token': idToken,
         }),
       );

      if (response.statusCode == 200) {
        final authData = jsonDecode(response.body);
        
        // Store session data securely
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
        throw Exception('Backend authentication failed: ${response.body}');
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
         await _client.post(
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

  /// Verify token is still valid by calling /me endpoint
  /// If token is expired (401), clear session gracefully
  Future<bool> _verifyToken() async {
    if (_sessionToken == null) return false;

    try {
       final response = await _client.get(
         Uri.parse('$baseUrl/auth/me'),
         headers: {
           'Content-Type': 'application/json',
           'Authorization': 'Bearer $_sessionToken',
         },
       );

      if (response.statusCode == 200) {
        return true;
      } else if (response.statusCode == 401) {
        // Token expired or invalid - clear session gracefully
        // This is expected behavior after 30 days
        return false;
      } else {
        // Other error - assume invalid
        return false;
      }
    } catch (e) {
      // Network error or other exception - assume invalid
      return false;
    }
  }

  /// Handle 401 errors by clearing session and providing user feedback
  /// Call this when API requests return 401 status
  Future<void> handleUnauthorized() async {
    await clearSession();
    // Note: The calling code should show a message to the user:
    // "Your session has expired. Please sign in again."
  }

  /// Check if the current session is still valid
  /// Returns true if valid, false if expired or invalid
  /// If false, caller should prompt user to sign in again
  Future<bool> checkSessionValid() async {
    return await _verifyToken();
  }
}
