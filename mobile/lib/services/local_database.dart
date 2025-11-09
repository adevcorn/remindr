"""Local SQLite database for offline queue with batch operations."""
import 'package:sqflite/sqflite.dart';
import 'package:path/path.dart';
import '../models/capture.dart';
import '../models/draft.dart';

class LocalDatabase {
  static final LocalDatabase instance = LocalDatabase._init();
  static Database? _database;

  LocalDatabase._init();

  Future<Database> get database async {
    if (_database != null) return _database!;
    _database = await _initDB('remindr.db');
    return _database!;
  }

  Future<Database> _initDB(String filePath) async {
    final dbPath = await getDatabasesPath();
    final path = join(dbPath, filePath);

    return await openDatabase(
      path,
      version: 1,
      onCreate: _createDB,
    );
  }

  Future _createDB(Database db, int version) async {
    const idType = 'INTEGER PRIMARY KEY AUTOINCREMENT';
    const textType = 'TEXT NOT NULL';
    const textTypeNullable = 'TEXT';
    const intType = 'INTEGER NOT NULL';
    const realType = 'REAL';

    // Captures table
    await db.execute('''
      CREATE TABLE captures (
        id $idType,
        user_id $textType,
        capture_type $textType,
        state $textType,
        raw_text $textTypeNullable,
        audio_url $textTypeNullable,
        image_url $textTypeNullable,
        ai_confidence $realType,
        error_message $textTypeNullable,
        retry_count $intType DEFAULT 0,
        created_at $textType,
        updated_at $textTypeNullable,
        processed_at $textTypeNullable
      )
    ''');

    // Drafts table
    await db.execute('''
      CREATE TABLE drafts (
        id $idType,
        capture_id $intType,
        user_id $textType,
        draft_type $textType,
        ai_confidence $realType,
        title $textType,
        description $textTypeNullable,
        due_date $textTypeNullable,
        priority $textTypeNullable,
        location $textTypeNullable,
        start_time $textTypeNullable,
        end_time $textTypeNullable,
        is_confirmed INTEGER NOT NULL DEFAULT 0,
        google_task_id $textTypeNullable,
        google_event_id $textTypeNullable,
        sync_state $textType,
        extracted_entities $textTypeNullable,
        created_at $textType,
        updated_at $textTypeNullable,
        synced_at $textTypeNullable
      )
    ''');
  }

  // Capture operations
  Future<int> insertCapture(Capture capture) async {
    final db = await instance.database;
    return await db.insert('captures', capture.toSqlite());
  }

  Future<List<Capture>> getCaptures() async {
    final db = await instance.database;
    final result = await db.query(
      'captures',
      orderBy: 'created_at DESC',
    );
    return result.map((json) => Capture.fromSqlite(json)).toList();
  }

  /// Batch operation: Get all pending captures at once
  Future<List<Capture>> getPendingCaptures() async {
    final db = await instance.database;
    final result = await db.query(
      'captures',
      where: 'state IN (?, ?, ?)',
      whereArgs: ['queued', 'error', 'processing'],
      orderBy: 'created_at ASC',
    );
    return result.map((json) => Capture.fromSqlite(json)).toList();
  }

  Future<int> updateCapture(Capture capture) async {
    final db = await instance.database;
    return await db.update(
      'captures',
      capture.toSqlite(),
      where: 'id = ?',
      whereArgs: [capture.id],
    );
  }

  /// Batch operation: Update multiple captures in a single transaction
  /// This dramatically reduces database I/O overhead
  Future<void> batchUpdateCaptures(List<Capture> captures) async {
    if (captures.isEmpty) return;

    final db = await instance.database;
    final batch = db.batch();

    for (final capture in captures) {
      batch.update(
        'captures',
        capture.toSqlite(),
        where: 'id = ?',
        whereArgs: [capture.id],
      );
    }

    await batch.commit(noResult: true);
    print('Batch updated ${captures.length} captures');
  }

  /// Batch operation: Insert multiple captures in a single transaction
  Future<void> batchInsertCaptures(List<Capture> captures) async {
    if (captures.isEmpty) return;

    final db = await instance.database;
    final batch = db.batch();

    for (final capture in captures) {
      batch.insert('captures', capture.toSqlite());
    }

    await batch.commit(noResult: true);
    print('Batch inserted ${captures.length} captures');
  }

  // Draft operations
  Future<int> insertDraft(Draft draft) async {
    final db = await instance.database;
    final data = draft.toJson();
    data['is_confirmed'] = draft.isConfirmed ? 1 : 0;
    return await db.insert('drafts', data);
  }

  Future<List<Draft>> getDrafts({bool? needsReviewOnly}) async {
    final db = await instance.database;
    
    String? whereClause;
    List<dynamic>? whereArgs;
    
    if (needsReviewOnly == true) {
      whereClause = 'is_confirmed = ?';
      whereArgs = [0];
    }
    
    final result = await db.query(
      'drafts',
      where: whereClause,
      whereArgs: whereArgs,
      orderBy: 'created_at DESC',
    );
    
    return result.map((json) {
      final draftJson = Map<String, dynamic>.from(json);
      draftJson['is_confirmed'] = json['is_confirmed'] == 1;
      return Draft.fromJson(draftJson);
    }).toList();
  }

  /// Batch operation: Get all pending drafts at once
  Future<List<Draft>> getPendingDrafts() async {
    final db = await instance.database;
    final result = await db.query(
      'drafts',
      where: 'is_confirmed = ? AND sync_state IN (?, ?)',
      whereArgs: [1, 'confirmed', 'error'],
      orderBy: 'created_at ASC',
    );
    
    return result.map((json) {
      final draftJson = Map<String, dynamic>.from(json);
      draftJson['is_confirmed'] = json['is_confirmed'] == 1;
      return Draft.fromJson(draftJson);
    }).toList();
  }

  Future<int> updateDraft(Draft draft) async {
    final db = await instance.database;
    final data = draft.toJson();
    data['is_confirmed'] = draft.isConfirmed ? 1 : 0;
    return await db.update(
      'drafts',
      data,
      where: 'id = ?',
      whereArgs: [draft.id],
    );
  }

  /// Batch operation: Update multiple drafts in a single transaction
  /// This dramatically reduces database I/O overhead
  Future<void> batchUpdateDrafts(List<Draft> drafts) async {
    if (drafts.isEmpty) return;

    final db = await instance.database;
    final batch = db.batch();

    for (final draft in drafts) {
      final data = draft.toJson();
      data['is_confirmed'] = draft.isConfirmed ? 1 : 0;
      
      batch.update(
        'drafts',
        data,
        where: 'id = ?',
        whereArgs: [draft.id],
      );
    }

    await batch.commit(noResult: true);
    print('Batch updated ${drafts.length} drafts');
  }

  /// Batch operation: Insert multiple drafts in a single transaction
  Future<void> batchInsertDrafts(List<Draft> drafts) async {
    if (drafts.isEmpty) return;

    final db = await instance.database;
    final batch = db.batch();

    for (final draft in drafts) {
      final data = draft.toJson();
      data['is_confirmed'] = draft.isConfirmed ? 1 : 0;
      batch.insert('drafts', data);
    }

    await batch.commit(noResult: true);
    print('Batch inserted ${drafts.length} drafts');
  }

  /// Batch operation: Get counts of items by state for progress tracking
  Future<Map<String, int>> getSyncStatistics() async {
    final db = await instance.database;
    
    final captureStats = await db.rawQuery('''
      SELECT state, COUNT(*) as count 
      FROM captures 
      GROUP BY state
    ''');
    
    final draftStats = await db.rawQuery('''
      SELECT sync_state, COUNT(*) as count 
      FROM drafts 
      GROUP BY sync_state
    ''');
    
    final stats = <String, int>{};
    
    for (final row in captureStats) {
      stats['captures_${row['state']}'] = row['count'] as int;
    }
    
    for (final row in draftStats) {
      stats['drafts_${row['sync_state']}'] = row['count'] as int;
    }
    
    return stats;
  }

  Future close() async {
    final db = await instance.database;
    db.close();
  }
}
