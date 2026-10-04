import 'api_client.dart';

class SessionUser {
  SessionUser({required this.role, required this.firstName});

  final String role;
  final String firstName;
}

class AuthRepository {
  final _api = ApiClient.instance;

  /// Returns the logged-in user; throws [ApiException] on bad credentials or
  /// when a non-field-staff account is used (this app is staff-only).
  Future<SessionUser> login(String email, String password) async {
    final body = await _api.post('/auth/login', {
      'email': email,
      'password': password,
    });
    final user = body['user'] as Map<String, dynamic>;
    if (user['role'] != 'FIELD_STAFF') {
      throw ApiException(403, 'This app is for field staff only');
    }
    await _api.saveToken(body['accessToken'] as String);
    await _api.saveName(user['firstName'] as String);
    return SessionUser(
      role: user['role'] as String,
      firstName: user['firstName'] as String,
    );
  }

  Future<void> logout() => _api.clearSession();
}
