import 'package:flutter_test/flutter_test.dart';
import 'package:mockito/mockito.dart';
import 'package:mockito/annotations.dart';
import 'package:http/http.dart' as http;
import 'package:google_sign_in/google_sign_in.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'dart:convert';

import 'package:remindr/services/auth_service.dart';

// Generate mocks with: flutter pub run build_runner build
@GenerateMocks([
  http.Client,
  GoogleSignIn,
  GoogleSignInAccount,
  GoogleSignInAuthentication,
  FlutterSecureStorage,
])
import 'auth_service_test.mocks.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  group('AuthService Google Sign-In', () {
    late AuthService authService;
    late MockGoogleSignIn mockGoogleSignIn;
    late MockGoogleSignInAccount mockGoogleAccount;
    late MockGoogleSignInAuthentication mockGoogleAuth;
    late MockFlutterSecureStorage mockSecureStorage;
    late MockClient mockClient;

    setUp(() {
      mockGoogleSignIn = MockGoogleSignIn();
      mockGoogleAccount = MockGoogleSignInAccount();
      mockGoogleAuth = MockGoogleSignInAuthentication();
      mockSecureStorage = MockFlutterSecureStorage();
      mockClient = MockClient();
      
      authService = AuthService(
        baseUrl: 'http://localhost:8000/api/v1',
        secureStorage: mockSecureStorage,
        googleSignIn: mockGoogleSignIn,
        client: mockClient,
      );
    });

    test('signInWithGoogle success - creates session with ID token', () async {
      // Mock Google Sign-In flow
      when(mockGoogleSignIn.signIn())
          .thenAnswer((_) async => mockGoogleAccount);
      when(mockGoogleAccount.authentication)
          .thenAnswer((_) async => mockGoogleAuth);
      when(mockGoogleAuth.idToken)
          .thenReturn('mock_id_token_123');
      
      // Mock backend response
      when(mockClient.post(
        Uri.parse('http://localhost:8000/api/v1/auth/google-token'),
        headers: anyNamed('headers'),
        body: anyNamed('body'),
      )).thenAnswer((_) async => http.Response(
        jsonEncode({
          'session_token': 'session_abc123',
          'user_id': 'user_123',
          'email': 'test@example.com',
          'name': 'Test User',
        }),
        200,
      ));

      // Mock secure storage
      when(mockSecureStorage.write(
        key: anyNamed('key'),
        value: anyNamed('value'),
      )).thenAnswer((_) async => null);

      final result = await authService.signInWithGoogle();

      expect(result, true);
      expect(authService.isAuthenticated, true);
      expect(authService.sessionToken, 'session_abc123');
      expect(authService.email, 'test@example.com');
      
      // Verify secure storage was called
      verify(mockSecureStorage.write(
        key: 'session_token',
        value: 'session_abc123',
      )).called(1);
    });

    test('signInWithGoogle fails - user cancels', () async {
      when(mockGoogleSignIn.signIn())
          .thenAnswer((_) async => null);
      // Stub backend call to avoid hanging
      when(mockClient.post(
        any,
        headers: anyNamed('headers'),
        body: anyNamed('body'),
      )).thenAnswer((_) async => http.Response('User cancelled', 400));

      final result = await authService.signInWithGoogle();

      expect(result, false);
      expect(authService.isAuthenticated, false);
    });

    test('signInWithGoogle fails - no ID token', () async {
      when(mockGoogleSignIn.signIn())
          .thenAnswer((_) async => mockGoogleAccount);
      when(mockGoogleAccount.authentication)
          .thenAnswer((_) async => mockGoogleAuth);
      when(mockGoogleAuth.idToken)
          .thenReturn(null);

      final result = await authService.signInWithGoogle();

      expect(result, false);
    });

    test('signInWithGoogle fails - backend error', () async {
      when(mockGoogleSignIn.signIn())
          .thenAnswer((_) async => mockGoogleAccount);
      when(mockGoogleAccount.authentication)
          .thenAnswer((_) async => mockGoogleAuth);
      when(mockGoogleAuth.idToken)
          .thenReturn('mock_id_token');
      
      when(mockClient.post(
        any,
        headers: anyNamed('headers'),
        body: anyNamed('body'),
      )).thenAnswer((_) async => http.Response(
        'Authentication failed',
        401,
      ));

      final result = await authService.signInWithGoogle();

      expect(result, false);
    });
  });

  group('AuthService Session Management', () {
    late AuthService authService;
    late MockFlutterSecureStorage mockSecureStorage;
    late MockClient mockClient;
    late MockGoogleSignIn mockGoogleSignIn;

    setUp(() {
      mockSecureStorage = MockFlutterSecureStorage();
      mockClient = MockClient();
      mockGoogleSignIn = MockGoogleSignIn();
      authService = AuthService(
        baseUrl: 'http://localhost:8000/api/v1',
        secureStorage: mockSecureStorage,
        client: mockClient,
        googleSignIn: mockGoogleSignIn,
      );
    });

    test('clearSession - removes all stored data', () async {
      when(mockSecureStorage.delete(key: anyNamed('key')))
          .thenAnswer((_) async => null);

      await authService.clearSession();

      verify(mockSecureStorage.delete(key: 'session_token')).called(1);
      verify(mockSecureStorage.delete(key: 'user_id')).called(1);
      verify(mockSecureStorage.delete(key: 'email')).called(1);
      verify(mockSecureStorage.delete(key: 'name')).called(1);
      
      expect(authService.isAuthenticated, false);
    });

    test('signOut - calls backend and clears local session', () async {
      // Set up authenticated state
      authService.setAuthToken('test_token');
      
      when(mockClient.post(
        Uri.parse('http://localhost:8000/api/v1/auth/logout'),
        headers: anyNamed('headers'),
      )).thenAnswer((_) async => http.Response('{"message": "Logged out"}', 200));
      
      when(mockSecureStorage.delete(key: anyNamed('key')))
          .thenAnswer((_) async => null);

      when(mockGoogleSignIn.signOut()).thenAnswer((_) async => null);

      await authService.signOut();

      verify(mockClient.post(
        Uri.parse('http://localhost:8000/api/v1/auth/logout'),
        headers: anyNamed('headers'),
      )).called(1);
      verify(mockGoogleSignIn.signOut()).called(1);
      
      expect(authService.isAuthenticated, false);
    });
  });

  group('AuthService Token Expiry', () {
    late AuthService authService;
    late MockClient mockClient;
    late MockFlutterSecureStorage mockSecureStorage;

    setUp(() {
      mockClient = MockClient();
      mockSecureStorage = MockFlutterSecureStorage();
      authService = AuthService(
        baseUrl: 'http://localhost:8000/api/v1',
        client: mockClient,
        secureStorage: mockSecureStorage,
      );
    });

    test('checkSessionValid - returns true for valid token', () async {
      authService.setAuthToken('test_token');
      when(mockClient.get(
        Uri.parse('http://localhost:8000/api/v1/auth/me'),
        headers: anyNamed('headers'),
      )).thenAnswer((_) async => http.Response('{"email": "test@example.com"}', 200));

      final result = await authService.checkSessionValid();

      expect(result, true);
    });

    test('checkSessionValid - returns false for expired token', () async {
      when(mockClient.get(
        Uri.parse('http://localhost:8000/api/v1/auth/me'),
        headers: anyNamed('headers'),
      )).thenAnswer((_) async => http.Response('Unauthorized', 401));

      final result = await authService.checkSessionValid();

      expect(result, false);
    });

    test('handleUnauthorized - clears session', () async {
      when(mockSecureStorage.delete(key: anyNamed('key')))
          .thenAnswer((_) async => null);

      await authService.handleUnauthorized();

      expect(authService.isAuthenticated, false);
    });
  });

  group('AuthService 401 Handling', () {
    late AuthService authService;
    late MockFlutterSecureStorage mockSecureStorage;
    late MockClient mockClient;

    setUp(() {
      mockSecureStorage = MockFlutterSecureStorage();
      mockClient = MockClient();
      authService = AuthService(
        baseUrl: 'http://localhost:8000/api/v1',
        secureStorage: mockSecureStorage,
        client: mockClient,
      );
    });

    test('handleUnauthorized clears session data', () async {
      when(mockSecureStorage.delete(key: anyNamed('key')))
          .thenAnswer((_) async => null);

      await authService.handleUnauthorized();

      verify(mockSecureStorage.delete(key: 'session_token')).called(1);
      verify(mockSecureStorage.delete(key: 'user_id')).called(1);
      expect(authService.isAuthenticated, false);
    });
  });
}
