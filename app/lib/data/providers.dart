import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:cozy_app/data/api_client.dart';

// Services
final apiClientProvider = Provider((ref) => ApiClient());

// Models (Simplified for JSON)
// We could use Freezed, but for MVP straight Map integration or simple classes.

// Providers
final dashboardSummaryProvider = FutureProvider.autoDispose((ref) async {
  final api = ref.watch(apiClientProvider);
  return await api.get('/dashboard/summary');
});

final assetsProvider = FutureProvider.autoDispose((ref) async {
  final api = ref.watch(apiClientProvider);
  return await api.get('/assets/');
});

// Daily Report Provider
final dailyReportProvider = FutureProvider.family.autoDispose<Map<String, dynamic>, String>((ref, dateStr) async {
  final api = ref.watch(apiClientProvider);
  // dateStr format: YYYY-MM-DD
  return await api.get('/dashboard/report/daily', queryParameters: {'date_str': dateStr});
});
