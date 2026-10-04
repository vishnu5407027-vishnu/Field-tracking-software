import '../api/api_client.dart';
import '../models/task.dart';

class ShiftStatus {
  ShiftStatus({required this.isClockedIn, this.clockInAt});

  final bool isClockedIn;
  final DateTime? clockInAt;
}

class StaffRepository {
  final _api = ApiClient.instance;

  Future<ShiftStatus> fetchStatus() async {
    final body = await _api.get('/staff/status');
    final shift = body['shift'] as Map<String, dynamic>?;
    return ShiftStatus(
      isClockedIn: body['isClockedIn'] as bool,
      clockInAt: shift != null
          ? DateTime.parse(shift['clockInAt'] as String).toLocal()
          : null,
    );
  }

  Future<void> clock(bool clockIn) =>
      _api.patch('/staff/clock', {'action': clockIn ? 'in' : 'out'});

  Future<List<Task>> myTasks() async {
    final body = await _api.get('/staff/tasks') as List<dynamic>;
    return [for (final json in body) Task.fromJson(json as Map<String, dynamic>)];
  }

  Future<List<Task>> completedTasks() async {
    final body = await _api.get('/staff/tasks?completed=1') as List<dynamic>;
    return [for (final json in body) Task.fromJson(json as Map<String, dynamic>)];
  }

  Future<Task> fetchTask(String taskId) async {
    final body = await _api.get('/staff/tasks/$taskId') as Map<String, dynamic>;
    return Task.fromJson(body);
  }

  Future<void> updateTaskStatus(String taskId, String status) =>
      _api.patch('/staff/tasks/$taskId', {'status': status});

  Future<void> addNoteProof(String taskId, String note) =>
      _api.post('/staff/tasks/$taskId/proofs', {'type': 'NOTE', 'content': note});

  Future<void> addPhotoProof(String taskId, String filePath) =>
      _api.uploadFile('/staff/tasks/$taskId/photo', 'photo', filePath);
}
