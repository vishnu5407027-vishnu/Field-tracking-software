import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../api/api_client.dart';
import '../services/profile_repository.dart';
import '../theme.dart';

const _roleLabels = <String, String>{
  'TENANT_ADMIN': 'Tenant Admin',
  'DISPATCHER': 'Dispatcher',
  'FIELD_STAFF': 'Field Staff',
};

/// Self-service profile: edit name/email and change password. The home
/// screen reloads its greeting after this screen is popped.
class ProfileScreen extends StatefulWidget {
  const ProfileScreen({super.key});

  @override
  State<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends State<ProfileScreen> {
  final _repo = ProfileRepository();

  Profile? _profile;
  bool _loading = true;
  bool _savingProfile = false;
  bool _savingPassword = false;

  final _first = TextEditingController();
  final _last = TextEditingController();
  final _email = TextEditingController();
  final _current = TextEditingController();
  final _next = TextEditingController();
  final _confirm = TextEditingController();

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    for (final c in [_first, _last, _email, _current, _next, _confirm]) {
      c.dispose();
    }
    super.dispose();
  }

  Future<void> _load() async {
    try {
      final profile = await _repo.fetch();
      if (!mounted) return;
      setState(() {
        _profile = profile;
        _first.text = profile.firstName;
        _last.text = profile.lastName;
        _email.text = profile.email;
        _loading = false;
      });
    } catch (e) {
      if (mounted) {
        setState(() => _loading = false);
        _snack(e.toString(), Brand.red);
      }
    }
  }

  Future<void> _saveProfile() async {
    setState(() => _savingProfile = true);
    try {
      final updated = await _repo.update(
        firstName: _first.text.trim(),
        lastName: _last.text.trim(),
        email: _email.text.trim(),
      );
      await ApiClient.instance.saveName(updated.firstName);
      if (!mounted) return;
      setState(() => _profile = updated);
      _snack('Profile updated', Brand.green);
    } catch (e) {
      _snack(e.toString(), Brand.red);
    } finally {
      if (mounted) setState(() => _savingProfile = false);
    }
  }

  Future<void> _changePassword() async {
    if (_next.text != _confirm.text) {
      _snack('New passwords do not match', Brand.red);
      return;
    }
    if (_next.text.length < 8) {
      _snack('New password must be at least 8 characters', Brand.red);
      return;
    }
    setState(() => _savingPassword = true);
    try {
      await _repo.changePassword(_current.text, _next.text);
      _current.clear();
      _next.clear();
      _confirm.clear();
      _snack('Password updated', Brand.green);
    } catch (e) {
      _snack(e.toString(), Brand.red);
    } finally {
      if (mounted) setState(() => _savingPassword = false);
    }
  }

  void _snack(String text, Color color) {
    if (!mounted) return;
    ScaffoldMessenger.of(context)
        .showSnackBar(SnackBar(content: Text(text), backgroundColor: color));
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Brand.surface,
      appBar: AppBar(
        title: const Text('My Profile'),
        backgroundColor: Brand.indigo,
        foregroundColor: Colors.white,
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : ListView(
              padding: const EdgeInsets.all(16),
              children: [
                if (_profile != null) _identityCard(_profile!),
                const SizedBox(height: 16),
                _editCard(),
                const SizedBox(height: 16),
                _passwordCard(),
              ],
            ),
    );
  }

  Widget _identityCard(Profile p) {
    final initials =
        ((p.firstName.isNotEmpty ? p.firstName[0] : '') +
                (p.lastName.isNotEmpty ? p.lastName[0] : ''))
            .toUpperCase();
    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        gradient: Brand.headerGradient,
        borderRadius: BorderRadius.circular(18),
      ),
      child: Row(
        children: [
          CircleAvatar(
            radius: 30,
            backgroundColor: Colors.white24,
            child: Text(initials,
                style: const TextStyle(
                    color: Colors.white,
                    fontSize: 20,
                    fontWeight: FontWeight.w700)),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('${p.firstName} ${p.lastName}',
                    style: const TextStyle(
                        color: Colors.white,
                        fontSize: 18,
                        fontWeight: FontWeight.w700)),
                Text(p.email,
                    style: TextStyle(
                        color: Colors.white.withValues(alpha: 0.9), fontSize: 13)),
                const SizedBox(height: 4),
                Text(
                  '${_roleLabels[p.role] ?? p.role}'
                  '${p.tenantName != null ? ' · ${p.tenantName}' : ''}\n'
                  'Member since ${DateFormat('d MMM yyyy').format(p.createdAt)}',
                  style: TextStyle(
                      color: Colors.white.withValues(alpha: 0.85), fontSize: 12),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _editCard() {
    return _card(
      title: 'Edit details',
      children: [
        _field(_first, 'First name', Icons.person_outline),
        const SizedBox(height: 12),
        _field(_last, 'Last name', Icons.person_outline),
        const SizedBox(height: 12),
        _field(_email, 'Email', Icons.mail_outline,
            keyboard: TextInputType.emailAddress),
        const SizedBox(height: 16),
        _primaryButton('Save changes', _savingProfile, _saveProfile),
      ],
    );
  }

  Widget _passwordCard() {
    return _card(
      title: 'Change password',
      children: [
        _field(_current, 'Current password', Icons.lock_outline, obscure: true),
        const SizedBox(height: 12),
        _field(_next, 'New password', Icons.lock_reset, obscure: true),
        const SizedBox(height: 12),
        _field(_confirm, 'Confirm new password', Icons.lock_reset, obscure: true),
        const SizedBox(height: 16),
        _primaryButton('Update password', _savingPassword, _changePassword),
      ],
    );
  }

  Widget _card({required String title, required List<Widget> children}) {
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
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title,
              style: const TextStyle(
                  fontWeight: FontWeight.w700, fontSize: 15, color: Brand.ink)),
          const SizedBox(height: 14),
          ...children,
        ],
      ),
    );
  }

  Widget _field(
    TextEditingController controller,
    String label,
    IconData icon, {
    bool obscure = false,
    TextInputType? keyboard,
  }) {
    return TextField(
      controller: controller,
      obscureText: obscure,
      keyboardType: keyboard,
      autocorrect: false,
      decoration: InputDecoration(
        labelText: label,
        prefixIcon: Icon(icon),
        border: const OutlineInputBorder(),
      ),
    );
  }

  Widget _primaryButton(String label, bool busy, VoidCallback onTap) {
    return SizedBox(
      width: double.infinity,
      height: 48,
      child: FilledButton(
        onPressed: busy ? null : onTap,
        style: FilledButton.styleFrom(
          backgroundColor: Brand.indigo,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        ),
        child: busy
            ? const SizedBox(
                height: 18,
                width: 18,
                child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
              )
            : Text(label,
                style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w600)),
      ),
    );
  }
}
