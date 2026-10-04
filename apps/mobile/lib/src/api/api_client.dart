import 'dart:convert';

import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

/// Thrown for non-2xx API responses with the server's error message.
class ApiException implements Exception {
  ApiException(this.statusCode, this.message);

  final int statusCode;
  final String message;

  @override
  String toString() => message;
}

/// Singleton HTTP client for the Django REST API (camelCase JSON, JWT auth).
class ApiClient {
  ApiClient._();

  static final ApiClient instance = ApiClient._();

  /// Override at build time for a physical device:
  ///   flutter run --dart-define=API_BASE=http://192.168.1.10:8000/api/v1
  /// The default reaches the host machine from the Android emulator.
  static const String baseUrl = String.fromEnvironment(
    'API_BASE',
    defaultValue: 'http://10.0.2.2:8000/api/v1',
  );

  /// Absolute URL for a server media path like "/media/proofs/x.jpg".
  static String mediaUrl(String path) {
    if (path.startsWith('http')) return path;
    final origin = baseUrl.replaceFirst(RegExp(r'/api/v1/?$'), '');
    return '$origin$path';
  }

  static const _tokenKey = 'ft_token';
  static const _nameKey = 'ft_name';

  String? _token;

  bool get isAuthed => _token != null;

  Future<bool> loadSession() async {
    final prefs = await SharedPreferences.getInstance();
    _token = prefs.getString(_tokenKey);
    return _token != null;
  }

  Future<void> saveToken(String token) async {
    _token = token;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_tokenKey, token);
  }

  Future<void> saveName(String name) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_nameKey, name);
  }

  Future<String?> loadName() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(_nameKey);
  }

  Future<void> clearSession() async {
    _token = null;
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_tokenKey);
    await prefs.remove(_nameKey);
  }

  Map<String, String> get _headers => {
        'Content-Type': 'application/json',
        if (_token != null) 'Authorization': 'Bearer $_token',
      };

  Future<dynamic> get(String path) => _send('GET', path);

  Future<dynamic> post(String path, Object body) => _send('POST', path, body);

  Future<dynamic> patch(String path, Object body) => _send('PATCH', path, body);

  /// Multipart upload of a single file (used for camera proof photos).
  Future<dynamic> uploadFile(String path, String field, String filePath) async {
    final request = http.MultipartRequest('POST', Uri.parse('$baseUrl$path'));
    if (_token != null) request.headers['Authorization'] = 'Bearer $_token';
    request.files.add(await http.MultipartFile.fromPath(field, filePath));

    final streamed = await request.send().timeout(const Duration(seconds: 60));
    final response = await http.Response.fromStream(streamed);
    if (response.statusCode >= 200 && response.statusCode < 300) {
      return response.body.isEmpty ? null : jsonDecode(response.body);
    }
    String message = 'Upload failed (${response.statusCode})';
    try {
      final decoded = jsonDecode(response.body);
      if (decoded is Map && decoded['detail'] is String) {
        message = decoded['detail'] as String;
      }
    } catch (_) {}
    throw ApiException(response.statusCode, message);
  }

  Future<dynamic> _send(String method, String path, [Object? body]) async {
    final uri = Uri.parse('$baseUrl$path');
    final request = http.Request(method, uri)..headers.addAll(_headers);
    if (body != null) request.body = jsonEncode(body);

    final streamed = await request.send().timeout(const Duration(seconds: 20));
    final response = await http.Response.fromStream(streamed);

    if (response.statusCode >= 200 && response.statusCode < 300) {
      return response.body.isEmpty ? null : jsonDecode(response.body);
    }

    String message = 'Request failed (${response.statusCode})';
    try {
      final decoded = jsonDecode(response.body);
      if (decoded is Map && decoded['detail'] is String) {
        message = decoded['detail'] as String;
      } else if (decoded is Map && decoded.isNotEmpty) {
        final first = decoded.values.first;
        if (first is List && first.isNotEmpty) message = first.first.toString();
      }
    } catch (_) {}
    throw ApiException(response.statusCode, message);
  }
}
