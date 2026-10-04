# FieldTracking — Flutter field staff app

Shift control, background route tracking with an offline queue, and task
management for field staff. Talks to the Django API (`apps/api`).

## One-time setup

The repo ships only `lib/` + `pubspec.yaml`; generate the Android/iOS
platform folders locally:

```bash
cd apps/mobile
flutter create . --org dev.fieldtracking --project-name fieldtracking
flutter pub get
```

### Android permissions

Add inside `<manifest>` in `android/app/src/main/AndroidManifest.xml`:

```xml
<uses-permission android:name="android.permission.INTERNET" />
<uses-permission android:name="android.permission.ACCESS_FINE_LOCATION" />
<uses-permission android:name="android.permission.ACCESS_COARSE_LOCATION" />
<uses-permission android:name="android.permission.ACCESS_BACKGROUND_LOCATION" />
<uses-permission android:name="android.permission.FOREGROUND_SERVICE" />
<uses-permission android:name="android.permission.FOREGROUND_SERVICE_LOCATION" />
```

For tracking to continue with the screen off, the user must choose
**"Allow all the time"** when prompted for location access.

### iOS permissions

Add to `ios/Runner/Info.plist`:

```xml
<key>NSLocationWhenInUseUsageDescription</key>
<string>Your route is recorded while you are on shift.</string>
<key>NSLocationAlwaysAndWhenInUseUsageDescription</key>
<string>Your route is recorded while you are on shift.</string>
<key>UIBackgroundModes</key>
<array><string>location</string></array>
```

## Running

```bash
# Android emulator (API reachable on 10.0.2.2 — the default):
flutter run

# Physical device — point at your machine's LAN IP:
flutter run --dart-define=API_BASE=http://192.168.1.10:8000/api/v1
```

Demo login: `ravi@acme.test` / `Password123!` (after the API seeds).

## How tracking works

- Clock-in starts a `geolocator` position stream (50 m / 60 s pulses). On
  Android the stream runs a foreground service, so points keep arriving in
  the background under the "On duty" notification.
- Every point is written to a local SQLite queue first
  (`lib/src/services/ping_queue.dart`), then flushed to
  `POST /staff/locations` in batches — if the device is offline, points
  simply wait for the next flush. Nothing is lost.
- Clock-out stops the stream, does a final flush, and the server clears the
  live marker from the dispatch map.
