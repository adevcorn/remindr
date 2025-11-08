"""Home screen with capture inputs."""
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
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

  @override
  void dispose() {
    _textController.dispose();
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
                  onPressed: () {
                    // TODO: Voice capture
                    ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(content: Text('Voice capture coming soon')),
                    );
                  },
                  icon: const Icon(Icons.mic),
                  label: const Text('Voice'),
                ),
                ElevatedButton.icon(
                  onPressed: () {
                    // TODO: Image capture
                    ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(content: Text('Image capture coming soon')),
                    );
                  },
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
