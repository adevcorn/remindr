// Data model for Draft

enum DraftType { task, event, note }

class Draft {
  final int? id;
  final int captureId;
  final String userId;
  final DraftType draftType;
  final double aiConfidence;
  final String title;
  final String? description;
  final DateTime? dueDate;
  final String? priority;
  final String? location;
  final DateTime? startTime;
  final DateTime? endTime;
  final bool isConfirmed;
  final String? googleTaskId;
  final String? googleEventId;
  final String syncState;
  final Map<String, dynamic>? extractedEntities;
  final DateTime createdAt;
  final DateTime? updatedAt;
  final DateTime? syncedAt;

  Draft({
    this.id,
    required this.captureId,
    required this.userId,
    required this.draftType,
    required this.aiConfidence,
    required this.title,
    this.description,
    this.dueDate,
    this.priority,
    this.location,
    this.startTime,
    this.endTime,
    this.isConfirmed = false,
    this.googleTaskId,
    this.googleEventId,
    this.syncState = 'parsed',
    this.extractedEntities,
    required this.createdAt,
    this.updatedAt,
    this.syncedAt,
  });

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'capture_id': captureId,
      'user_id': userId,
      'draft_type': draftType.name,
      'ai_confidence': aiConfidence,
      'title': title,
      'description': description,
      'due_date': dueDate?.toIso8601String(),
      'priority': priority,
      'location': location,
      'start_time': startTime?.toIso8601String(),
      'end_time': endTime?.toIso8601String(),
      'is_confirmed': isConfirmed,
      'google_task_id': googleTaskId,
      'google_event_id': googleEventId,
      'sync_state': syncState,
      'extracted_entities': extractedEntities,
      'created_at': createdAt.toIso8601String(),
      'updated_at': updatedAt?.toIso8601String(),
      'synced_at': syncedAt?.toIso8601String(),
    };
  }

  factory Draft.fromJson(Map<String, dynamic> json) {
    return Draft(
      id: json['id'],
      captureId: json['capture_id'],
      userId: json['user_id'],
      draftType: DraftType.values.firstWhere(
        (e) => e.name == json['draft_type'],
      ),
      aiConfidence: json['ai_confidence'].toDouble(),
      title: json['title'],
      description: json['description'],
      dueDate: json['due_date'] != null
          ? DateTime.parse(json['due_date'])
          : null,
      priority: json['priority'],
      location: json['location'],
      startTime: json['start_time'] != null
          ? DateTime.parse(json['start_time'])
          : null,
      endTime: json['end_time'] != null
          ? DateTime.parse(json['end_time'])
          : null,
      isConfirmed: json['is_confirmed'] ?? false,
      googleTaskId: json['google_task_id'],
      googleEventId: json['google_event_id'],
      syncState: json['sync_state'] ?? 'parsed',
      extractedEntities: json['extracted_entities'],
      createdAt: DateTime.parse(json['created_at']),
      updatedAt: json['updated_at'] != null
          ? DateTime.parse(json['updated_at'])
          : null,
      syncedAt: json['synced_at'] != null
          ? DateTime.parse(json['synced_at'])
          : null,
    );
  }

  Draft copyWith({
    int? id,
    int? captureId,
    String? userId,
    DraftType? draftType,
    double? aiConfidence,
    String? title,
    String? description,
    DateTime? dueDate,
    String? priority,
    String? location,
    DateTime? startTime,
    DateTime? endTime,
    bool? isConfirmed,
    String? googleTaskId,
    String? googleEventId,
    String? syncState,
    Map<String, dynamic>? extractedEntities,
    DateTime? createdAt,
    DateTime? updatedAt,
    DateTime? syncedAt,
  }) {
    return Draft(
      id: id ?? this.id,
      captureId: captureId ?? this.captureId,
      userId: userId ?? this.userId,
      draftType: draftType ?? this.draftType,
      aiConfidence: aiConfidence ?? this.aiConfidence,
      title: title ?? this.title,
      description: description ?? this.description,
      dueDate: dueDate ?? this.dueDate,
      priority: priority ?? this.priority,
      location: location ?? this.location,
      startTime: startTime ?? this.startTime,
      endTime: endTime ?? this.endTime,
      isConfirmed: isConfirmed ?? this.isConfirmed,
      googleTaskId: googleTaskId ?? this.googleTaskId,
      googleEventId: googleEventId ?? this.googleEventId,
      syncState: syncState ?? this.syncState,
      extractedEntities: extractedEntities ?? this.extractedEntities,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
      syncedAt: syncedAt ?? this.syncedAt,
    );
  }
}
