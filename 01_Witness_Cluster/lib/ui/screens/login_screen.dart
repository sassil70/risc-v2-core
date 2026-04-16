import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:glassmorphism/glassmorphism.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:flutter_animate/flutter_animate.dart'; // Using the requested lib
import 'package:witness_v2/core/services/auth_service.dart';

class LoginScreen extends ConsumerStatefulWidget {
  final VoidCallback onLoginSuccess;
  const LoginScreen({super.key, required this.onLoginSuccess});

  @override
  ConsumerState<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends ConsumerState<LoginScreen> {
  final _usernameController = TextEditingController();
  final _passwordController = TextEditingController();
  bool _isLoading = false;
  String? _error;

  Future<void> _handleLogin() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });

    final auth = ref.read(authServiceProvider);
    try {
      final user = await auth.login(
        _usernameController.text.trim(),
        _passwordController.text,
      );

      ref.read(userProvider.notifier).state = user;

      if (mounted) {
        widget.onLoginSuccess();
      }
    } catch (e) {
      if (mounted) {
        setState(() => _error = e.toString().replaceAll("Exception: ", ""));
      }
    } finally {
      if (mounted) {
        setState(() => _isLoading = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    // Theme Accents
    const neonBlue = Color(0xFF00E5FF);
    const dangerRed = Color(0xFFFF2E63);

    return Scaffold(
      backgroundColor: Colors.black, // Fallback
      body: Stack(
        children: [
          // 1. Background Image with subtle zoom animation
          Positioned.fill(
              child: Image.network(
            'https://images.unsplash.com/photo-1550751827-4bd374c3f58b?q=80&w=2670&auto=format&fit=crop', // Cyberpunk City
            fit: BoxFit.cover,
            loadingBuilder: (context, child, loadingProgress) {
              if (loadingProgress == null) return child;
              return Container(color: const Color(0xFF0A0E17));
            },
          )
                  .animate(
                      onPlay: (controller) => controller.repeat(reverse: true))
                  .scale(
                      duration: 20.seconds,
                      begin: const Offset(1.0, 1.0),
                      end: const Offset(1.1, 1.1)) // Subtle Breathe
              ),

          // 2. Heavy Dark Overlay Gradient
          Positioned.fill(
            child: Container(
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  begin: Alignment.topCenter,
                  end: Alignment.bottomCenter,
                  colors: [
                    const Color(0xFF050505).withOpacity(0.6),
                    const Color(0xFF0A0E17).withOpacity(0.85),
                    const Color(0xFF000000).withOpacity(0.95),
                  ],
                ),
              ),
            ),
          ),

          // 3. Grid Pattern Overlay (Optional Sci-Fi Touch)
          Positioned.fill(
            child: Opacity(
              opacity: 0.05,
              child: Image.network(
                  "https://www.transparenttextures.com/patterns/graphy.png",
                  repeat: ImageRepeat.repeat),
            ),
          ),

          // 4. Content Center
          Center(
            child: SingleChildScrollView(
              padding: const EdgeInsets.symmetric(horizontal: 24),
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  // Logo / Icon
                  Container(
                    padding: const EdgeInsets.all(20),
                    decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        border: Border.all(
                            color: neonBlue.withOpacity(0.3), width: 1),
                        color: neonBlue.withOpacity(0.05),
                        boxShadow: [
                          BoxShadow(
                              color: neonBlue.withOpacity(0.2),
                              blurRadius: 20,
                              spreadRadius: 1)
                        ]),
                    child: const Icon(Icons.security, size: 48, color: neonBlue),
                  ).animate().fadeIn(duration: 800.ms).scale(),

                  const SizedBox(height: 32),

                  // Text Header
                  Column(
                    children: [
                      Text(
                        "RISC V2.0",
                        style: GoogleFonts.outfit(
                          fontSize: 42,
                          fontWeight: FontWeight.w800,
                          color: Colors.white,
                          letterSpacing: 2,
                        ),
                      )
                          .animate()
                          .fadeIn(delay: 200.ms)
                          .moveY(begin: 20, end: 0),
                      const SizedBox(height: 8),
                      Text(
                        "FORENSIC INTELLIGENCE UNIT",
                        style: GoogleFonts.spaceMono(
                            fontSize: 12,
                            color: neonBlue.withOpacity(0.8),
                            letterSpacing: 3,
                            fontWeight: FontWeight.w600),
                      ).animate().fadeIn(delay: 400.ms),
                    ],
                  ),

                  const SizedBox(height: 50),

                  // Glass Form Card
                  GlassmorphicContainer(
                    width: double.infinity,
                    height: 460,
                    borderRadius: 24,
                    blur: 20,
                    alignment: Alignment.center,
                    border: 1,
                    linearGradient: LinearGradient(
                      begin: Alignment.topLeft,
                      end: Alignment.bottomRight,
                      colors: [
                        Colors.white.withOpacity(0.08),
                        Colors.white.withOpacity(0.02),
                      ],
                    ),
                    borderGradient: LinearGradient(
                      begin: Alignment.topLeft,
                      end: Alignment.bottomRight,
                      colors: [
                        neonBlue.withOpacity(0.3),
                        Colors.transparent,
                      ],
                    ),
                    child: Padding(
                      padding: const EdgeInsets.all(32.0),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          // Username
                          _buildLabel("OPERATOR ID")
                              .animate()
                              .fadeIn(delay: 600.ms),
                          const SizedBox(height: 8),
                          _buildInput(
                                  controller: _usernameController,
                                  icon: Icons.fingerprint,
                                  hint: "Identity Signature")
                              .animate()
                              .fadeIn(delay: 700.ms),

                          const SizedBox(height: 24),

                          // Password
                          _buildLabel("ACCESS KEY")
                              .animate()
                              .fadeIn(delay: 800.ms),
                          const SizedBox(height: 8),
                          _buildInput(
                                  controller: _passwordController,
                                  icon: Icons.vpn_key_outlined,
                                  hint: "Encrypted Token",
                                  isPwd: true)
                              .animate()
                              .fadeIn(delay: 900.ms),

                          const SizedBox(height: 32),

                          // Error
                          if (_error != null)
                            Container(
                                width: double.infinity,
                                padding: const EdgeInsets.all(12),
                                margin: const EdgeInsets.only(bottom: 16),
                                decoration: BoxDecoration(
                                    color: dangerRed.withOpacity(0.1),
                                    borderRadius: BorderRadius.circular(8),
                                    border: Border.all(
                                        color: dangerRed.withOpacity(0.3))),
                                child: Row(
                                  children: [
                                    const Icon(Icons.warning_amber_rounded,
                                        color: dangerRed, size: 18),
                                    const SizedBox(width: 8),
                                    Expanded(
                                        child: Text(_error!,
                                            style: const TextStyle(
                                                color: dangerRed,
                                                fontSize: 12,
                                                fontFamily: 'SpaceMono'))),
                                  ],
                                )).animate().shake(),

                          const SizedBox(height: 8),

                          // Button
                          SizedBox(
                            width: double.infinity,
                            height: 56,
                            child: ElevatedButton(
                              onPressed: _isLoading ? null : _handleLogin,
                              style: ElevatedButton.styleFrom(
                                backgroundColor: neonBlue,
                                foregroundColor: Colors.black,
                                elevation: 0,
                                shadowColor: neonBlue.withOpacity(0.5),
                                shape: RoundedRectangleBorder(
                                    borderRadius: BorderRadius.circular(12)),
                              ),
                              child: _isLoading
                                  ? const SizedBox(
                                      height: 24,
                                      width: 24,
                                      child: CircularProgressIndicator(
                                          color: Colors.black, strokeWidth: 2))
                                  : Text(
                                      "INITIATE LINK",
                                      style: GoogleFonts.outfit(
                                        fontSize: 16,
                                        fontWeight: FontWeight.bold,
                                        letterSpacing: 2,
                                      ),
                                    ),
                            ),
                          )
                              .animate()
                              .fadeIn(delay: 1000.ms)
                              .shimmer(delay: 2000.ms, duration: 1500.ms),
                        ],
                      ),
                    ),
                  ),

                  const SizedBox(height: 32),

                  Text(
                    "SECURE CONNECTION :: ENCRYPTED [SHA-256]",
                    style: TextStyle(
                        color: Colors.white.withOpacity(0.2),
                        fontSize: 9,
                        fontFamily: 'SpaceMono'),
                  ).animate().fadeIn(delay: 1500.ms),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildLabel(String text) {
    return Text(
      text,
      style: GoogleFonts.spaceMono(
        fontSize: 10,
        color: Colors.white54,
        fontWeight: FontWeight.bold,
        letterSpacing: 1.5,
      ),
    );
  }

  Widget _buildInput(
      {required TextEditingController controller,
      required IconData icon,
      required String hint,
      bool isPwd = false}) {
    return Container(
      decoration: BoxDecoration(
        color: Colors.transparent, // Glass handled by parent or transparent
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.white.withOpacity(0.1)),
      ),
      child: TextField(
        controller: controller,
        obscureText: isPwd,
        style: GoogleFonts.spaceMono(color: Colors.white, fontSize: 14),
        cursorColor: const Color(0xFF00E5FF),
        decoration: InputDecoration(
          prefixIcon: Icon(icon, color: Colors.white38, size: 20),
          hintText: hint,
          hintStyle: TextStyle(
              color: Colors.white.withOpacity(0.2),
              fontFamily: 'SpaceMono',
              fontSize: 12),
          filled: true,
          fillColor: Colors.black.withOpacity(0.2),
          border: OutlineInputBorder(
              borderRadius: BorderRadius.circular(12),
              borderSide: BorderSide.none),
          contentPadding:
              const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
        ),
      ),
    );
  }
}
