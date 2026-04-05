import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../data/local/app_database.dart';

// Access the Database anywhere
final databaseProvider = Provider<AppDatabase>((ref) {
  return AppDatabase();
});
