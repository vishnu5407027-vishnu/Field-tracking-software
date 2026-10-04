import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:intl/intl.dart';

import '../api/api_client.dart';
import '../models/task.dart';
import '../services/staff_repository.dart';
import '../theme.dart';

const _statusColors = <String, Color>{
  'ASSIGNED': Color(0xFF1D4ED8),
  'EN_ROUTE': Color(0xFFB45309),
  'IN_PROGRESS': Color(0xFF7E22CE),
  'COMPLETED': Brand.green,
  'CANCELLED': Brand.red,
};

class TaskDetailScreen extends StatefulWidget {
  const TaskDetailScreen({super.key, required this.taskId});

  final String taskId;

  @override
  State<TaskDetailScreen> createState() => _TaskDetailScreenState();
}

class _TaskDetailScreenState extends State<TaskDetailScreen> {
  final _staff = StaffRepository();
  final _picker = ImagePicker();

  Task? _task;
  bool _loading = true;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final task = await _staff.fetchTask(widget.taskId);
      if (mounted) {
        setState(() {
          _task = task;
          _loading = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() => _loading = false);
        _snack(e.toString(), Brand.red);
      }
    }
  }

  Future<void> _advance() async {
    final next = _task?.next;
    if (next == null) return;
    setState(() => _busy = true);
    try {
      await _staff.updateTaskStatus(_task!.id, next);
      await _load();
    } catch (e) {
      _snack(e.toString(), Brand.red);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _addNote() async {
    final controller = TextEditingController();
    final note = await showDialog<String>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Add work note'),
        content: TextField(
          controller: controller,
          autofocus: true,
          maxLines: 3,
          decoration: const InputDecoration(hintText: 'What was done on site?'),
        ),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(context), child: const Text('Cancel')),
          FilledButton(
              onPressed: () => Navigator.pop(context, controller.text.trim()),
              child: const Text('Save')),
        ],
      ),
    );
    if (note == null || note.isEmpty) return;
    setState(() => _busy = true);
    try {
      await _staff.addNoteProof(_task!.id, note);
      await _load();
      _snack('Note attached', Brand.green);
    } catch (e) {
      _snack(e.toString(), Brand.red);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _addPhoto() async {
    final source = await showModalBottomSheet<ImageSource>(
      context: context,
      builder: (context) => SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            ListTile(
              leading: const Icon(Icons.photo_camera_outlined),
              title: const Text('Take a photo'),
              onTap: () => Navigator.pop(context, ImageSource.camera),
            ),
            ListTile(
              leading: const Icon(Icons.photo_library_outlined),
              title: const Text('Choose from gallery'),
              onTap: () => Navigator.pop(context, ImageSource.gallery),
            ),
          ],
        ),
      ),
    );
    if (source == null) return;

    final XFile? shot = await _picker.pickImage(
      source: source,
      imageQuality: 70,
      maxWidth: 1600,
    );
    if (shot == null) return;

    setState(() => _busy = true);
    try {
      await _staff.addPhotoProof(_task!.id, shot.path);
      await _load();
      _snack('Photo attached', Brand.green);
    } catch (e) {
      _snack(e.toString(), Brand.red);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  void _snack(String text, Color color) {
    if (!mounted) return;
    ScaffoldMessenger.of(context)
        .showSnackBar(SnackBar(content: Text(text), backgroundColor: color));
  }

  @override
  Widget build(BuildContext context) {
    final task = _task;
    return Scaffold(
      backgroundColor: Brand.surface,
      appBar: AppBar(
        title: const Text('Task'),
        backgroundColor: Brand.indigo,
        foregroundColor: Colors.white,
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : task == null
              ? const Center(child: Text('Task not found'))
              : RefreshIndicator(
                  onRefresh: _load,
                  child: ListView(
                    padding: const EdgeInsets.all(16),
                    children: [
                      _headerCard(task),
                      const SizedBox(height: 14),
                      if (!task.isClosed) _actions(task),
                      if (!task.isClosed) const SizedBox(height: 14),
                      _photosCard(task),
                      const SizedBox(height: 14),
                      _notesCard(task),
                    ],
                  ),
                ),
    );
  }

  Widget _headerCard(Task task) {
    final accent = _statusColors[task.status] ?? Brand.slate;
    return _card(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(task.title,
                    style: const TextStyle(
                        fontSize: 18, fontWeight: FontWeight.w700, color: Brand.ink)),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                decoration: BoxDecoration(
                  color: accent.withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(999),
                ),
                child: Text(task.status.replaceAll('_', ' '),
                    style: TextStyle(
                        color: accent, fontWeight: FontWeight.w700, fontSize: 12)),
              ),
            ],
          ),
          const SizedBox(height: 10),
          if (task.description != null && task.description!.isNotEmpty) ...[
            Text(task.description!,
                style: const TextStyle(color: Brand.slate, fontSize: 14)),
            const SizedBox(height: 10),
          ],
          _meta(Icons.location_on_outlined, task.address),
          const SizedBox(height: 6),
          _meta(Icons.schedule,
              'Due ${DateFormat('d MMM, h:mm a').format(task.dueAt)}'),
          if (task.completedAt != null) ...[
            const SizedBox(height: 6),
            _meta(Icons.check_circle_outline,
                'Completed ${DateFormat('d MMM, h:mm a').format(task.completedAt!)}'),
          ],
        ],
      ),
    );
  }

  Widget _actions(Task task) {
    return _card(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const Text('Actions',
              style: TextStyle(fontWeight: FontWeight.w700, color: Brand.ink)),
          const SizedBox(height: 12),
          if (task.next != null)
            FilledButton.icon(
              onPressed: _busy ? null : _advance,
              icon: const Icon(Icons.arrow_forward),
              label: Text('Mark ${task.next!.replaceAll('_', ' ')}'),
              style: FilledButton.styleFrom(
                backgroundColor: Brand.indigo,
                padding: const EdgeInsets.symmetric(vertical: 14),
                shape:
                    RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
              ),
            ),
          const SizedBox(height: 10),
          Row(
            children: [
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: _busy ? null : _addPhoto,
                  icon: const Icon(Icons.photo_camera_outlined, size: 18),
                  label: const Text('Add photo'),
                  style: OutlinedButton.styleFrom(
                    foregroundColor: Brand.indigo,
                    side: const BorderSide(color: Brand.indigo),
                    padding: const EdgeInsets.symmetric(vertical: 12),
                    shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(12)),
                  ),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: _busy ? null : _addNote,
                  icon: const Icon(Icons.note_add_outlined, size: 18),
                  label: const Text('Add note'),
                  style: OutlinedButton.styleFrom(
                    foregroundColor: Brand.indigo,
                    side: const BorderSide(color: Brand.indigo),
                    padding: const EdgeInsets.symmetric(vertical: 12),
                    shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(12)),
                  ),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _photosCard(Task task) {
    final photos = task.photos;
    return _card(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('Photo attachments (${photos.length})',
              style: const TextStyle(fontWeight: FontWeight.w700, color: Brand.ink)),
          const SizedBox(height: 12),
          if (photos.isEmpty)
            const Text('No photos yet.',
                style: TextStyle(color: Brand.slate, fontSize: 13))
          else
            GridView.count(
              crossAxisCount: 3,
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              mainAxisSpacing: 8,
              crossAxisSpacing: 8,
              children: [
                for (final p in photos)
                  ClipRRect(
                    borderRadius: BorderRadius.circular(10),
                    child: Image.network(
                      ApiClient.mediaUrl(p.content),
                      fit: BoxFit.cover,
                      errorBuilder: (_, __, ___) => Container(
                        color: Brand.surface,
                        child: const Icon(Icons.broken_image_outlined,
                            color: Brand.slate),
                      ),
                    ),
                  ),
              ],
            ),
        ],
      ),
    );
  }

  Widget _notesCard(Task task) {
    final notes = task.notes;
    return _card(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('Work notes (${notes.length})',
              style: const TextStyle(fontWeight: FontWeight.w700, color: Brand.ink)),
          const SizedBox(height: 12),
          if (notes.isEmpty)
            const Text('No notes yet.',
                style: TextStyle(color: Brand.slate, fontSize: 13))
          else
            for (final n in notes)
              Container(
                margin: const EdgeInsets.only(bottom: 8),
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Brand.surface,
                  borderRadius: BorderRadius.circular(10),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(n.content,
                        style: const TextStyle(color: Brand.ink, fontSize: 14)),
                    const SizedBox(height: 4),
                    Text(DateFormat('d MMM, h:mm a').format(n.createdAt),
                        style: const TextStyle(color: Brand.slate, fontSize: 11)),
                  ],
                ),
              ),
        ],
      ),
    );
  }

  Widget _card({required Widget child}) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.05),
            blurRadius: 10,
            offset: const Offset(0, 3),
          ),
        ],
      ),
      child: child,
    );
  }

  Widget _meta(IconData icon, String text) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Icon(icon, size: 16, color: Brand.slate),
        const SizedBox(width: 6),
        Expanded(
            child: Text(text,
                style: const TextStyle(color: Brand.slate, fontSize: 13))),
      ],
    );
  }
}
