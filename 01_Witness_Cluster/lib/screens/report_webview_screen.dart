import 'package:flutter/material.dart';
import 'package:webview_flutter/webview_flutter.dart';
import 'package:google_fonts/google_fonts.dart';

class ReportWebViewScreen extends StatefulWidget {
  final String projectId;
  final String backendBaseUrl; // e.g., http://192.168.13.49:8000/api

  const ReportWebViewScreen({
    super.key,
    required this.projectId,
    required this.backendBaseUrl,
  });

  @override
  State<ReportWebViewScreen> createState() => _ReportWebViewScreenState();
}

class _ReportWebViewScreenState extends State<ReportWebViewScreen> {
  late final WebViewController _controller;
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();

    // Direct PDF URL from the backend
    final pdfUrl =
        '${widget.backendBaseUrl}/projects/${widget.projectId}/report/pdf';

    // Wrap in Google Docs Viewer for reliable in-app PDF rendering
    final viewerUrl =
        'https://docs.google.com/viewer?url=${Uri.encodeComponent(pdfUrl)}&embedded=true';

    print("Loading PDF Viewer: $viewerUrl");
    print("Direct PDF URL: $pdfUrl");

    _controller = WebViewController()
      ..setJavaScriptMode(JavaScriptMode.unrestricted)
      ..setBackgroundColor(const Color(0xFF05080D))
      ..setNavigationDelegate(
        NavigationDelegate(
          onProgress: (int progress) {},
          onPageStarted: (String url) {},
          onPageFinished: (String url) {
            setState(() => _isLoading = false);
          },
          onWebResourceError: (WebResourceError error) {
            print("WebView Error: ${error.description}");
            // If Google Docs fails (e.g. local network), fall back to direct URL
            if (error.errorType == WebResourceErrorType.hostLookup ||
                error.errorType == WebResourceErrorType.connect) {
              _controller.loadRequest(Uri.parse(pdfUrl));
            }
          },
        ),
      )
      ..loadRequest(Uri.parse(viewerUrl));
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF05080D),
      appBar: AppBar(
        backgroundColor: const Color(0xFF0F4A8A),
        title: Text(
          'RICS FINAL REPORT',
          style: GoogleFonts.outfit(
            color: Colors.white,
            fontWeight: FontWeight.bold,
            letterSpacing: 1.5,
          ),
        ),
        centerTitle: true,
        iconTheme: const IconThemeData(color: Colors.white),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () => _controller.reload(),
            tooltip: 'Reload',
          ),
          IconButton(
            icon: const Icon(Icons.open_in_browser),
            onPressed: () {
              final pdfUrl =
                  '${widget.backendBaseUrl}/projects/${widget.projectId}/report/pdf';
              _controller.loadRequest(Uri.parse(pdfUrl));
            },
            tooltip: 'Direct PDF',
          ),
        ],
      ),
      body: Stack(
        children: [
          WebViewWidget(controller: _controller),
          if (_isLoading)
            Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  const CircularProgressIndicator(color: Color(0xFFFFD700)),
                  const SizedBox(height: 16),
                  Text(
                    'Loading RICS Report...',
                    style: GoogleFonts.spaceMono(
                      color: Colors.white54,
                      fontSize: 12,
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
