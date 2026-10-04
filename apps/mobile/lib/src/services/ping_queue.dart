import 'dart:convert';

import 'package:path/path.dart' as p;
import 'package:sqflite/sqflite.dart';

import '../api/api_client.dart';

/// Store-and-forward queue for GPS pings.
///
/// Pings are always written to SQLite first, then flushed to the server in
/// batches. If the network is down the flush fails silently and the rows
/// simply wait for the next attempt — nothing is lost offline.
class PingQueue {
  PingQueue._();

  static final PingQueue instance = PingQueue._();

  static const flushBatchSize = 20;
  static const _maxRowsPerFlush = 200;

  Database? _db;

  Future<Database> _database() async {
    _db ??= await openDatabase(
      p.join(await getDatabasesPath(), 'fieldtracking.db'),
      version: 1,
      onCreate: (db, _) => db.execute(
        'CREATE TABLE ping_queue ('
        '  id INTEGER PRIMARY KEY AUTOINCREMENT,'
        '  payload TEXT NOT NULL'
        ')',
      ),
    );
    return _db!;
  }

  Future<void> enqueue(Map<String, dynamic> ping) async {
    final db = await _database();
    await db.insert('ping_queue', {'payload': jsonEncode(ping)});
  }

  Future<int> pendingCount() async {
    final db = await _database();
    final rows = await db.rawQuery('SELECT COUNT(*) AS n FROM ping_queue');
    return Sqflite.firstIntValue(rows) ?? 0;
  }

  /// Push queued pings to the server; keeps them on any failure.
  Future<void> flush() async {
    final db = await _database();
    final rows = await db.query(
      'ping_queue',
      orderBy: 'id',
      limit: _maxRowsPerFlush,
    );
    if (rows.isEmpty) return;

    final pings = [
      for (final row in rows) jsonDecode(row['payload'] as String),
    ];
    try {
      await ApiClient.instance.post('/staff/locations', {'pings': pings});
      final maxId = rows.last['id'] as int;
      await db.delete('ping_queue', where: 'id <= ?', whereArgs: [maxId]);
    } catch (_) {
      // Offline or server unavailable — retry on the next flush.
    }
  }
}
