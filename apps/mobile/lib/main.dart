import 'package:flutter/material.dart';

import 'src/api/api_client.dart';
import 'src/screens/home_screen.dart';
import 'src/screens/login_screen.dart';
import 'src/theme.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final authed = await ApiClient.instance.loadSession();
  runApp(FieldTrackingApp(initiallyAuthed: authed));
}

class FieldTrackingApp extends StatelessWidget {
  const FieldTrackingApp({super.key, required this.initiallyAuthed});

  final bool initiallyAuthed;

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'FieldTracking',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(
          seedColor: Brand.indigo,
          primary: Brand.indigo,
        ),
        scaffoldBackgroundColor: Brand.surface,
        useMaterial3: true,
      ),
      home: initiallyAuthed ? const HomeScreen() : const LoginScreen(),
    );
  }
}
