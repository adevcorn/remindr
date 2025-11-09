"""API service for communicating with backend - thread-safe for parallel operations."""
import 'dart:convert';
import 'package:http/http.dart' as http;
import '../models/capture.dart';
import '../models/draft.dart';

class ApiService {
  final String baseUrl;
  String? _authToken;
  Function()? onUnauthorized;
  
  // HTTP client reuse for connection pooling and better performance
  final http.Client _client = http.Client();

  ApiService({this.baseUrl = 'http://localhost:8000/api/v1'});

  void setAuthToken(String token) {
    _authToken = token;
  }

  void clearAuthToken() {
    _authToken = null;
  }

  Map<String, String> get _headers => {
        'Content-Type': 'application/json',
        if (_authToken != null) 'Authorization': 'Bearer $_authToken',
      };

  void _handleUnauthorized() {
    clearAuthToken();
    onUnauthorized?.call();
  }

  // Generic GET request - thread-safe
  Future<Map<String, dynamic>> get(String path) async {
    final response = await _client.get(
      Uri.parse('$baseUrl$path'),
      headers: _headers,
    );

    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    } else if (response.statusCode == 401) {
      _handleUnauthorized();
      throw Exception('Authentication required');
    } else {
      throw Exception('Request failed: ${response.body}');
    }
  }

  // Capture endpoints - thread-safe for parallel calls
  Future<Capture> createCapture(Capture capture) async {
    final response = await _client.post(
      Uri.parse('$baseUrl/captures/captures'),
      headers: _headers,
      body: jsonEncode(capture.toJson()),
    );

    if (response.statusCode == 201) {
      return Capture.fromJson(jsonDecode(response.body));
    } else if (response.statusCode == 401) {
      _handleUnauthorized();
      throw Exception('Authentication required');
    } else {
      throw Exception('Failed to create capture: ${response.body}');
    }
  }

  Future<List<Capture>> getCaptures({int skip = 0, int limit = 100}) async {
    final response = await _client.get(
      Uri.parse('$baseUrl/captures/captures?skip=$skip&limit=$limit'),
      headers: _headers,
    );

    if (response.statusCode == 200) {
      final List<dynamic> data = jsonDecode(response.body);
      return data.map((json) => Capture.fromJson(json)).toList();
    } else if (response.statusCode == 401) {
      _handleUnauthorized();
      throw Exception('Authentication required');
    } else {
      throw Exception('Failed to load captures');
    }
  }

  Future<Capture> getCapture(int captureId) async {
    final response = await _client.get(
      Uri.parse('$baseUrl/captures/captures/$captureId'),
      headers: _headers,
    );

    if (response.statusCode == 200) {
      return Capture.fromJson(jsonDecode(response.body));
    } else if (response.statusCode == 401) {
      _handleUnauthorized();
      throw Exception('Authentication required');
    } else {
      throw Exception('Failed to load capture');
    }
  }

  // Draft endpoints - thread-safe for parallel calls
  Future<List<Draft>> getDrafts({
    int skip = 0,
    int limit = 100,
    bool? needsReviewOnly,
  }) async {
    var url = '$baseUrl/captures/drafts?skip=$skip&limit=$limit';
    if (needsReviewOnly != null) {
      url += '&needs_review_only=$needsReviewOnly';
    }

    final response = await _client.get(
      Uri.parse(url),
      headers: _headers,
    );

    if (response.statusCode == 200) {
      final List<dynamic> data = jsonDecode(response.body);
      return data.map((json) => Draft.fromJson(json)).toList();
    } else if (response.statusCode == 401) {
      _handleUnauthorized();
      throw Exception('Authentication required');
    } else {
      throw Exception('Failed to load drafts');
    }
  }

  Future<Draft> confirmDraft({
    required int draftId,
    String? title,
    String? description,
    DateTime? dueDate,
    String? priority,
  }) async {
    final body = {
      'draft_id': draftId,
      if (title != null) 'title': title,
      if (description != null) 'description': description,
      if (dueDate != null) 'due_date': dueDate.toIso8601String(),
      if (priority != null) 'priority': priority,
    };

    final response = await _client.post(
      Uri.parse('$baseUrl/captures/drafts/$draftId/confirm'),
      headers: _headers,
      body: jsonEncode(body),
    );

    if (response.statusCode == 200) {
      return Draft.fromJson(jsonDecode(response.body));
    } else if (response.statusCode == 401) {
      _handleUnauthorized();
      throw Exception('Authentication required');
    } else {
      throw Exception('Failed to confirm draft');
    }
  }

  // Health check - thread-safe
  Future<bool> checkHealth() async {
    try {
      final response = await _client.get(
        Uri.parse('${baseUrl.replaceAll('/api/v1', '')}/health'),
        headers: _headers,
      ).timeout(const Duration(seconds: 5));
      return response.statusCode == 200;
    } catch (e) {
      return false;
    }
  }

  /// Dispose HTTP client when service is no longer needed
  void dispose() {
    _client.close();
  }
}
