import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:cozy_app/core/theme.dart';
import 'package:cozy_app/data/providers.dart';
import 'package:intl/intl.dart';
import 'package:fl_chart/fl_chart.dart';
import 'package:phosphor_flutter/phosphor_flutter.dart';

class SavingsReportModal extends ConsumerWidget {
  const SavingsReportModal({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Scaffold(
      backgroundColor: AppTheme.cream,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        leading: IconButton(
          icon: const Icon(Icons.close, color: AppTheme.charcoal),
          onPressed: () => Navigator.of(context).pop(),
        ),
        title: const Text("Detailed Analysis", style: TextStyle(color: AppTheme.charcoal)),
      ),
      body: const _ReportView(),
    );
  }
}

class _ReportView extends ConsumerWidget {
  const _ReportView();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    // Request "48h" explicitly
    final reportAsync = ref.watch(dailyReportProvider("48h"));

    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Header
          const Text(
            "Last 48 Hours",
            textAlign: TextAlign.center,
            style: TextStyle(
              fontSize: 20,
              fontWeight: FontWeight.bold,
              color: AppTheme.charcoal,
            ),
          ),
          const SizedBox(height: 24),

          reportAsync.when(
            data: (data) {
              final summary = data['summary'];
              final optimizedSeries = (data['optimized_series'] as List).cast<Map<String, dynamic>>();
              final benchmarkSeries = (data['benchmark_series'] as List).cast<Map<String, dynamic>>();
              
              final savingsEur = summary['savings_eur'] ?? 0.0;
              final realCost = summary['real_cost_eur'] ?? 0.0;
              final benchCost = summary['benchmark_cost_eur'] ?? 0.0;

              return Column(
                children: [
                   // Savings Big Number
                   Text(
                      "€ ${savingsEur.toStringAsFixed(2)}",
                      style: const TextStyle(
                        color: AppTheme.terracotta,
                        fontSize: 64,
                        fontWeight: FontWeight.w900,
                        letterSpacing: -2.0,
                        height: 1.0,
                      ),
                   ),
                   const Text(
                     "TOTAL SAVINGS",
                     style: TextStyle(
                       color: AppTheme.terracotta,
                       fontSize: 14,
                       fontWeight: FontWeight.bold,
                       letterSpacing: 1.0,
                     ),
                   ),
                   const SizedBox(height: 32),

                   // Comparison Cards
                   Row(
                     children: [
                       Expanded(child: _CostSummaryCard(label: "You Paid", amount: realCost, isHighlighted: true)),
                       const SizedBox(width: 16),
                       Expanded(child: _CostSummaryCard(label: "Benchmark", amount: benchCost, isHighlighted: false)),
                     ],
                   ),
                   const SizedBox(height: 48),

                   // Chart 1: With Cozy
                   const Text("With Cozy (Optimized)", style: TextStyle(fontWeight: FontWeight.bold, fontSize: 18)),
                   const SizedBox(height: 16),
                   _DetailedMultiAssetChart(points: optimizedSeries),
                   
                   const SizedBox(height: 32),
                   
                   // Chart 2: Without Cozy
                   const Text("Without Cozy (Benchmark)", style: TextStyle(fontWeight: FontWeight.bold, fontSize: 18)),
                   const SizedBox(height: 16),
                   _DetailedMultiAssetChart(points: benchmarkSeries),
                ],
              );
            },
            loading: () => const Center(child: CircularProgressIndicator(color: AppTheme.terracotta)),
            error: (e, s) => Center(child: Text("Error: $e")),
          ),
        ],
      ),
    );
  }
}

class _CostSummaryCard extends StatelessWidget {
  final String label;
  final double amount;
  final bool isHighlighted;

  const _CostSummaryCard({required this.label, required this.amount, required this.isHighlighted});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        border: isHighlighted ? Border.all(color: AppTheme.terracotta, width: 2) : Border.all(color: Colors.transparent),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.05),
            blurRadius: 10,
            offset: const Offset(0, 4),
          )
        ]
      ),
      child: Column(
        children: [
          Text(label, style: TextStyle(color: Colors.grey[600], fontSize: 14)),
          const SizedBox(height: 4),
          Text("€${amount.toStringAsFixed(2)}", style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 24)),
        ],
      ),
    );
  }
}

class _DetailedMultiAssetChart extends StatelessWidget {
  final List<Map<String, dynamic>> points;

  const _DetailedMultiAssetChart({required this.points});

  @override
  Widget build(BuildContext context) {
    if (points.isEmpty) return const Center(child: Text("No Data"));

    // 1. Aggregate to Hourly Data (Better Overview)
    final List<Map<String, dynamic>> hourlyPoints = [];
    if (points.isNotEmpty) {
      Map<String, dynamic>? currentHour;
      int count = 0;
      
      String pad(int n) => n.toString().padLeft(2, '0');

      for (var p in points) {
        final t = DateTime.parse(p['timestamp']);
        // Key by Hour (ISO 8601 Safe)
        final hourKey = "${t.year}-${pad(t.month)}-${pad(t.day)} ${pad(t.hour)}:00:00";
        
        if (currentHour == null || currentHour['timestamp'] != hourKey) {
          if (currentHour != null) {
            // Finalize previous
            _averageMap(currentHour, count);
            hourlyPoints.add(currentHour);
          }
          // Start new
          currentHour = Map.from(p);
          currentHour['timestamp'] = hourKey; // Snap to hour
          count = 1;
        } else {
          // Accumulate
          _accumulateMap(currentHour, p);
          count++;
        }
      }
      // Finalize last
      if (currentHour != null) {
        _averageMap(currentHour, count);
        hourlyPoints.add(currentHour);
      }
    }

    // 2. Calculate Scales & MaxPrice
    double maxScale = 5.0; 
    double maxPrice = 0.0;
    
    for (var d in hourlyPoints) {
      // Energy Scale
      double supply = (d['solar_kw'] ?? 0.0) as double;
      double grid = (d['grid_kw'] ?? 0.0) as double;
      double batt = (d['battery_kw'] ?? 0.0) as double;
      
      double posSum = 0;
      if (supply > 0) posSum += supply;
      if (grid > 0) posSum += grid;
      if (batt > 0) posSum += batt; 
      
      double negSum = 0;
      double load = (d['load_kw'] ?? 0.0) as double;
      double ev = (d['ev_kw'] ?? 0.0) as double;
      
      negSum += load; 
      if (ev > 0) posSum += ev; 
      if (ev < 0) negSum += ev.abs();
      if (grid < 0) negSum += grid.abs();
      if (batt < 0) negSum += batt.abs();
      
      if (posSum > maxScale) maxScale = posSum;
      if (negSum > maxScale) maxScale = negSum;
      
      // Price Scale
      double price = (d['price'] ?? 0.0) as double;
      if (price > maxPrice) maxPrice = price;
    }
    maxScale *= 1.1;
    maxPrice *= 1.2;
    if (maxPrice == 0) maxPrice = 0.50;

    return Column(
      children: [
        // Legend
        Wrap(
          spacing: 12,
          runSpacing: 8,
          alignment: WrapAlignment.center,
          crossAxisAlignment: WrapCrossAlignment.center,
          children: [
             _LegendItem(color: AppTheme.warmYellow, label: "Solar"),
             _LegendItem(color: AppTheme.terracotta, label: "Bat"),
             _LegendItem(color: AppTheme.dullRed, label: "Home"),
             _LegendItem(color: AppTheme.charcoal, label: "EV"),
             _LegendItem(color: Colors.grey, label: "Grid"),
             _LegendItem(color: AppTheme.charcoal.withOpacity(0.5), label: "Price", isDashed: true),
          ],
        ),
        const SizedBox(height: 16),
        
        // Chart
        AspectRatio(
          aspectRatio: 1.7,
          child: Stack(
            children: [
              // Layer 1: Bars
              BarChart(
                BarChartData(
                  alignment: BarChartAlignment.spaceBetween,
                  maxY: maxScale,
                  minY: -maxScale,
                  barTouchData: BarTouchData(
                    touchTooltipData: BarTouchTooltipData(
                      tooltipBgColor: Colors.white,
                      getTooltipItem: (group, groupIndex, rod, rodIndex) {
                         final d = hourlyPoints[groupIndex];
                         final time = DateTime.parse(d['timestamp']);
                         final price = (d['price'] as num).toDouble();
                         
                         final solar = (d['solar_kw'] as num? ?? 0.0).toDouble();
                         final grid = (d['grid_kw'] as num? ?? 0.0).toDouble();
                         final batt = (d['battery_kw'] as num? ?? 0.0).toDouble();
                         final load = (d['load_kw'] as num? ?? 0.0).toDouble();
                         final ev = (d['ev_kw'] as num? ?? 0.0).toDouble();

                         final List<TextSpan> lines = [];
                         
                         // Price
                         lines.add(TextSpan(
                           text: "\nPrice: ${price.toStringAsFixed(2)} €/kWh\n", 
                           style: TextStyle(color: AppTheme.charcoal.withOpacity(0.6), fontSize: 12, fontStyle: FontStyle.italic)
                         ));
                         
                         // Solar
                         if (solar > 0.1) {
                           lines.add(TextSpan(text: "Solar: ${solar.toStringAsFixed(1)} kW\n", style: const TextStyle(color: AppTheme.warmYellow, fontSize: 12)));
                         }
                         // Battery
                         if (batt.abs() > 0.1) {
                           lines.add(TextSpan(text: "Bat: ${batt.toStringAsFixed(1)} kW\n", style: const TextStyle(color: AppTheme.terracotta, fontSize: 12)));
                         }
                         // Home
                         if (load > 0.1) {
                           lines.add(TextSpan(text: "Home: -${load.toStringAsFixed(1)} kW\n", style: const TextStyle(color: AppTheme.dullRed, fontSize: 12)));
                         }
                         // EV
                         if (ev.abs() > 0.1) {
                           lines.add(TextSpan(text: "EV: ${ev.toStringAsFixed(1)} kW\n", style: const TextStyle(color: AppTheme.charcoal, fontSize: 12)));
                         }
                         // Grid
                         if (grid.abs() > 0.1) {
                           lines.add(TextSpan(text: "Grid: ${grid.toStringAsFixed(1)} kW", style: const TextStyle(color: Colors.grey, fontSize: 12)));
                         }

                         return BarTooltipItem(
                           DateFormat('HH:mm').format(time),
                           const TextStyle(color: Colors.black, fontWeight: FontWeight.bold),
                           children: lines
                         );
                      } 
                    ), 
                  ),
                  titlesData: FlTitlesData(
                    show: true,
                    leftTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
                    rightTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
                    topTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
                    bottomTitles: AxisTitles(
                      sideTitles: SideTitles(
                        showTitles: true,
                        reservedSize: 30,
                        interval: 1, 
                        getTitlesWidget: (val, meta) {
                          final idx = val.toInt();
                          // Show label every 6 hours (6 steps of 1h)
                          if (idx >= 0 && idx < hourlyPoints.length && idx % 6 == 0) {
                             final d = hourlyPoints[idx];
                             final time = DateTime.parse(d['timestamp']);
                             return Padding(
                               padding: const EdgeInsets.only(top: 8),
                               child: Text(
                                  DateFormat('d MMM\nHH:mm').format(time),
                                  textAlign: TextAlign.center,
                                  style: TextStyle(color: Colors.grey[600], fontSize: 9, fontWeight: FontWeight.bold),
                               ),
                             );
                          }
                          return const SizedBox.shrink();
                        },
                      ),
                    ),
                  ),
                  gridData: const FlGridData(show: false),
                  borderData: FlBorderData(show: false),
                  barGroups: hourlyPoints.asMap().entries.map((e) {
                    final i = e.key;
                    final d = e.value;
                    
                    double solar = (d['solar_kw'] ?? 0.0) as double;
                    double grid = (d['grid_kw'] ?? 0.0) as double;
                    double batt = (d['battery_kw'] ?? 0.0) as double;
                    double load = (d['load_kw'] ?? 0.0) as double;
                    double ev = (d['ev_kw'] ?? 0.0) as double;
                    
                    final rods = <BarChartRodStackItem>[];
                    double currentPos = 0;
                    double currentNeg = 0;

                    if (solar > 0) { rods.add(BarChartRodStackItem(currentPos, currentPos + solar, AppTheme.warmYellow)); currentPos += solar; }
                    if (batt > 0) { rods.add(BarChartRodStackItem(currentPos, currentPos + batt, AppTheme.terracotta)); currentPos += batt; }
                    if (grid > 0) { rods.add(BarChartRodStackItem(currentPos, currentPos + grid, Colors.grey)); currentPos += grid; }
                    
                    if (load > 0) { rods.add(BarChartRodStackItem(currentNeg - load, currentNeg, AppTheme.dullRed)); currentNeg -= load; }
                    if (ev < 0) { rods.add(BarChartRodStackItem(currentNeg + ev, currentNeg, AppTheme.charcoal)); currentNeg += ev; }
                    if (batt < 0) { rods.add(BarChartRodStackItem(currentNeg + batt, currentNeg, AppTheme.terracotta.withOpacity(0.7))); currentNeg += batt; }
                    if (grid < 0) { rods.add(BarChartRodStackItem(currentNeg + grid, currentNeg, Colors.grey.withOpacity(0.7))); currentNeg += grid; }

                    return BarChartGroupData(
                      x: i,
                      barRods: [
                        BarChartRodData(
                          toY: currentPos,
                          fromY: currentNeg,
                          width: 4, // Thicker bars for 48h view (Hourly)
                          color: Colors.transparent,
                          rodStackItems: rods,
                          borderRadius: BorderRadius.zero,
                        ),
                      ],
                    );
                  }).toList(),
                ),
              ),

              // Layer 2: Price Line
              IgnorePointer(
                child: LineChart(
                  LineChartData(
                    minY: -maxScale,
                    maxY: maxScale, 
                    gridData: const FlGridData(show: false),
                    titlesData: const FlTitlesData(show: false), 
                    borderData: FlBorderData(show: false),
                    lineBarsData: [
                       LineChartBarData(
                         spots: hourlyPoints.asMap().entries.map((e) {
                           int i = e.key;
                           double price = (e.value['price'] ?? 0.0) as double;
                           double normalizedY = (price / maxPrice) * maxScale;
                           return FlSpot(i.toDouble(), normalizedY);
                         }).toList(),
                         isCurved: true,
                         color: AppTheme.charcoal.withOpacity(0.5),
                         barWidth: 2,
                         dashArray: [5, 5],
                         dotData: const FlDotData(show: false),
                       ),
                    ],
                  ),
                ),
              ),
              
              // Layer 3: Price Labels
              Positioned(
                right: 0, top: 0, bottom: 0,
                child: IgnorePointer(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    crossAxisAlignment: CrossAxisAlignment.end,
                    children: [
                      Text("${maxPrice.toStringAsFixed(2)} €/kWh", style: TextStyle(color: AppTheme.charcoal.withOpacity(0.5), fontSize: 10)),
                      const Text("0 €", style: TextStyle(color: Colors.transparent, fontSize: 10)), 
                      const Text("0 €", style: TextStyle(color: Colors.transparent, fontSize: 10)), 
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }

  void _accumulateMap(Map<String, dynamic> acc, Map<String, dynamic> next) {
    acc['solar_kw'] = (acc['solar_kw'] ?? 0.0) + (next['solar_kw'] ?? 0.0);
    acc['grid_kw'] = (acc['grid_kw'] ?? 0.0) + (next['grid_kw'] ?? 0.0);
    acc['battery_kw'] = (acc['battery_kw'] ?? 0.0) + (next['battery_kw'] ?? 0.0);
    acc['load_kw'] = (acc['load_kw'] ?? 0.0) + (next['load_kw'] ?? 0.0);
    acc['ev_kw'] = (acc['ev_kw'] ?? 0.0) + (next['ev_kw'] ?? 0.0);
    acc['price'] = (acc['price'] ?? 0.0) + (next['price'] ?? 0.0);
  }

  void _averageMap(Map<String, dynamic> acc, int count) {
    if (count == 0) return;
    acc['solar_kw'] = (acc['solar_kw'] as double) / count;
    acc['grid_kw'] = (acc['grid_kw'] as double) / count;
    acc['battery_kw'] = (acc['battery_kw'] as double) / count;
    acc['load_kw'] = (acc['load_kw'] as double) / count;
    acc['ev_kw'] = (acc['ev_kw'] as double) / count;
    acc['price'] = (acc['price'] as double) / count;
  }
}

class _LegendItem extends StatelessWidget {
  final Color color;
  final String label;
  final bool isDashed;

  const _LegendItem({required this.color, required this.label, this.isDashed = false});

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 8, height: 8, 
          decoration: BoxDecoration(
             color: isDashed ? Colors.transparent : color,
             border: isDashed ? Border.all(color: color, width: 2) : null,
             shape: BoxShape.circle,
          ),
          child: isDashed ? Center(child: Container(width: 4, height: 4, color: color)) : null
        ),
        const SizedBox(width: 4),
        Text(label, style: TextStyle(color: Colors.grey[600], fontSize: 12)),
      ],
    );
  }
}
