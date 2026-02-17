import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:cozy_app/core/theme.dart';

class OptimizationChart extends StatelessWidget {
  final List<dynamic> forecastData;

  const OptimizationChart({
    super.key,
    required this.forecastData,
  });

  @override
  Widget build(BuildContext context) {
    if (forecastData.isEmpty) {
      return Container(
        height: 200,
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(24),
        ),
        alignment: Alignment.center,
        child: Text(
          "No Optimization Plan Available",
          style: TextStyle(color: Colors.grey[400]),
        ),
      );
    }

    // 1. Filter & Parse Data (Next 12 Hours)
    final now = DateTime.now();
    // In strict mode, we'd filter > now. For MVP demo, we take the first 48 points (12h * 4 intervals)
    // assuming the list starts near 'now'.
    final limitedData = forecastData.take(48).toList(); 

    final points = limitedData.asMap().entries.map((e) {
      final i = e.key;
      final d = e.value;
      final time = DateTime.parse(d['timestamp']);
      final price = (d['price'] as num).toDouble();
      final gridKw = (d['grid_kw'] as num).toDouble(); 
      final solarKw = (d['solar_kw'] as num).toDouble();
      final battKw = (d['battery_kw'] as num).toDouble();
      final evKw = (d['ev_kw'] as num).toDouble();
      final loadKw = (d.containsKey('load_kw') ? (d['load_kw'] as num).toDouble() : 0.0);
      
      return _ChartPoint(i, time, price, gridKw, solarKw, battKw, evKw, loadKw);
    }).toList();

    // 2. Calculate Scales
    double maxScale = 5.0; // Min scale
    double maxPrice = 0.0;

    for (var p in points) {
      if (p.price > maxPrice) maxPrice = p.price;

      // Supply Stack Sum
      double supply = 0;
      if (p.solarKw > 0) supply += p.solarKw;
      if (p.gridKw > 0) supply += p.gridKw;
      if (p.battKw > 0) supply += p.battKw; // Discharge

      // Demand Stack Sum (Abs)
      double demand = 0;
      demand += p.loadKw; // Always demand
      if (p.evKw > 0) demand += p.evKw; // Discharge (V2G)
      if (p.evKw < 0) demand += p.evKw.abs(); // Charge
      if (p.gridKw < 0) demand += p.gridKw.abs();
      if (p.battKw < 0) demand += p.battKw.abs(); // Charge

      if (supply > maxScale) maxScale = supply;
      if (demand > maxScale) maxScale = demand;
    }
    
    maxScale *= 1.1; // Padding
    
    // Price Scaling for Decimals
    maxPrice = maxPrice * 1.2; 
    if (maxPrice == 0) maxPrice = 0.50; // Default fallback

    return Container(
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(24),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.05),
            blurRadius: 10,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text(
                "Optimization Preview",
                style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
              ),
              Text(
                "Next 12 Hours",
                style: TextStyle(fontSize: 12, color: Colors.grey[500], fontWeight: FontWeight.bold),
              ),
            ],
          ),
          const SizedBox(height: 12),
          // Legend
          SizedBox(
            width: double.infinity,
            child: Wrap(
              spacing: 16,
              runSpacing: 8,
              alignment: WrapAlignment.start,
              crossAxisAlignment: WrapCrossAlignment.center,
              children: [
                 _LegendItem(color: AppTheme.warmYellow, label: "Solar"),
                 _LegendItem(color: AppTheme.terracotta, label: "Battery"),
                 _LegendItem(color: AppTheme.charcoal, label: "EV"),
                 _LegendItem(color: AppTheme.dullRed, label: "Home"),
                 _LegendItem(color: Colors.grey, label: "Grid"),
                 _LegendItem(color: AppTheme.charcoal.withOpacity(0.5), label: "Price", isDashed: true),
              ],
            ),
          ),
          const SizedBox(height: 24),
          AspectRatio(
            aspectRatio: 1.5,
            child: Stack(
              children: [
                // Layer 1: Stacked Bars (Energy)
                BarChart(
                  BarChartData(
                    alignment: BarChartAlignment.spaceBetween,
                    maxY: maxScale,
                    minY: -maxScale,
                    barTouchData: BarTouchData(
                      touchTooltipData: BarTouchTooltipData(
                        tooltipBgColor: Colors.white,
                        tooltipRoundedRadius: 8,
                        tooltipPadding: const EdgeInsets.all(12),
                        tooltipMargin: 8,
                        getTooltipItem: (group, groupIndex, rod, rodIndex) {
                           final p = points[groupIndex];
                           
                           // Build Lines
                           final List<TextSpan> lines = [];
                           
                           // Header: Time
                           lines.add(TextSpan(
                             text: "${DateFormat('HH:mm').format(p.time)}\n",
                             style: const TextStyle(color: Colors.black, fontSize: 14, fontWeight: FontWeight.bold, height: 1.5),
                           ));
                           
                           // Helper
                           void addLine(String label, double val, Color color) {
                             if (val.abs() > 0.05) { // Threshold to hide zeros
                               lines.add(TextSpan(
                                 text: "$label: ${val > 0 ? '+' : ''}${val.toStringAsFixed(1)} kW\n",
                                 style: TextStyle(color: color, fontSize: 12, fontWeight: FontWeight.w600, height: 1.4),
                               ));
                             }
                           }
                           
                           addLine("Solar", p.solarKw, AppTheme.warmYellow);
                           
                           if (p.loadKw > 0) {
                              lines.add(TextSpan(
                                 text: "Home: ${p.loadKw.toStringAsFixed(1)} kW\n",
                                 style: TextStyle(color: AppTheme.dullRed, fontSize: 12, fontWeight: FontWeight.w600, height: 1.4),
                               ));
                           }
                           
                           if (p.battKw != 0) {
                             // Discharge + (Up), Charge - (Down)
                             String label = p.battKw > 0 ? "Batt Dischg" : "Batt Charge";
                             lines.add(TextSpan(
                               text: "$label: ${p.battKw.abs().toStringAsFixed(1)} kW\n",
                               style: TextStyle(color: AppTheme.terracotta, fontSize: 12, fontWeight: FontWeight.w600, height: 1.4),
                             ));
                           }
                           
                           if (p.evKw.abs() > 0.05) {
                             String label = p.evKw > 0 ? "EV Dischg" : "EV Charge"; // Usually Charge (-ve)
                             lines.add(TextSpan(
                               text: "$label: ${p.evKw.abs().toStringAsFixed(1)} kW\n",
                               style: TextStyle(color: AppTheme.charcoal, fontSize: 12, fontWeight: FontWeight.w600, height: 1.4),
                             ));
                           }

                           if (p.gridKw != 0) {
                             String label = p.gridKw > 0 ? "Grid Import" : "Grid Export";
                             lines.add(TextSpan(
                               text: "$label: ${p.gridKw.abs().toStringAsFixed(1)} kW\n",
                               style: TextStyle(color: Colors.grey, fontSize: 12, fontWeight: FontWeight.w600, height: 1.4),
                             ));
                           }
                           
                           // Price
                           lines.add(TextSpan(
                             text: "Price: ${p.price.toStringAsFixed(2)} €/kWh",
                             style: TextStyle(color: AppTheme.charcoal.withOpacity(0.5), fontSize: 12, fontStyle: FontStyle.italic, height: 1.4),
                           ));

                           return BarTooltipItem(
                             "", // Main text is empty, using children
                             const TextStyle(),
                             children: lines,
                           );
                        }
                      ),
                    ),
                    titlesData: FlTitlesData(
                      show: true,
                      topTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
                      rightTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
                      leftTitles: AxisTitles(
                        sideTitles: SideTitles(
                          showTitles: true,
                          reservedSize: 40, 
                          getTitlesWidget: (val, meta) {
                            if (val == 0) return const SizedBox.shrink();
                            return Text(
                              "${val.abs().toStringAsFixed(0)} kW",
                              style: TextStyle(color: Colors.grey[400], fontSize: 10),
                            );
                          },
                        ),
                      ),
                      bottomTitles: AxisTitles(
                        sideTitles: SideTitles(
                          showTitles: true,
                          reservedSize: 30,
                          interval: 1, // We control visibility manually
                          getTitlesWidget: (val, meta) {
                            final idx = val.toInt();
                            if (idx >= 0 && idx < points.length) {
                               final date = points[idx].time;
                               // Show every 2 hours (8 steps of 15min)
                               if (idx % 8 == 0) {
                                 return Padding(
                                   padding: const EdgeInsets.only(top: 8),
                                   child: Text(
                                      DateFormat('HH:mm').format(date),
                                      style: TextStyle(color: Colors.grey[600], fontSize: 10, fontWeight: FontWeight.bold),
                                   ),
                                 );
                               }
                            }
                            return const SizedBox.shrink();
                          },
                        ),
                      ),
                    ),
                    gridData: FlGridData(
                      show: true, 
                      drawVerticalLine: false,
                      horizontalInterval: maxScale / 2,
                      getDrawingHorizontalLine: (val) => FlLine(color: Colors.grey[100], strokeWidth: 1),
                    ),
                    borderData: FlBorderData(show: false),
                    barGroups: points.map((p) {
                      // Stack Logic
                      // Positive: Solar + BattDiss + GridImp
                      // Negative: EV + BattChg + GridExp
                      
                      final rods = <BarChartRodStackItem>[];
                      double currentPos = 0;
                      double currentNeg = 0;

                      // 1. Solar (Always Top Positive)
                      if (p.solarKw > 0) {
                         rods.add(BarChartRodStackItem(currentPos, currentPos + p.solarKw, AppTheme.warmYellow));
                         currentPos += p.solarKw;
                      }

                      // 2. Battery Discharge
                      if (p.battKw > 0) {
                         rods.add(BarChartRodStackItem(currentPos, currentPos + p.battKw, AppTheme.terracotta));
                         currentPos += p.battKw;
                      }

                      // 3. Grid Import
                      if (p.gridKw > 0) {
                         rods.add(BarChartRodStackItem(currentPos, currentPos + p.gridKw, Colors.grey));
                         currentPos += p.gridKw;
                      }

                      // NEGATIVE STACK

                      // 4. Home Load (First Negative for visibility)
                      if (p.loadKw > 0) {
                         rods.add(BarChartRodStackItem(currentNeg - p.loadKw, currentNeg, AppTheme.dullRed));
                         currentNeg -= p.loadKw;
                      }

                      // 5. EV 
                      if (p.evKw > 0) { // Discharge V2G
                         rods.add(BarChartRodStackItem(currentPos, currentPos + p.evKw, AppTheme.charcoal));
                         currentPos += p.evKw;
                      }
                      if (p.evKw < 0) { // Charge
                         final val = p.evKw.abs();
                         rods.add(BarChartRodStackItem(currentNeg - val, currentNeg, AppTheme.charcoal));
                         currentNeg -= val;
                      }

                      // 6. Battery Charge
                      if (p.battKw < 0) {
                         rods.add(BarChartRodStackItem(currentNeg + p.battKw, currentNeg, AppTheme.terracotta.withOpacity(0.7))); 
                         currentNeg += p.battKw;
                      }

                      // 7. Grid Export
                      if (p.gridKw < 0) {
                         rods.add(BarChartRodStackItem(currentNeg + p.gridKw, currentNeg, Colors.grey.withOpacity(0.7)));
                         currentNeg += p.gridKw;
                      }

                      return BarChartGroupData(
                        x: p.index,
                        barRods: [
                          BarChartRodData(
                            toY: currentPos, // Max positive
                            fromY: currentNeg, // Max negative
                            width: 6, // Thick bars
                            color: Colors.transparent, // Uses stack items
                            rodStackItems: rods,
                            borderRadius: BorderRadius.zero,
                          ),
                        ],
                      );
                    }).toList(),
                  ),
                ),

                // Layer 2: Price Line Overlay
                IgnorePointer(
                  child: LineChart(
                    LineChartData(
                      minY: -maxScale, // MATCH BarChart Min
                      maxY: maxScale,  // MATCH BarChart Max
                      gridData: const FlGridData(show: false),
                      titlesData: const FlTitlesData(show: false), 
                      borderData: FlBorderData(show: false),
                      lineBarsData: [
                         LineChartBarData(
                           spots: points.map((p) {
                             // Normalize Price to Energy Scale
                             // MaxPrice should map to MaxScale
                             // 0 Price should map to 0 (Center)
                             
                             double normalizedY = (p.price / maxPrice) * maxScale;
                             return FlSpot(p.index.toDouble(), normalizedY);
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
                
                // Price Axis Label (Right Overlay)
                Positioned(
                  right: 0,
                  top: 0,
                  bottom: 0,
                  child: IgnorePointer(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      crossAxisAlignment: CrossAxisAlignment.end,
                      children: [
                        Text("${maxPrice.toStringAsFixed(2)} €/kWh", style: TextStyle(color: AppTheme.charcoal.withOpacity(0.5), fontSize: 10)),
                        const Text("0 €", style: TextStyle(color: Colors.transparent, fontSize: 10)), // Center Placeholder
                        const Text("0 €", style: TextStyle(color: Colors.transparent, fontSize: 10)), // Bottom Placeholder
                      ],
                    ),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _ChartPoint {
  final int index;
  final DateTime time;
  final double price;
  final double gridKw;
  final double solarKw;
  final double battKw;
  final double evKw;
  final double loadKw;

  _ChartPoint(this.index, this.time, this.price, this.gridKw, this.solarKw, this.battKw, this.evKw, this.loadKw);
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
      crossAxisAlignment: CrossAxisAlignment.center, // Critical for alignment
      children: [
        Container(
          width: 12,
          height: 12,
          decoration: BoxDecoration(
            color: isDashed ? Colors.transparent : color,
            border: isDashed ? Border.all(color: color, width: 2) : null,
            shape: BoxShape.circle,
          ),
          child: isDashed ? Center(child: Container(width: 4, height: 4, color: color)) : null,
        ),
        const SizedBox(width: 6), // Slightly more space
        Padding(
          padding: const EdgeInsets.only(bottom: 1), // Optical correction
          child: Text(label, style: TextStyle(color: Colors.grey[600], fontSize: 13, height: 1.0)),
        ),
      ],
    );
  }
}
