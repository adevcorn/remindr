"""Main Flutter application."""
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'services/local_database.dart';
import 'services/api_service.dart';
import 'services/sync_service.dart';
import 'screens/home_screen.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  
  // Initialize services
  final localDb = LocalDatabase.instance;
  final apiService = ApiService();
  final syncService = SyncService(localDb, apiService);
  
  // Start automatic sync
  syncService.startAutoSync();
  
  runApp(
    MultiProvider(
      providers: [
        Provider<LocalDatabase>.value(value: localDb),
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
    return MaterialApp(
      title: 'Remindr',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.deepPurple),
        useMaterial3: true,
        fontFamily: 'SF Pro',
      ),
      home: const HomeScreen(),
    );
  }
}
