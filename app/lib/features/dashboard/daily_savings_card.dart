import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:cozy_app/core/theme.dart';
import 'package:cozy_app/data/providers.dart';
import 'package:cozy_app/features/savings/savings_report_modal.dart';
import 'package:intl/intl.dart';

class DailySavingsCard extends ConsumerWidget {
  const DailySavingsCard({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final summaryAsync = ref.watch(dashboardSummaryProvider);
    
    return GestureDetector(
      onTap: () {
        showGeneralDialog(
          context: context,
          barrierDismissible: true,
          barrierLabel: "Savings Report",
          transitionDuration: const Duration(milliseconds: 300),
          pageBuilder: (ctx, anim1, anim2) {
             // Currently only supports 48h view, but we can extend later
            return const SavingsReportModal();
          },
          transitionBuilder: (ctx, anim1, anim2, child) {
            return SlideTransition(
              position: Tween<Offset>(begin: const Offset(0, 1), end: Offset.zero)
                  .animate(CurvedAnimation(parent: anim1, curve: Curves.easeOutCubic)),
              child: child,
            );
          },
        );
      },
      child: Container(
        color: Colors.transparent, 
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12), // Reduced horizontal padding
        width: double.infinity,
        child: summaryAsync.when(
          data: (data) {
            final savings48h = (data['summary']?['savings_eur'] ?? 0.0);
            final savingsMonth = (data['month_savings_eur'] ?? 0.0);
            
            return Row(
              mainAxisAlignment: MainAxisAlignment.spaceEvenly,
              children: [
                _SavingsItem(
                  label: "Savings (Last 48h)",
                  value: savings48h,
                  showChevron: true,
                ),
                Container(height: 50, width: 1, color: Colors.grey.withOpacity(0.2)),
                _SavingsItem(
                  label: "Savings (DEC)", // Hardcoded for now or use formatting
                  value: savingsMonth,
                  isMonth: true,
                ),
              ],
            );
          },
          loading: () => const Center(child: CircularProgressIndicator(color: AppTheme.terracotta)),
          error: (_,__) => const Text("--", style: TextStyle(color: AppTheme.terracotta, fontSize: 32)),
        ),
      ),
    );
  }
}

class _SavingsItem extends StatelessWidget {
  final String label;
  final double value;
  final bool showChevron;
  final bool isMonth;

  const _SavingsItem({
    required this.label, 
    required this.value, 
    this.showChevron = false,
    this.isMonth = false
  });

  @override
  Widget build(BuildContext context) {
    // Dynamic Month Label
    String displayLabel = label;
    if (isMonth) {
       displayLabel = "Savings (${DateFormat('MMM').format(DateTime.now())})";
    }

    return Expanded(
      child: Column(
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Text(
                displayLabel,
                style: TextStyle(
                  color: AppTheme.charcoal.withOpacity(0.6), 
                  fontSize: 14, // Smaller font for dual display
                  fontWeight: FontWeight.w600,
                ),
              ),
              if (showChevron) ...[
                const SizedBox(width: 4),
                Icon(Icons.chevron_right_rounded, color: AppTheme.charcoal.withOpacity(0.4), size: 16),
              ],
            ],
          ),
          const SizedBox(height: 4),
          Text(
            "€ ${value.toStringAsFixed(2)}",
            style: const TextStyle(
              color: AppTheme.terracotta,
              fontSize: 36, // Smaller font (was 64)
              fontWeight: FontWeight.w900,
              letterSpacing: -1.0,
            ),
          ),
        ],
      ),
    );
  }
}
