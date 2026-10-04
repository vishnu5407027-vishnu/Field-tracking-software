import 'dart:async';

import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../api/api_client.dart';
import '../api/auth_repository.dart';
import '../models/task.dart';
import '../services/ping_queue.dart';
import '../services/staff_repository.dart';
import '../services/tracking_service.dart';
import '../theme.dart';
import '../widgets/task_card.dart';
import 'login_screen.dart';
import 'profile_screen.dart';
import 'task_detail_screen.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  final _staff = StaffRepository();
  final _auth = AuthRepository();

  bool _clockedIn = false;
  bool _busy = false;
  DateTime? _clockInAt;
  String _name = '';
  List<Task> _tasks = [];
  int _tab = 0; // 0 = open, 1 = completed
  Timer? _offlineFlush;

  @override
  void initState() {
    super.initState();
    ApiClient.instance.loadName().then((n) {
      if (mounted) setState(() => _name = n ?? '');
    });
    _refresh();
    // Periodic flush picks up queued offline pings once we're back online,
    // even when the position stream is quiet.
    _offlineFlush = Timer.periodic(
      const Duration(seconds: 30),
      (_) => PingQueue.instance.flush(),
    );
  }

  @override
  void dispose() {
    _offlineFlush?.cancel();
    super.dispose();
  }

  Future<void> _refresh() async {
    try {
      final status = await _staff.fetchStatus();
      if (mounted) {
        setState(() {
          _clockedIn = status.isClockedIn;
          _clockInAt = status.clockInAt;
        });
      }
      if (_clockedIn && !TrackingService.instance.isTracking) {
        await TrackingService.instance.start();
      }
      await _loadTasks();
    } catch (e) {
      _showError(e);
    }
  }

  Future<void> _loadTasks() async {
    final tasks =
        _tab == 0 ? await _staff.myTasks() : await _staff.completedTasks();
    if (mounted) setState(() => _tasks = tasks);
  }

  void _setTab(int tab) {
    if (tab == _tab) return;
    setState(() {
      _tab = tab;
      _tasks = [];
    });
    _loadTasks().catchError(_showError);
  }

  Future<void> _openTask(Task task) async {
    await Navigator.of(context).push(
      MaterialPageRoute(builder: (_) => TaskDetailScreen(taskId: task.id)),
    );
    // Status / proofs may have changed in the detail screen.
    await _loadTasks();
  }

  Future<void> _toggleShift() async {
    setState(() => _busy = true);
    try {
      if (!_clockedIn) {
        if (!await TrackingService.instance.start()) {
          _showMessage(
            'Location permission required',
            'Allow location access ("all the time" on Android) so your route '
            'can be tracked during shifts.',
          );
          return;
        }
        await _staff.clock(true);
      } else {
        await _staff.clock(false);
        await TrackingService.instance.stop();
      }
      await _refresh();
    } catch (e) {
      _showError(e);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _openProfile() async {
    await Navigator.of(context).push(
      MaterialPageRoute(builder: (_) => const ProfileScreen()),
    );
    // The greeting reflects the (possibly edited) name on return.
    final name = await ApiClient.instance.loadName();
    if (mounted) setState(() => _name = name ?? _name);
  }

  Future<void> _signOut() async {
    if (_clockedIn) await _toggleShift();
    await _auth.logout();
    if (!mounted) return;
    Navigator.of(context).pushReplacement(
      MaterialPageRoute(builder: (_) => const LoginScreen()),
    );
  }

  void _showError(Object error) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(error.toString()), backgroundColor: Brand.red),
    );
  }

  void _showMessage(String title, String body) {
    if (!mounted) return;
    showDialog<void>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(title),
        content: Text(body),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('OK'),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Brand.surface,
      body: RefreshIndicator(
        onRefresh: _refresh,
        child: CustomScrollView(
          slivers: [
            SliverToBoxAdapter(child: _header()),
            SliverPadding(
              padding: const EdgeInsets.fromLTRB(16, 18, 16, 8),
              sliver: SliverToBoxAdapter(child: _taskTabs()),
            ),
            if (_tasks.isEmpty)
              SliverFillRemaining(
                hasScrollBody: false,
                child: _emptyTasks(),
              )
            else
              SliverPadding(
                padding: const EdgeInsets.fromLTRB(16, 0, 16, 24),
                sliver: SliverList.builder(
                  itemCount: _tasks.length,
                  itemBuilder: (_, i) => TaskCard(
                    task: _tasks[i],
                    onTap: () => _openTask(_tasks[i]),
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }

  Widget _header() {
    final greeting = _name.isEmpty ? 'Welcome' : 'Hi, $_name';
    final dateLabel = DateFormat('EEEE, d MMMM').format(DateTime.now());

    return Container(
      decoration: const BoxDecoration(
        gradient: Brand.headerGradient,
        borderRadius: BorderRadius.vertical(bottom: Radius.circular(28)),
      ),
      child: SafeArea(
        bottom: false,
        child: Padding(
          padding: const EdgeInsets.fromLTRB(20, 12, 12, 24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(greeting,
                            style: const TextStyle(
                                color: Colors.white,
                                fontSize: 22,
                                fontWeight: FontWeight.w700)),
                        Text(dateLabel,
                            style: TextStyle(
                                color: Colors.white.withValues(alpha: 0.85),
                                fontSize: 13)),
                      ],
                    ),
                  ),
                  IconButton(
                    tooltip: 'Profile',
                    icon: const Icon(Icons.account_circle_outlined,
                        color: Colors.white),
                    onPressed: _openProfile,
                  ),
                  IconButton(
                    tooltip: 'Sign out',
                    icon: const Icon(Icons.logout, color: Colors.white),
                    onPressed: _signOut,
                  ),
                ],
              ),
              const SizedBox(height: 18),
              _shiftCard(),
            ],
          ),
        ),
      ),
    );
  }

  Widget _shiftCard() {
    final onSince = _clockInAt != null
        ? 'On duty since ${DateFormat('h:mm a').format(_clockInAt!)}'
        : 'Tracking active — visible to dispatch';

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(18),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.12),
            blurRadius: 16,
            offset: const Offset(0, 6),
          ),
        ],
      ),
      child: Column(
        children: [
          Row(
            children: [
              _statusDot(_clockedIn),
              const SizedBox(width: 10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      _clockedIn ? 'On duty' : 'Off duty',
                      style: const TextStyle(
                          fontSize: 16,
                          fontWeight: FontWeight.w700,
                          color: Brand.ink),
                    ),
                    Text(
                      _clockedIn ? onSince : 'Location is not being tracked',
                      style: const TextStyle(color: Brand.slate, fontSize: 12),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 14),
          SizedBox(
            width: double.infinity,
            height: 52,
            child: FilledButton.icon(
              onPressed: _busy ? null : _toggleShift,
              icon: _busy
                  ? const SizedBox(
                      height: 18,
                      width: 18,
                      child: CircularProgressIndicator(
                          strokeWidth: 2, color: Colors.white),
                    )
                  : Icon(_clockedIn ? Icons.stop_rounded : Icons.play_arrow_rounded),
              label: Text(
                _busy
                    ? 'Please wait…'
                    : (_clockedIn ? 'Clock Out' : 'Clock In'),
                style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w600),
              ),
              style: FilledButton.styleFrom(
                backgroundColor: _clockedIn ? Brand.red : Brand.green,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(13),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _statusDot(bool on) {
    return Container(
      height: 36,
      width: 36,
      decoration: BoxDecoration(
        color: (on ? Brand.green : Brand.slate).withValues(alpha: 0.12),
        shape: BoxShape.circle,
      ),
      child: Icon(
        on ? Icons.gps_fixed : Icons.gps_off,
        size: 18,
        color: on ? Brand.green : Brand.slate,
      ),
    );
  }

  Widget _taskTabs() {
    Widget tab(int index, String label) {
      final active = _tab == index;
      return Expanded(
        child: GestureDetector(
          onTap: () => _setTab(index),
          child: Container(
            padding: const EdgeInsets.symmetric(vertical: 9),
            decoration: BoxDecoration(
              color: active ? Brand.indigo : Colors.transparent,
              borderRadius: BorderRadius.circular(10),
            ),
            alignment: Alignment.center,
            child: Text(
              label,
              style: TextStyle(
                fontWeight: FontWeight.w600,
                fontSize: 13,
                color: active ? Colors.white : Brand.slate,
              ),
            ),
          ),
        ),
      );
    }

    return Container(
      padding: const EdgeInsets.all(4),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: const Color(0xFFE2E8F0)),
      ),
      child: Row(
        children: [tab(0, 'Open tasks'), tab(1, 'Completed')],
      ),
    );
  }

  Widget _emptyTasks() {
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(Icons.task_alt, size: 48, color: Brand.slate.withValues(alpha: 0.4)),
          const SizedBox(height: 10),
          Text(_tab == 0 ? 'No open tasks' : 'No completed tasks yet',
              style: const TextStyle(color: Brand.slate, fontWeight: FontWeight.w600)),
          const SizedBox(height: 2),
          Text('Pull down to refresh',
              style: TextStyle(color: Brand.slate.withValues(alpha: 0.8), fontSize: 12)),
        ],
      ),
    );
  }
}
