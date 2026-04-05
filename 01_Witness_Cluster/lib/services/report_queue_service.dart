import 'dart:async';
import '../services/api_service.dart';

/// Represents a single report generation job
class ReportJob {
  final String projectId;
  final String roomId;
  final String roomName;
  String status; // QUEUED, PROCESSING, COMPLETE, ERROR
  String? errorMessage;
  DateTime queuedAt;
  DateTime? completedAt;
  Map<String, dynamic>? result;

  ReportJob({
    required this.projectId,
    required this.roomId,
    required this.roomName,
    this.status = 'QUEUED',
    DateTime? queuedAt,
  }) : queuedAt = queuedAt ?? DateTime.now();
}

/// Manages a queue of report generation jobs.
/// Processes one at a time in the background so the inspector is never blocked.
class ReportQueueService {
  static final ReportQueueService _instance = ReportQueueService._internal();
  factory ReportQueueService() => _instance;
  ReportQueueService._internal();

  final ApiService _api = ApiService();
  final List<ReportJob> _queue = [];
  bool _isProcessing = false;

  // Stream controller for UI updates
  final _statusController = StreamController<List<ReportJob>>.broadcast();
  Stream<List<ReportJob>> get statusStream => _statusController.stream;

  List<ReportJob> get jobs => List.unmodifiable(_queue);

  int get pendingCount => _queue.where((j) => j.status == 'QUEUED').length;
  int get processingCount =>
      _queue.where((j) => j.status == 'PROCESSING').length;
  int get completedCount =>
      _queue.where((j) => j.status == 'COMPLETE').length;

  /// Check if a room already has a job in the queue
  bool hasJobForRoom(String roomId) =>
      _queue.any((j) => j.roomId == roomId &&
          (j.status == 'QUEUED' || j.status == 'PROCESSING'));

  /// Get the latest job for a room (any status)
  ReportJob? getLatestJobForRoom(String roomId) {
    final jobs = _queue.where((j) => j.roomId == roomId).toList();
    if (jobs.isEmpty) return null;
    return jobs.last;
  }

  /// Enqueue a new report generation job
  void enqueue(String projectId, String roomId, String roomName) {
    // Don't duplicate if already queued/processing
    if (hasJobForRoom(roomId)) return;

    _queue.add(ReportJob(
      projectId: projectId,
      roomId: roomId,
      roomName: roomName,
    ));
    _notifyListeners();
    _processNext();
  }

  /// Remove a completed or errored job
  void removeJob(String roomId) {
    _queue.removeWhere((j) =>
        j.roomId == roomId &&
        (j.status == 'COMPLETE' || j.status == 'ERROR'));
    _notifyListeners();
  }

  /// Retry a failed job
  void retry(String roomId) {
    final job = _queue.firstWhere(
      (j) => j.roomId == roomId && j.status == 'ERROR',
      orElse: () => ReportJob(
          projectId: '', roomId: '', roomName: ''),
    );
    if (job.roomId.isNotEmpty) {
      job.status = 'QUEUED';
      job.errorMessage = null;
      _notifyListeners();
      _processNext();
    }
  }

  void _notifyListeners() {
    _statusController.add(List.from(_queue));
  }

  Future<void> _processNext() async {
    if (_isProcessing) return;

    final nextJob = _queue.cast<ReportJob?>().firstWhere(
      (j) => j!.status == 'QUEUED',
      orElse: () => null,
    );

    if (nextJob == null) return;

    _isProcessing = true;
    nextJob.status = 'PROCESSING';
    _notifyListeners();

    try {
      final result = await _api.generatePartialReport(
        nextJob.projectId,
        nextJob.roomId,
      );

      if (result != null) {
        nextJob.status = 'COMPLETE';
        nextJob.result = result;
        nextJob.completedAt = DateTime.now();
      } else {
        nextJob.status = 'ERROR';
        nextJob.errorMessage = 'Server returned null';
      }
    } catch (e) {
      nextJob.status = 'ERROR';
      nextJob.errorMessage = e.toString();
    }

    _isProcessing = false;
    _notifyListeners();

    // Process next in queue
    _processNext();
  }

  void dispose() {
    _statusController.close();
  }
}
