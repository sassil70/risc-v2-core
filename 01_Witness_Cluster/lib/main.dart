import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:flex_color_scheme/flex_color_scheme.dart';
import 'core/services/auth_service.dart';
import 'ui/screens/dashboard_screen.dart';
import 'ui/screens/login_screen.dart';

void main() {
  runApp(const ProviderScope(child: WitnessApp()));
}

class WitnessApp extends StatelessWidget {
  const WitnessApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'RISC Witness V2',
      debugShowCheckedModeBanner: false,
      // Da Vinci Architect Theme (Midnight & Gold)
      theme:
          FlexThemeData.dark(
            scheme: FlexScheme.bahamaBlue, // Deep Blue Base
            surfaceMode: FlexSurfaceMode.levelSurfacesLowScaffold,
            blendLevel: 20, // High blend for integrated look
            subThemesData: const FlexSubThemesData(
              blendOnLevel: 20,
              blendOnColors: true,
              useTextTheme: true,
              useM2StyleDividerInM3: true,
              alignedDropdown: true,
              useInputDecoratorThemeInDialogs: true,
              inputDecoratorBorderType: FlexInputBorderType.underline,
              fabUseShape: true,
              fabAlwaysCircular: true,
              chipSchemeColor: SchemeColor.tertiary, // Gold Accents
            ),
            keyColors: const FlexKeyColors(
              useSecondary: true,
              useTertiary: true,
              keepPrimary: true,
            ),
            visualDensity: FlexColorScheme.comfortablePlatformDensity,
            useMaterial3: true,
            swapLegacyOnMaterial3: true,
            fontFamily: GoogleFonts.outfit().fontFamily,
          ).copyWith(
            // Manual Overrides for "The 4" Gold Accent
            colorScheme: const ColorScheme.dark(
              primary: Color(0xFF1E88E5), // Architect Blue
              secondary: Color(0xFFFFD700), // Da Vinci Gold
              surface: Color(0xFF0B1019), // Void
              onSurface: Colors.white,
            ),
          ),
      themeMode: ThemeMode.dark, // Force Dark Mode
      // Check Auth on Startup
      home: const AuthCheck(),
      routes: {
        '/login': (context) => LoginScreen(
          onLoginSuccess: () {
            Navigator.of(context).pushReplacementNamed('/dashboard');
          },
        ),
        '/dashboard': (context) => const DashboardScreen(),
      },
    );
  }
}

class AuthCheck extends ConsumerStatefulWidget {
  const AuthCheck({super.key});

  @override
  ConsumerState<AuthCheck> createState() => _AuthCheckState();
}

class _AuthCheckState extends ConsumerState<AuthCheck> {
  @override
  void initState() {
    super.initState();
    _checkAuth();
  }

  Future<void> _checkAuth() async {
    // Artificial delay to show splash/loading if needed
    // await Future.delayed(const Duration(seconds: 1));

    final auth = ref.read(authServiceProvider);
    final user = await auth.tryAutoLogin();

    if (mounted) {
      if (user != null) {
        ref.read(userProvider.notifier).state = user;
        Navigator.of(context).pushReplacementNamed('/dashboard');
      } else {
        Navigator.of(context).pushReplacementNamed('/login');
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return const Scaffold(
      backgroundColor: Colors.black,
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            CircularProgressIndicator(color: Colors.white),
            SizedBox(height: 16),
            Text(
              "Connecting to RISC V2...",
              style: TextStyle(color: Colors.white70),
            ),
          ],
        ),
      ),
    );
  }
}
