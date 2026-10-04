import '../api/api_client.dart';

class Profile {
  Profile({
    required this.email,
    required this.firstName,
    required this.lastName,
    required this.role,
    required this.createdAt,
    this.tenantName,
  });

  factory Profile.fromJson(Map<String, dynamic> json) => Profile(
        email: json['email'] as String,
        firstName: json['firstName'] as String,
        lastName: json['lastName'] as String,
        role: json['role'] as String,
        createdAt: DateTime.parse(json['createdAt'] as String).toLocal(),
        tenantName: json['tenantName'] as String?,
      );

  final String email;
  final String firstName;
  final String lastName;
  final String role;
  final DateTime createdAt;
  final String? tenantName;
}

class ProfileRepository {
  final _api = ApiClient.instance;

  Future<Profile> fetch() async {
    final body = await _api.get('/me') as Map<String, dynamic>;
    return Profile.fromJson(body);
  }

  Future<Profile> update({
    required String firstName,
    required String lastName,
    required String email,
  }) async {
    final body = await _api.patch('/me', {
      'firstName': firstName,
      'lastName': lastName,
      'email': email,
    }) as Map<String, dynamic>;
    return Profile.fromJson(body);
  }

  Future<void> changePassword(String current, String next) =>
      _api.post('/me/password', {'currentPassword': current, 'newPassword': next});
}
