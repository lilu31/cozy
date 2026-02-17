import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:cozy_app/data/providers.dart';

class SettingsScreen extends ConsumerWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Scaffold(
      appBar: AppBar(title: const Text("Settings")),
      body: ListView(
        children: [
          const Padding(
            padding: EdgeInsets.all(16.0),
            child: Text("Demo Controls", style: TextStyle(fontWeight: FontWeight.bold, color: Colors.grey)),
          ),
          ListTile(
            title: const Text("Advance Time (15 min)"),
            subtitle: const Text("Simulates physics and re-optimizes"),
            trailing: const Icon(Icons.fast_forward),
            onTap: () async {
               // Show loading
               ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text("Simulating...")));
               
               final api = ref.read(apiClientProvider);
               try {
                 await api.post('/debug/advance-time', data: {'minutes': 15});
                 ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text("Time Advanced! Refreshing...")));
                 ref.refresh(dashboardSummaryProvider);
                 ref.refresh(assetsProvider);
               } catch (e) {
                 ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text("Error: $e")));
               }
            },
          ),
        ],
      ),
    );
  }
}
