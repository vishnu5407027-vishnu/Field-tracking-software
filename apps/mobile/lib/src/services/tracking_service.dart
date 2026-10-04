import 'dart:async';

import 'package:battery_plus/battery_plus.dart';
import 'package:geolocator/geolocator.dart';

import 'ping_queue.dart';

/// Records the route while a shift is open and stops the moment the user
/// clocks out — tracking never runs off-shift.
///
/// On Android the position stream keeps a foreground service alive (the
/// "On duty" notification), so points keep arriving with the app in the
/// background. Every point lands in [PingQueue] first; a timer flushes the
/// queue to the server, which also drains anything captured offline.
class TrackingService {
  TrackingService._();

  static final TrackingService instance = TrackingService._();

  final _battery = Battery();
  StreamSubscription<Position>? _positions;
  Timer? _flushTimer;

  bool get isTracking => _positions != null;

  /// Returns false when location permission was refused.
  Future<bool> start() async {
    if (isTracking) return true;

    if (!await Geolocator.isLocationServiceEnabled()) return false;
    var permission = await Geolocator.checkPermission();
    if (permission == LocationPermission.denied) {
      permission = await Geolocator.requestPermission();
    }
    if (permission == LocationPermission.denied ||
        permission == LocationPermission.deniedForever) {
      return false;
    }

    final settings = AndroidSettings(
      accuracy: LocationAccuracy.high,
      distanceFilter: 50, // meters between points
      intervalDuration: const Duration(seconds: 60),
      foregroundNotificationConfig: const ForegroundNotificationConfig(
        notificationTitle: 'On duty',
        notificationText: 'FieldTracking is recording your route for this shift.',
        enableWakeLock: true,
      ),
    );

    _positions = Geolocator.getPositionStream(locationSettings: settings)
        .listen(_onPosition, onError: (_) {});
    // Safety-net flush in case a point fails to send (e.g. a brief outage).
    _flushTimer = Timer.periodic(
      const Duration(seconds: 30),
      (_) => PingQueue.instance.flush(),
    );

    // Grab one fix immediately so the dispatcher map shows the worker the
    // moment they go on duty, instead of waiting for the first stream tick.
    unawaited(_captureNow());
    return true;
  }

  Future<void> _captureNow() async {
    try {
      final position = await Geolocator.getCurrentPosition(
        locationSettings: const LocationSettings(accuracy: LocationAccuracy.high),
      );
      await _onPosition(position);
    } catch (_) {
      // No immediate fix available — the stream will deliver one shortly.
    }
  }

  Future<void> _onPosition(Position position) async {
    final battery = await _battery.batteryLevel.catchError((_) => -1);
    await PingQueue.instance.enqueue({
      'lat': position.latitude,
      'lng': position.longitude,
      'speed': position.speed,
      'heading': position.heading,
      'accuracy': position.accuracy,
      if (battery >= 0) 'batteryLevel': battery.toDouble(),
      'recordedAt': position.timestamp.toUtc().toIso8601String(),
    });
    // Push right away so the dashboard updates in real time. Offline, the
    // flush is a no-op and the point waits in the queue for the next attempt.
    await PingQueue.instance.flush();
  }

  Future<void> stop() async {
    await _positions?.cancel();
    _positions = null;
    _flushTimer?.cancel();
    _flushTimer = null;
    await PingQueue.instance.flush(); // push any remaining buffered points
  }
}
