// Main Flutter application
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'services/local_database.dart';
import 'services/api_service.dart';
import 'services/sync_service.dart';
import 'services/auth_service.dart';
import 'screens/home_screen.dart';
import 'screens/login_screen.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  
  // Initialize services
  final localDb = LocalDatabase.instance;
  final authService = AuthService();
  final apiService = ApiService();
  final syncService = SyncService(localDb, apiService);
  
  // Initialize auth and restore session
  await authService.initialize();
  
  // Set auth token in API service if available
  if (authService.sessionToken != null) {
    apiService.setAuthToken(authService.sessionToken!);
  }
  
  // Set up unauthorized callback to handle token expiry
  apiService.onUnauthorized = () {
    authService.handleUnauthorized();
  };
  
  // Start automatic sync if authenticated
  if (authService.isAuthenticated) {
    syncService.startAutoSync();
  }
  
  runApp(
    MultiProvider(
      providers: [
        Provider<LocalDatabase>.value(value: localDb),
        Provider<AuthService>.value(value: authService),
        Provider<ApiService>.value(value: apiService),
        Provider<SyncService>.value(value: syncService),
      ],
      child: const RemindrApp(),
    ),
  );
}

class RemindrApp extends StatelessWidget {
  const RemindrApp({super.key});

  @override
  Widget build(BuildContext context) {
    final authService = Provider.of<AuthService>(context, listen: false);
    
    return MaterialApp(
      title: 'Remindr',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.deepPurple),
        useMaterial3: true,
        fontFamily: 'SF Pro',
      ),
      home: authService.isAuthenticated
          ? const HomeScreen()
          : LoginScreen(authService: authService),
    );
  }
}
