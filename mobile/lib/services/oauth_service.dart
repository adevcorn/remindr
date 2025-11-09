// OAuth service for Google services connection
import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:uni_links/uni_links.dart';
import 'dart:async';
import 'api_service.dart';

class OAuthService {
  final ApiService _apiService;
  StreamSubscription? _linkSubscription;

  OAuthService(this._apiService);

  /// Initiate OAuth flow to connect Google Tasks/Calendar
  Future<bool> connectGoogleServices(BuildContext context) async {
    try {
      // Get OAuth authorization URL from backend
      final response = await _apiService.get('/auth/connect-google');
      
      final authUrl = response['authorization_url'] as String;
      final state = response['state'] as String;

      // Launch OAuth URL in browser
      final uri = Uri.parse(authUrl);
      if (!await canLaunchUrl(uri)) {
        throw Exception('Could not launch OAuth URL');
      }

      await launchUrl(
        uri,
        mode: LaunchMode.externalApplication,
      );

      // Wait for callback (simplified for MVP - production should use deep links)
      // For now, user will need to manually return to app after OAuth
      if (context.mounted) {
        await _showOAuthCompletionDialog(context);
      }

      // Check connection status
      return await checkConnectionStatus();
    } catch (e) {
      debugPrint('OAuth flow error: $e');
      rethrow;
    }
  }

  /// Check if user has connected Google services
  Future<bool> checkConnectionStatus() async {
    try {
      final response = await _apiService.get('/auth/google-connection-status');
      return response['connected'] as bool? ?? false;
    } catch (e) {
      debugPrint('Error checking connection status: $e');
      return false;
    }
  }

  /// Get detailed connection status
  Future<Map<String, dynamic>> getConnectionStatus() async {
    try {
      return await _apiService.get('/auth/google-connection-status');
    } catch (e) {
      debugPrint('Error getting connection status: $e');
      return {
        'connected': false,
        'has_tasks_scope': false,
        'has_calendar_scope': false,
      };
    }
  }

  /// Show dialog prompting user to return after OAuth
  Future<void> _showOAuthCompletionDialog(BuildContext context) async {
    return showDialog<void>(
      context: context,
      barrierDismissible: false,
      builder: (BuildContext context) {
        return AlertDialog(
          title: const Text('Connect Google Services'),
          content: const SingleChildScrollView(
            child: ListBody(
              children: <Widget>[
                Text('You will be redirected to Google to grant permissions.'),
                SizedBox(height: 16),
                Text('After granting permissions, return to this app and tap "Done".'),
              ],
            ),
          ),
          actions: <Widget>[
            TextButton(
              child: const Text('Cancel'),
              onPressed: () {
                Navigator.of(context).pop();
              },
            ),
            TextButton(
              child: const Text('Done'),
              onPressed: () {
                Navigator.of(context).pop();
              },
            ),
          ],
        );
      },
    );
  }

  /// Dispose resources
  void dispose() {
    _linkSubscription?.cancel();
  }
}
