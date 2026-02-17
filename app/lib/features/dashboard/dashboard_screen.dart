import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:phosphor_flutter/phosphor_flutter.dart';
import 'package:cozy_app/core/theme.dart';
import 'package:cozy_app/data/providers.dart';
import 'package:cozy_app/features/dashboard/energy_flow_view.dart';
import 'package:cozy_app/features/dashboard/optimization_chart.dart';
import 'package:cozy_app/features/settings/settings_screen.dart';
import 'package:cozy_app/features/dashboard/daily_savings_card.dart';
import 'package:flutter_animate/flutter_animate.dart';

class DashboardScreen extends ConsumerWidget {
  const DashboardScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final summaryAsync = ref.watch(dashboardSummaryProvider);

    return Scaffold(
      backgroundColor: Colors.white, // allow stack to show through
      appBar: AppBar(
        title: const Text("Cozy"),
        backgroundColor: Colors.transparent, // Transparent to show gradient
        elevation: 0,
        actions: [
          IconButton(
            icon: const Icon(PhosphorIconsRegular.gear),
            onPressed: () {
              Navigator.of(context).push(MaterialPageRoute(builder: (_) => const SettingsScreen()));
            },
          )
        ],
      ),
      body: Stack(
        children: [
          // 1. Ambient Background Layer
          // Base Gradient
          Container(
            decoration: BoxDecoration(
              gradient: LinearGradient(
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
                colors: [
                  AppTheme.cream,
                  AppTheme.cream.withOpacity(0.8),
                  Colors.white,
                ],
              ),
            ),
          ),
          
          // Orb 1: Solar Warmth (Top Left)
          Positioned(
            top: -100,
            left: -100,
            child: Container(
              width: 500,
              height: 500,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                gradient: RadialGradient(
                  colors: [
                    AppTheme.warmYellow.withOpacity(0.4), // Boosted
                    AppTheme.warmYellow.withOpacity(0.0),
                  ],
                ),
              ),
            ).animate(onPlay: (c) => c.repeat(reverse: true))
             .scaleXY(begin: 1.0, end: 1.2, duration: 4.seconds, curve: Curves.easeInOut),
          ),

          // Orb 2: Terracotta Haze (Bottom Right)
          Positioned(
            bottom: -150,
            right: -50,
            child: Container(
              width: 600,
              height: 600,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                gradient: RadialGradient(
                  colors: [
                    AppTheme.terracotta.withOpacity(0.3), // Boosted
                    AppTheme.terracotta.withOpacity(0.0),
                  ],
                ),
              ),
            ).animate(onPlay: (c) => c.repeat(reverse: true))
             .scaleXY(begin: 1.2, end: 1.0, duration: 5.seconds, curve: Curves.easeInOut),
          ),

          // 2. Main Content
          RefreshIndicator(
            onRefresh: () => ref.refresh(dashboardSummaryProvider.future),
            child: SingleChildScrollView(
              physics: const AlwaysScrollableScrollPhysics(),
              child: Padding(
                padding: const EdgeInsets.all(24.0),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    // Savings Card (Interactive)
                    const DailySavingsCard(),
                    
                    const SizedBox(height: 48), // More breathing room
                    
                    // Live House
                    SizedBox(
                      height: MediaQuery.of(context).size.height * 0.55, // Larger responsive height
                      child: const EnergyFlowView(),
                    ),
                    
                    const SizedBox(height: 48),
                    
                    // Optimization Chart
                    summaryAsync.when(
                      data: (data) {
                        final forecast = data['forecast'] as List? ?? [];
                        return OptimizationChart(forecastData: forecast);
                      },
                      loading: () => const SizedBox(),
                      error: (_,__) => const SizedBox(),
                    ),

                    const SizedBox(height: 48),

                    // Asset List
                    const Text("Your Assets", style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold)),
                    const SizedBox(height: 24),
                    
                    Consumer(builder: (ctx, ref, _) {
                      final assetsAsync = ref.watch(assetsProvider);
                      return assetsAsync.when(
                        data: (assets) {
                          final list = assets as List;
                          return Column(
                            children: list.map((a) => _AssetCard(data: a)).toList()
                                .animate(interval: 100.ms).fadeIn().slideY(begin: 0.2, end: 0,curve: Curves.easeOut),
                          );
                        },
                        loading: () => const LinearProgressIndicator(color: AppTheme.terracotta),
                        error: (e,s) => Text("Error loading assets: $e"),
                      );
                    }),
                  ],
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _AssetCard extends StatelessWidget {
  final dynamic data;
  const _AssetCard({required this.data});

  @override
  Widget build(BuildContext context) {
    final type = data['asset_type'];
    final name = data['display_name'];
    final power = (data['current_power_kw'] as num).toDouble();
    final soc = data['current_soc'];
    
    final capacity = data['capacity_kwh'];
    
    IconData icon;
    Color iconColor;
    
    if (type == 'PV') {
      icon = PhosphorIconsRegular.sun;
      iconColor = AppTheme.warmYellow;
    } else if (type == 'BATTERY') {
      icon = PhosphorIconsRegular.batteryHigh;
      iconColor = AppTheme.terracotta;
    } else if (type == 'EV') {
      icon = PhosphorIconsRegular.car;
      iconColor = AppTheme.charcoal;
    } else {
      icon = PhosphorIconsRegular.lightning;
      iconColor = AppTheme.charcoal;
    }

    String subtitleText = "Active";
    if (type == 'BATTERY') {
      if (soc != null) {
        subtitleText = "SoC: $soc%";
        if (capacity != null) {
          final stored = (soc / 100.0) * capacity;
          subtitleText += " (${stored.toStringAsFixed(1)} kWh)";
        }
      }
    } else if (type == 'EV') {
      if (soc != null) subtitleText = "SoC: $soc%";
    }

    return Card(
      margin: const EdgeInsets.only(bottom: 16), // More spacing
      child: ListTile(
        contentPadding: const EdgeInsets.all(16),
        leading: Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: iconColor.withOpacity(0.1),
            shape: BoxShape.circle, // Circular icons
          ),
          child: Icon(icon, color: iconColor, size: 28),
        ),
        title: Text(name, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 18)),
        subtitle: Text(subtitleText, style: TextStyle(color: Colors.grey[600])),
        trailing: Text(
          "${power > 0 ? '+' : ''}${power.toStringAsFixed(1)} kW",
          style: TextStyle(
            color: power > 0 ? AppTheme.terracotta : (power < 0 ? AppTheme.warmYellow : Colors.grey),
            fontWeight: FontWeight.bold,
            fontSize: 18,
          ),
        ),
      ),
    );
  }
}
