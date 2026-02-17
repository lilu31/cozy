import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:cozy_app/core/theme.dart';
import 'package:cozy_app/features/dashboard/dashboard_screen.dart';

void main() {
  runApp(const ProviderScope(child: CozyApp()));
}

class CozyApp extends StatelessWidget {
  const CozyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Cozy Energy',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.lightTheme,
      home: const DashboardScreen(),
    );
  }
}
