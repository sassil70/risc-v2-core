
import 'package:camera/camera.dart';
import 'package:record/record.dart';

/// RICS-V2 Hardware Abstraction Layer
/// Enforces "High-End" constraints: Max Resolution, Max Bitrate, Max Stability.
class HardwareService {
  CameraController? _cameraController;
  final AudioRecorder _audioRecorder = AudioRecorder();

  // Singleton
  static final HardwareService _instance = HardwareService._internal();
  factory HardwareService() => _instance;
  HardwareService._internal();

  /// Initializes the Camera with MAX Resolution (Ultra High Definition)
  /// Returns the initialized controller.
  Future<CameraController> initCamera() async {
    // 1. Get available cameras
    final cameras = await availableCameras();
    if (cameras.isEmpty) throw Exception("No Camera Found on Device");

    // 2. Select Ultra-Wide if available, else Main (Back)
    // For now, we stick to the first available back camera for stability
    final camera = cameras.firstWhere(
        (c) => c.lensDirection == CameraLensDirection.back,
        orElse: () => cameras.first
    );

    // 3. Configure for MAX Precision
    _cameraController = CameraController(
      camera,
      ResolutionPreset.max, // <--- USER REQUEST: FORCE MAX
      enableAudio: false, // Audio handled by separate high-fidelity recorder
      imageFormatGroup: ImageFormatGroup.jpeg, // Standardization
    );

    await _cameraController!.initialize();
    
    // 4. Lock Autofocus to ensure sharp macro details if needed, 
    // or set to auto (previously continuousVideo might be deprecated/renamed)
    // We want the most stable focus.
    await _cameraController!.setFocusMode(FocusMode.auto);
    
    // 5. Turn off Flash by default to avoid glare on glossy surfaces
    await _cameraController!.setFlashMode(FlashMode.off);

    return _cameraController!;
  }

  /// Starts High-Fidelity Audio Recording (AAC 128kbps+)
  Future<void> startRecording(String path) async {
    // RICS Requirement: Clear voice for transcription
    // We use AAC-LC at 128kbps which is excellent for voice.
    const config = RecordConfig(
      encoder: AudioEncoder.aacLc,
      bitRate: 128000, 
      sampleRate: 44100,
    );
    
    await _audioRecorder.start(config, path: path);
  }

  Future<void> stopRecording() async {
    await _audioRecorder.stop();
  }

  void dispose() {
    _cameraController?.dispose();
    _audioRecorder.dispose();
  }
}
