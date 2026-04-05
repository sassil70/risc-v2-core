import 'package:drift/drift.dart';
import 'package:uuid/uuid.dart';

// Helper function to avoid import issues in generated code
String generateUuid() => const Uuid().v4();

// 1. Sessions Table (The Digital Parcel)
class Sessions extends Table {
  TextColumn get id => text().clientDefault(generateUuid)();
  TextColumn get projectReference => text().nullable()(); // Linked Project
  DateTimeColumn get startedAt => dateTime()(); // UTC
  DateTimeColumn get closedAt => dateTime().nullable()(); // UTC
  BoolColumn get isLocked => boolean().withDefault(const Constant(false))(); // Witness Seal
  
  @override
  Set<Column> get primaryKey => {id};
}

// 2. Media Assets Table (The Evidence)
class MediaAssets extends Table {
  TextColumn get id => text().clientDefault(generateUuid)();
  TextColumn get sessionId => text().references(Sessions, #id)();
  
  // Storage
  TextColumn get localPath => text()();
  TextColumn get assetType => text()(); // 'image' or 'audio'
  
  // Forensic Data
  TextColumn get fileHash => text().nullable()(); // SHA-256
  DateTimeColumn get capturedAt => dateTime()(); // UTC
  
  // Spatial Binding (Optional)
  TextColumn get roomTag => text().nullable()(); // e.g., "Living Room"
  TextColumn get elementTag => text().nullable()(); // e.g., "Wall"
  
  @override
  Set<Column> get primaryKey => {id};
}
