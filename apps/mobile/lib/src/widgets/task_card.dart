import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../models/task.dart';
import '../theme.dart';

const _statusColors = <String, Color>{
  'ASSIGNED': Color(0xFF1D4ED8),
  'EN_ROUTE': Color(0xFFB45309),
  'IN_PROGRESS': Color(0xFF7E22CE),
  'COMPLETED': Brand.green,
  'CANCELLED': Brand.red,
};

class TaskCard extends StatelessWidget {
  const TaskCard({super.key, required this.task, required this.onTap});

  final Task task;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final accent = _statusColors[task.status] ?? Brand.slate;
    final dateLabel = task.completedAt != null
        ? 'Completed ${DateFormat('d MMM, h:mm a').format(task.completedAt!)}'
        : 'Due ${DateFormat('d MMM, h:mm a').format(task.dueAt)}';

    return Container(
      margin: const EdgeInsets.only(bottom: 12),
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
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          borderRadius: BorderRadius.circular(16),
          onTap: onTap,
          child: IntrinsicHeight(
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Container(
                  width: 5,
                  decoration: BoxDecoration(
                    color: accent,
                    borderRadius:
                        const BorderRadius.horizontal(left: Radius.circular(16)),
                  ),
                ),
                Expanded(
                  child: Padding(
                    padding: const EdgeInsets.all(14),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Expanded(
                              child: Text(task.title,
                                  style: const TextStyle(
                                      fontWeight: FontWeight.w700,
                                      fontSize: 15,
                                      color: Brand.ink)),
                            ),
                            _chip(task.status, accent),
                          ],
                        ),
                        const SizedBox(height: 6),
                        _meta(Icons.location_on_outlined, task.address),
                        const SizedBox(height: 4),
                        _meta(
                          task.completedAt != null
                              ? Icons.check_circle_outline
                              : Icons.schedule,
                          dateLabel,
                        ),
                        if (task.proofs.isNotEmpty) ...[
                          const SizedBox(height: 8),
                          Row(
                            children: [
                              if (task.photos.isNotEmpty) ...[
                                const Icon(Icons.photo_outlined,
                                    size: 15, color: Brand.slate),
                                const SizedBox(width: 3),
                                Text('${task.photos.length}',
                                    style: const TextStyle(
                                        color: Brand.slate, fontSize: 12)),
                                const SizedBox(width: 12),
                              ],
                              if (task.notes.isNotEmpty) ...[
                                const Icon(Icons.sticky_note_2_outlined,
                                    size: 15, color: Brand.slate),
                                const SizedBox(width: 3),
                                Text('${task.notes.length}',
                                    style: const TextStyle(
                                        color: Brand.slate, fontSize: 12)),
                              ],
                            ],
                          ),
                        ],
                      ],
                    ),
                  ),
                ),
                const Padding(
                  padding: EdgeInsets.only(right: 8),
                  child: Icon(Icons.chevron_right, color: Brand.slate),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _chip(String status, Color color) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(999),
      ),
      child: Text(status.replaceAll('_', ' '),
          style:
              TextStyle(fontSize: 11, color: color, fontWeight: FontWeight.w700)),
    );
  }

  Widget _meta(IconData icon, String text) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Icon(icon, size: 15, color: Brand.slate),
        const SizedBox(width: 6),
        Expanded(
            child: Text(text,
                style: const TextStyle(color: Brand.slate, fontSize: 13))),
      ],
    );
  }
}
