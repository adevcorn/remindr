// Data model for Capture

enum CaptureType { voice, text, image }

enum CaptureState {
  queued,
  processing,
  parsed,
  confirmed,
  syncing,
  synced,
  error,
  needsReview
}

class Capture {
  final int? id;
  final String userId;
  final CaptureType captureType;
  final CaptureState state;
  final String? rawText;
  final String? audioUrl;
  final String? imageUrl;
  final String? audioData;  // Base64 encoded audio for upload
  final String? imageData;  // Base64 encoded image for upload
  final double? aiConfidence;
  final String? errorMessage;
  final int retryCount;
  final DateTime createdAt;
  final DateTime? updatedAt;
  final DateTime? processedAt;

  Capture({
    this.id,
    required this.userId,
    required this.captureType,
    required this.state,
    this.rawText,
    this.audioUrl,
    this.imageUrl,
    this.audioData,
    this.imageData,
    this.aiConfidence,
    this.errorMessage,
    this.retryCount = 0,
    required this.createdAt,
    this.updatedAt,
    this.processedAt,
  });

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'user_id': userId,
      'capture_type': captureType.name,
      'state': state.name,
      'raw_text': rawText,
      'audio_url': audioUrl,
      'image_url': imageUrl,
      'audio_data': audioData,
      'image_data': imageData,
      'ai_confidence': aiConfidence,
      'error_message': errorMessage,
      'retry_count': retryCount,
      'created_at': createdAt.toIso8601String(),
      'updated_at': updatedAt?.toIso8601String(),
      'processed_at': processedAt?.toIso8601String(),
    };
  }

  factory Capture.fromJson(Map<String, dynamic> json) {
    return Capture(
      id: json['id'],
      userId: json['user_id'],
      captureType: CaptureType.values.firstWhere(
        (e) => e.name == json['capture_type'],
      ),
      state: CaptureState.values.firstWhere(
        (e) => e.name == json['state'],
      ),
      rawText: json['raw_text'],
      audioUrl: json['audio_url'],
      imageUrl: json['image_url'],
      audioData: json['audio_data'],
      imageData: json['image_data'],
      aiConfidence: json['ai_confidence']?.toDouble(),
      errorMessage: json['error_message'],
      retryCount: json['retry_count'] ?? 0,
      createdAt: DateTime.parse(json['created_at']),
      updatedAt: json['updated_at'] != null
          ? DateTime.parse(json['updated_at'])
          : null,
      processedAt: json['processed_at'] != null
          ? DateTime.parse(json['processed_at'])
          : null,
    );
  }

  Map<String, dynamic> toSqlite() {
    return {
      'id': id,
      'user_id': userId,
      'capture_type': captureType.name,
      'state': state.name,
      'raw_text': rawText,
      'audio_url': audioUrl,
      'image_url': imageUrl,
      'ai_confidence': aiConfidence,
      'error_message': errorMessage,
      'retry_count': retryCount,
      'created_at': createdAt.toIso8601String(),
      'updated_at': updatedAt?.toIso8601String(),
      'processed_at': processedAt?.toIso8601String(),
    };
  }

  factory Capture.fromSqlite(Map<String, dynamic> map) {
    return Capture.fromJson(map);
  }
}
