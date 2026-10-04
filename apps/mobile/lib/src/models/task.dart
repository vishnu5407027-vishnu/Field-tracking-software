class TaskProof {
  TaskProof({required this.type, required this.content, required this.createdAt});

  factory TaskProof.fromJson(Map<String, dynamic> json) => TaskProof(
        type: json['type'] as String,
        content: json['content'] as String,
        createdAt: DateTime.parse(json['createdAt'] as String).toLocal(),
      );

  final String type; // PHOTO | SIGNATURE | NOTE
  final String content;
  final DateTime createdAt;

  bool get isPhoto => type == 'PHOTO';
}

class Task {
  Task({
    required this.id,
    required this.title,
    required this.status,
    required this.address,
    required this.dueAt,
    required this.proofs,
    this.description,
    this.completedAt,
  });

  factory Task.fromJson(Map<String, dynamic> json) => Task(
        id: json['id'] as String,
        title: json['title'] as String,
        status: json['status'] as String,
        address: json['address'] as String,
        dueAt: DateTime.parse(json['dueAt'] as String).toLocal(),
        description: json['description'] as String?,
        completedAt: json['completedAt'] != null
            ? DateTime.parse(json['completedAt'] as String).toLocal()
            : null,
        proofs: [
          for (final p in (json['proofs'] as List<dynamic>? ?? []))
            TaskProof.fromJson(p as Map<String, dynamic>),
        ],
      );

  final String id;
  final String title;
  final String status;
  final String address;
  final DateTime dueAt;
  final List<TaskProof> proofs;
  final String? description;
  final DateTime? completedAt;

  /// ASSIGNED -> EN_ROUTE -> IN_PROGRESS -> COMPLETED
  static const nextStatus = <String, String>{
    'ASSIGNED': 'EN_ROUTE',
    'EN_ROUTE': 'IN_PROGRESS',
    'IN_PROGRESS': 'COMPLETED',
  };

  String? get next => nextStatus[status];

  bool get isClosed => status == 'COMPLETED' || status == 'CANCELLED';

  List<TaskProof> get photos => proofs.where((p) => p.isPhoto).toList();
  List<TaskProof> get notes => proofs.where((p) => !p.isPhoto).toList();
}
