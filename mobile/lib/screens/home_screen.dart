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
import '../models/capture.dart';

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

  @override
  void dispose() {
    _textController.dispose();
    _audioRecorder.dispose();
    super.dispose();
  }

  Future<void> _captureText() async {
    if (_textController.text.isEmpty) return;

    final localDb = Provider.of<LocalDatabase>(context, listen: false);
    final apiService = Provider.of<ApiService>(context, listen: false);

    final capture = Capture(
      userId: 'demo_user',
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
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Saved offline: $e')),
        );
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
        // Read audio file and convert to base64
        final file = File(path);
        final bytes = await file.readAsBytes();
        final base64Audio = base64Encode(bytes);

        final localDb = Provider.of<LocalDatabase>(context, listen: false);
        final apiService = Provider.of<ApiService>(context, listen: false);

        final capture = Capture(
          userId: 'demo_user',
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
            ScaffoldMessenger.of(context).showSnackBar(
              SnackBar(content: Text('Saved offline: $e')),
            );
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
        // Read image file and convert to base64
        final bytes = await image.readAsBytes();
        final base64Image = base64Encode(bytes);

        final localDb = Provider.of<LocalDatabase>(context, listen: false);
        final apiService = Provider.of<ApiService>(context, listen: false);

        final capture = Capture(
          userId: 'demo_user',
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
            ScaffoldMessenger.of(context).showSnackBar(
              SnackBar(content: Text('Saved offline: $e')),
            );
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

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Remindr'),
        backgroundColor: Theme.of(context).colorScheme.inversePrimary,
      ),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.start,
          children: [
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
