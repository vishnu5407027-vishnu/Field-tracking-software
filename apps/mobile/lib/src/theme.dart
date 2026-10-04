import 'package:flutter/material.dart';

/// Shared brand palette so screens stay visually consistent.
class Brand {
  static const indigo = Color(0xFF4F46E5);
  static const violet = Color(0xFF7C3AED);
  static const ink = Color(0xFF0F172A);
  static const slate = Color(0xFF64748B);
  static const surface = Color(0xFFF1F5F9);
  static const green = Color(0xFF16A34A);
  static const red = Color(0xFFDC2626);

  static const headerGradient = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [indigo, violet],
  );
}
