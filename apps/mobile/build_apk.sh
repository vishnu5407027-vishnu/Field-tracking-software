#!/usr/bin/env bash
# Builds the release APK inside the cirruslabs/flutter Docker image.
# Usage (from repo root):
#   docker run --rm -v "<repo>/apps/mobile:/work" -w /work ghcr.io/cirruslabs/flutter:stable \
#     bash -c "tr -d '\r' < /work/build_apk.sh | bash -s -- http://192.168.1.7:8000/api/v1"
set -euo pipefail

API_BASE="${1:-http://10.0.2.2:8000/api/v1}"
echo "==> Building APK with API_BASE=$API_BASE"

git config --global --add safe.directory '*' || true

# 1. Generate the Android platform folder if it doesn't exist yet.
if [ ! -d android ]; then
  flutter create . --org dev.fieldtracking --project-name fieldtracking --platforms android
  rm -f test/widget_test.dart  # template test references the template app
fi

# 2. Permissions: internet + (background) location + foreground service.
# Camera capture uses image_picker's system-camera intent, which needs no
# CAMERA permission (and declaring it without a runtime request can break
# capture on some devices).
MANIFEST=android/app/src/main/AndroidManifest.xml
if ! grep -q ACCESS_FINE_LOCATION "$MANIFEST"; then
  sed -i 's#<manifest xmlns:android="http://schemas.android.com/apk/res/android">#<manifest xmlns:android="http://schemas.android.com/apk/res/android">\n    <uses-permission android:name="android.permission.INTERNET" />\n    <uses-permission android:name="android.permission.ACCESS_FINE_LOCATION" />\n    <uses-permission android:name="android.permission.ACCESS_COARSE_LOCATION" />\n    <uses-permission android:name="android.permission.ACCESS_BACKGROUND_LOCATION" />\n    <uses-permission android:name="android.permission.FOREGROUND_SERVICE" />\n    <uses-permission android:name="android.permission.FOREGROUND_SERVICE_LOCATION" />#' "$MANIFEST"
fi

# Allow cleartext HTTP so the app reaches the LAN API and loads proof photos
# over http:// (no TLS in this demo).
if ! grep -q "usesCleartextTraffic" "$MANIFEST"; then
  sed -i 's#<application#<application android:usesCleartextTraffic="true"#' "$MANIFEST"
fi

# 3. geolocator needs minSdk 23.
for GRADLE in android/app/build.gradle.kts android/app/build.gradle; do
  [ -f "$GRADLE" ] || continue
  sed -i 's/minSdk = flutter.minSdkVersion/minSdk = 23/' "$GRADLE"
  sed -i 's/minSdkVersion flutter.minSdkVersion/minSdkVersion 23/' "$GRADLE"
done

# 4. Build.
flutter pub get
flutter build apk --release --dart-define=API_BASE="$API_BASE"

echo "==> APK ready: build/app/outputs/flutter-apk/app-release.apk"
