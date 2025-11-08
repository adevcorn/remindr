"""Home screen with capture inputs."""
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:record/record.dart';
import 'package:image_picker/image_picker.dart';
import 'package:permission_handler/permission_handler.dart';
import 'dart:convert';
import 'dart:io';
import '../services/local_database.dart';
import '../services/api_service.dart';
import '../services/auth_service.dart';
import '../services/oauth_service.dart';
import '../models/capture.dart';
import 'login_screen.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  final TextEditingController _textController = TextEditingController();
  final AudioRecorder _audioRecorder = AudioRecorder();
  final ImagePicker _imagePicker = ImagePicker();
  
  bool _isRecording = false;
  String? _recordingPath;
  bool _isGoogleConnected = false;
  bool _isCheckingConnection = true;
  OAuthService? _oAuthService;

  @override
  void initState() {
    super.initState();
    _initializeOAuthService();
    _checkGoogleConnection();
  }

  void _initializeOAuthService() {
    final apiService = Provider.of<ApiService>(context, listen: false);
    _oAuthService = OAuthService(apiService);
  }

  Future<void> _checkGoogleConnection() async {
    if (_oAuthService == null) return;
    
    try {
      final connected = await _oAuthService!.checkConnectionStatus();
      if (mounted) {
        setState(() {
          _isGoogleConnected = connected;
          _isCheckingConnection = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _isCheckingConnection = false;
        });
      }
    }
  }

  Future<void> _connectGoogleServices() async {
    if (_oAuthService == null) return;

    try {
      final success = await _oAuthService!.connectGoogleServices(context);
      
      if (mounted) {
        setState(() {
          _isGoogleConnected = success;
        });

        if (success) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text('Google Calendar & Tasks connected!'),
              backgroundColor: Colors.green,
            ),
          );
        }
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to connect: $e')),
        );
      }
    }
  }

  @override
  void dispose() {
    _textController.dispose();
    _audioRecorder.dispose();
    _oAuthService?.dispose();
    super.dispose();
  }

  Future<void> _captureText() async {
    if (_textController.text.isEmpty) return;

    final localDb = Provider.of<LocalDatabase>(context, listen: false);
    final apiService = Provider.of<ApiService>(context, listen: false);
    final authService = Provider.of<AuthService>(context, listen: false);

    if (!authService.isAuthenticated) {
      _showLoginRequired();
      return;
    }

    final capture = Capture(
      userId: authService.userId!,
      captureType: CaptureType.text,
      state: CaptureState.queued,
      rawText: _textController.text,
      createdAt: DateTime.now(),
    );

    try {
      // Save locally first
      await localDb.insertCapture(capture);

      // Try to sync immediately
      await apiService.createCapture(capture);

      _textController.clear();
      
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Capture created!')),
        );
      }
    } catch (e) {
      if (mounted) {
        if (e.toString().contains('Authentication required')) {
          _showLoginRequired();
        } else {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('Saved offline: $e')),
          );
        }
      }
    }
  }

  Future<void> _captureVoice() async {
    if (_isRecording) {
      // Stop recording
      await _stopRecording();
    } else {
      // Start recording
      await _startRecording();
    }
  }

  Future<void> _startRecording() async {
    // Request microphone permission
    final status = await Permission.microphone.request();
    
    if (!status.isGranted) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Microphone permission denied')),
        );
      }
      return;
    }

    try {
      // Check if recording is supported
      if (await _audioRecorder.hasPermission()) {
        // Get temporary directory
        final tempDir = Directory.systemTemp;
        final timestamp = DateTime.now().millisecondsSinceEpoch;
        _recordingPath = '${tempDir.path}/recording_$timestamp.m4a';

        // Start recording
        await _audioRecorder.start(
          const RecordConfig(
            encoder: AudioEncoder.aacLc,
            bitRate: 128000,
            sampleRate: 16000,
          ),
          path: _recordingPath!,
        );

        setState(() {
          _isRecording = true;
        });

        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text('Recording... Tap again to stop'),
              duration: Duration(seconds: 2),
            ),
          );
        }
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to start recording: $e')),
        );
      }
    }
  }

  Future<void> _stopRecording() async {
    try {
      final path = await _audioRecorder.stop();
      
      setState(() {
        _isRecording = false;
      });

      if (path != null) {
        final authService = Provider.of<AuthService>(context, listen: false);

        if (!authService.isAuthenticated) {
          _showLoginRequired();
          return;
        }

        // Read audio file and convert to base64
        final file = File(path);
        final bytes = await file.readAsBytes();
        final base64Audio = base64Encode(bytes);

        final localDb = Provider.of<LocalDatabase>(context, listen: false);
        final apiService = Provider.of<ApiService>(context, listen: false);

        final capture = Capture(
          userId: authService.userId!,
          captureType: CaptureType.voice,
          state: CaptureState.queued,
          audioData: base64Audio,
          createdAt: DateTime.now(),
        );

        try {
          // Save locally first
          await localDb.insertCapture(capture);

          // Try to sync immediately
          await apiService.createCapture(capture);

          // Clean up temp file
          await file.delete();

          if (mounted) {
            ScaffoldMessenger.of(context).showSnackBar(
              const SnackBar(content: Text('Voice capture created!')),
            );
          }
        } catch (e) {
          if (mounted) {
            if (e.toString().contains('Authentication required')) {
              _showLoginRequired();
            } else {
              ScaffoldMessenger.of(context).showSnackBar(
                SnackBar(content: Text('Saved offline: $e')),
              );
            }
          }
        }
      }
    } catch (e) {
      setState(() {
        _isRecording = false;
      });
      
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to stop recording: $e')),
        );
      }
    }
  }

  Future<void> _captureImage() async {
    // Show options: Camera or Gallery
    final source = await showDialog<ImageSource>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Select Image Source'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            ListTile(
              leading: const Icon(Icons.camera_alt),
              title: const Text('Camera'),
              onTap: () => Navigator.pop(context, ImageSource.camera),
            ),
            ListTile(
              leading: const Icon(Icons.photo_library),
              title: const Text('Gallery'),
              onTap: () => Navigator.pop(context, ImageSource.gallery),
            ),
          ],
        ),
      ),
    );

    if (source == null) return;

    // Request camera permission if needed
    if (source == ImageSource.camera) {
      final status = await Permission.camera.request();
      if (!status.isGranted) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Camera permission denied')),
          );
        }
        return;
      }
    }

    try {
      // Pick image
      final XFile? image = await _imagePicker.pickImage(
        source: source,
        maxWidth: 1920,
        maxHeight: 1920,
        imageQuality: 85,
      );

      if (image != null) {
        final authService = Provider.of<AuthService>(context, listen: false);

        if (!authService.isAuthenticated) {
          _showLoginRequired();
          return;
        }

        // Read image file and convert to base64
        final bytes = await image.readAsBytes();
        final base64Image = base64Encode(bytes);

        final localDb = Provider.of<LocalDatabase>(context, listen: false);
        final apiService = Provider.of<ApiService>(context, listen: false);

        final capture = Capture(
          userId: authService.userId!,
          captureType: CaptureType.image,
          state: CaptureState.queued,
          imageData: base64Image,
          createdAt: DateTime.now(),
        );

        try {
          // Save locally first
          await localDb.insertCapture(capture);

          // Try to sync immediately
          await apiService.createCapture(capture);

          if (mounted) {
            ScaffoldMessenger.of(context).showSnackBar(
              const SnackBar(content: Text('Image capture created!')),
            );
          }
        } catch (e) {
          if (mounted) {
            if (e.toString().contains('Authentication required')) {
              _showLoginRequired();
            } else {
              ScaffoldMessenger.of(context).showSnackBar(
                SnackBar(content: Text('Saved offline: $e')),
              );
            }
          }
        }
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to capture image: $e')),
        );
      }
    }
  }

  void _showLoginRequired() {
    if (!mounted) return;

    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Please sign in to continue')),
    );

    // Navigate to login screen
    Navigator.of(context).pushReplacement(
      MaterialPageRoute(
        builder: (context) => LoginScreen(
          authService: Provider.of<AuthService>(context, listen: false),
        ),
      ),
    );
  }

  Future<void> _handleLogout() async {
    final authService = Provider.of<AuthService>(context, listen: false);
    final apiService = Provider.of<ApiService>(context, listen: false);

    try {
      await authService.signOut();
      apiService.clearAuthToken();

      if (mounted) {
        Navigator.of(context).pushReplacement(
          MaterialPageRoute(
            builder: (context) => LoginScreen(authService: authService),
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Logout failed: $e')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final authService = Provider.of<AuthService>(context, listen: false);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Remindr'),
        backgroundColor: Theme.of(context).colorScheme.inversePrimary,
        actions: [
          if (authService.isAuthenticated)
            PopupMenuButton<String>(
              onSelected: (value) {
                if (value == 'logout') {
                  _handleLogout();
                }
              },
              itemBuilder: (context) => [
                PopupMenuItem(
                  value: 'profile',
                  child: Text(authService.email ?? 'User'),
                  enabled: false,
                ),
                const PopupMenuItem(
                  value: 'logout',
                  child: Text('Logout'),
                ),
              ],
            ),
        ],
      ),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.start,
          children: [
            // Google Connection Banner
            if (!_isCheckingConnection && !_isGoogleConnected)
              Card(
                color: Colors.orange.shade50,
                child: Padding(
                  padding: const EdgeInsets.all(12.0),
                  child: Column(
                    children: [
                      Row(
                        children: [
                          Icon(Icons.info_outline, color: Colors.orange.shade700),
                          const SizedBox(width: 8),
                          Expanded(
                            child: Text(
                              'Connect Google Calendar & Tasks to sync your captures',
                              style: TextStyle(
                                color: Colors.orange.shade900,
                                fontWeight: FontWeight.w500,
                              ),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 8),
                      ElevatedButton.icon(
                        onPressed: _connectGoogleServices,
                        icon: const Icon(Icons.link),
                        label: const Text('Connect Google Services'),
                        style: ElevatedButton.styleFrom(
                          backgroundColor: Colors.orange,
                          foregroundColor: Colors.white,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            if (_isGoogleConnected)
              Card(
                color: Colors.green.shade50,
                child: Padding(
                  padding: const EdgeInsets.all(12.0),
                  child: Row(
                    children: [
                      Icon(Icons.check_circle, color: Colors.green.shade700),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          'Google Calendar & Tasks connected',
                          style: TextStyle(
                            color: Colors.green.shade900,
                            fontWeight: FontWeight.w500,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            const SizedBox(height: 20),
            const Text(
              'Quick Capture',
              style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 20),
            TextField(
              controller: _textController,
              decoration: const InputDecoration(
                hintText: 'Buy groceries tomorrow at 5pm',
                border: OutlineInputBorder(),
              ),
              onSubmitted: (_) => _captureText(),
            ),
            const SizedBox(height: 16),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceEvenly,
              children: [
                ElevatedButton.icon(
                  onPressed: _captureText,
                  icon: const Icon(Icons.text_fields),
                  label: const Text('Text'),
                ),
                ElevatedButton.icon(
                  onPressed: _captureVoice,
                  icon: Icon(_isRecording ? Icons.stop : Icons.mic),
                  label: Text(_isRecording ? 'Stop' : 'Voice'),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: _isRecording ? Colors.red : null,
                  ),
                ),
                ElevatedButton.icon(
                  onPressed: _captureImage,
                  icon: const Icon(Icons.camera_alt),
                  label: const Text('Image'),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
