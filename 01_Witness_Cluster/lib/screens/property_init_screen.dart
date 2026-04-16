import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:flutter_animate/flutter_animate.dart';
import '../services/api_service.dart';
import '../core/services/auth_service.dart';
import 'floor_plan_recorder.dart';

class PropertyInitScreen extends StatefulWidget {
  final Map<String, dynamic>? propertyData; // Passed when in Edit Mode

  const PropertyInitScreen({super.key, this.propertyData});

  @override
  State<PropertyInitScreen> createState() => _PropertyInitScreenState();
}

class _PropertyInitScreenState extends State<PropertyInitScreen> {
  final _formKey = GlobalKey<FormState>();
  final ApiService _api = ApiService();
  final AuthService _auth = AuthService();
  final PageController _pageController = PageController();

  int _currentStep = 0;
  bool _isLoading = false;
  List<dynamic> _addressSuggestions = [];

  // Controllers
  final TextEditingController _postcodeController = TextEditingController();
  final TextEditingController _numberController = TextEditingController();
  final TextEditingController _streetController = TextEditingController();
  final TextEditingController _cityController = TextEditingController();

  // State - Architecture DNA
  String _selectedType = 'Detached';
  String _selectedTenure = 'Freehold';
  int _numberOfFloors = 2;
  String _occupancyStatus = 'Occupied';
  String _constructionAge = 'Post-2000';

  // State - Environment DNA
  String _selectedWeather = 'Dry/Sunny';
  final Map<String, bool> _services = {
    'Gas Supply': true,
    'Electricity Supply': true,
    'Mains Water': true,
    'Mains Drainage': true,
  };

  bool get _isEditMode => widget.propertyData != null;

  @override
  void initState() {
    super.initState();
    if (_isEditMode) {
      _prefillData(widget.propertyData!);
    }
  }

  void _prefillData(Map<String, dynamic> data) {
    if (data['metadata'] != null) {
      final meta = data['metadata'];
      if (meta['address'] != null) {
        final addr = meta['address'];
        _postcodeController.text = addr['postcode'] ?? '';
        _numberController.text = addr['number'] ?? '';
        _streetController.text = addr['street'] ?? '';
        _cityController.text = addr['city'] ?? '';
      }
      _selectedType = meta['property_type'] ?? 'Detached';
      _selectedTenure = meta['tenure'] ?? 'Freehold';
      _numberOfFloors = meta['number_of_floors'] ?? 2;
      _occupancyStatus = meta['occupancy_status'] ?? 'Occupied';
      _constructionAge = meta['construction_age'] ?? 'Post-2000';
      _selectedWeather = meta['weather_conditions'] ?? 'Dry/Sunny';

      if (meta['utilities_services'] != null) {
        final srvs = meta['utilities_services'] as Map<String, dynamic>;
        _services.forEach((key, _) {
          if (srvs.containsKey(key)) _services[key] = srvs[key] == true;
        });
      }
    }
  }

  @override
  void dispose() {
    _pageController.dispose();
    _postcodeController.dispose();
    _numberController.dispose();
    _streetController.dispose();
    _cityController.dispose();
    super.dispose();
  }

  void _lookupPostcode() async {
    if (_postcodeController.text.isEmpty) return;
    setState(() => _isLoading = true);
    try {
      final res = await _api.lookupPostcode(_postcodeController.text);
      if (mounted) setState(() => _addressSuggestions = res['addresses'] ?? []);
    } catch (e) {
      // Handle silently
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  void _selectAddress(Map<String, dynamic> addr) {
    if (mounted) {
      setState(() {
        _streetController.text = addr['street'] ?? '';
        _cityController.text = addr['city'] ?? '';
        _addressSuggestions.clear();
      });
    }
  }

  void _nextStep() {
    if (_currentStep == 0) {
      if (_postcodeController.text.isEmpty || _streetController.text.isEmpty) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text("Postcode and Street are required")),
        );
        return;
      }
    }

    if (_currentStep < 2) {
      _pageController.nextPage(duration: 400.ms, curve: Curves.easeInOut);
      setState(() => _currentStep++);
    } else {
      _submit();
    }
  }

  void _prevStep() {
    if (_currentStep > 0) {
      _pageController.previousPage(duration: 400.ms, curve: Curves.easeInOut);
      setState(() => _currentStep--);
    } else {
      Navigator.pop(context);
    }
  }

  void _submit() async {
    if (!_formKey.currentState!.validate()) return;

    final timestampId = DateTime.now().millisecondsSinceEpoch
        .toString()
        .substring(7);
    final refStr =
        "${_postcodeController.text} ${_numberController.text} - $timestampId"
            .trim();
    final clientStr = "${_streetController.text}, ${_cityController.text}"
        .trim();

    final Map<String, dynamic> metadata = {
      "address": {
        "postcode": _postcodeController.text,
        "street": _streetController.text,
        "city": _cityController.text,
        "number": _numberController.text,
        "full_address":
            "${_numberController.text} ${_streetController.text}, ${_cityController.text}",
      },
      "property_type": _selectedType,
      "tenure": _selectedTenure,
      "number_of_floors": _numberOfFloors,
      "occupancy_status": _occupancyStatus,
      "construction_age": _constructionAge,
      "weather_conditions": _selectedWeather,
      "utilities_services": _services,
    };

    setState(() => _isLoading = true);
    try {
      if (_isEditMode) {
        final updated = await _api.updateProject(
          widget.propertyData!['id'],
          refStr,
          clientStr,
          metadata: metadata,
        );
        if (updated != null && mounted) {
          Navigator.pop(context, true);
        } else {
          if (mounted) {
            ScaffoldMessenger.of(
              context,
            ).showSnackBar(const SnackBar(content: Text("Failed to Update")));
          }
        }
      } else {
        final newProject = await _api.createProject(
          refStr,
          clientStr,
          metadata: metadata,
        );

        // Offline-resilient: If API fails, create project locally
        final projectData = newProject ?? {
          'id': 'local_${DateTime.now().millisecondsSinceEpoch}',
          'reference_number': refStr,
          'client_name': clientStr,
        };

        if (mounted) {
          // Explicit Data Passing: Get Auth and Create Session
          final user = await _auth.tryAutoLogin();
          final userId = user?['id'] ?? '00000000-0000-0000-0000-000000000000'; // Fixed Postgres DataError

          Map<String, dynamic>? session;
          try {
            session = await _api.createSession(
              projectId: projectData['id'],
              surveyorId: userId,
              title: refStr,
            );
          } catch (_) {
            // Offline fallback: create local session
            session = {
              'id': 'session_${DateTime.now().millisecondsSinceEpoch}',
            };
          }

          metadata['property_id'] = projectData['id'];

          if (mounted) {
            Navigator.pushReplacement(
              context,
              MaterialPageRoute(
                builder: (_) => FloorPlanRecorder(
                  initialData: metadata,
                  sessionId: session!['id'],
                  userId: userId,
                ),
              ),
            );
          }
        }
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text("Error: $e")));
      }
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    const midnight = Color(0xFF05080D);
    const gold = Color(0xFFFFD700);

    return Scaffold(
      backgroundColor: midnight,
      extendBodyBehindAppBar: true,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back, color: Colors.white),
          onPressed: _prevStep,
        ),
        title: Text(
          _isEditMode ? "EDIT PROPERTY" : "MISSION LAUNCHPAD",
          style: GoogleFonts.outfit(
            color: Colors.white,
            fontWeight: FontWeight.bold,
            letterSpacing: 1,
            fontSize: 18,
          ),
        ),
        centerTitle: true,
      ),
      body: Stack(
        children: [
          // Background Pattern
          Positioned.fill(
            child: Opacity(
              opacity: 0.05,
              child: Image.network(
                "https://www.transparenttextures.com/patterns/blueprint.png",
                repeat: ImageRepeat.repeat,
              ),
            ),
          ),
          Positioned(
            top: -100,
            left: -100,
            child: Container(
              width: 300,
              height: 300,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: gold.withOpacity(0.05),
                boxShadow: [
                  BoxShadow(
                    color: gold.withOpacity(0.05),
                    blurRadius: 100,
                    spreadRadius: 50,
                  ),
                ],
              ),
            ),
          ),

          SafeArea(
            child: Column(
              children: [
                // Progress Bar
                Padding(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 32,
                    vertical: 16,
                  ),
                  child: Row(
                    children: [
                      _buildStepDot(0, "Location", Icons.pin_drop),
                      _buildStepLine(0),
                      _buildStepDot(1, "DNA", Icons.corporate_fare),
                      _buildStepLine(1),
                      _buildStepDot(2, "Env", Icons.cloud),
                    ],
                  ),
                ),
                const SizedBox(height: 16),

                Expanded(
                  child: _isLoading
                      ? const Center(child: CircularProgressIndicator(color: gold))
                      : Form(
                          key: _formKey,
                          child: PageView(
                            controller: _pageController,
                            physics:
                                const NeverScrollableScrollPhysics(), // Only buttons advance
                            children: [
                              _buildStep1Location(),
                              _buildStep2Architecture(),
                              _buildStep3Environment(),
                            ],
                          ),
                        ),
                ),

                // Action Buttons
                Padding(
                  padding: const EdgeInsets.all(24),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      TextButton(
                        onPressed: _prevStep,
                        child: Text(
                          _currentStep == 0 ? "CANCEL" : "BACK",
                          style: GoogleFonts.spaceMono(
                            color: Colors.white54,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ),
                      ElevatedButton(
                        onPressed: _isLoading ? null : _nextStep,
                        style: ElevatedButton.styleFrom(
                          backgroundColor: gold,
                          foregroundColor: Colors.black,
                          padding: const EdgeInsets.symmetric(
                            horizontal: 32,
                            vertical: 16,
                          ),
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(30),
                          ),
                          elevation: 5,
                          shadowColor: gold.withOpacity(0.5),
                        ),
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Text(
                              _currentStep == 2
                                  ? (_isEditMode ? "SAVE" : "LAUNCH")
                                  : "NEXT",
                              style: GoogleFonts.outfit(
                                fontWeight: FontWeight.bold,
                                fontSize: 16,
                              ),
                            ),
                            const SizedBox(width: 8),
                            Icon(
                              _currentStep == 2
                                  ? Icons.rocket_launch
                                  : Icons.arrow_forward_rounded,
                              size: 20,
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  // --- UI Builders ---

  Expanded _buildStepLine(int index) {
    return Expanded(
      child: Container(
        height: 2,
        color: _currentStep > index ? const Color(0xFFFFD700) : Colors.white10,
      ),
    );
  }

  Widget _buildStepDot(int index, String label, IconData icon) {
    bool active = _currentStep >= index;
    bool current = _currentStep == index;
    return Column(
          children: [
            Container(
              width: 40,
              height: 40,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: active
                    ? const Color(0xFFFFD700)
                    : Colors.white.withOpacity(0.05),
                border: Border.all(
                  color: current ? Colors.white : Colors.transparent,
                  width: 2,
                ),
              ),
              child: Icon(
                icon,
                color: active ? Colors.black : Colors.white38,
                size: 20,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              label,
              style: GoogleFonts.spaceMono(
                fontSize: 10,
                color: active ? Colors.white : Colors.white38,
                fontWeight: current ? FontWeight.bold : FontWeight.normal,
              ),
            ),
          ],
        )
        .animate(target: current ? 1 : 0)
        .scale(begin: const Offset(1, 1), end: const Offset(1.1, 1.1));
  }

  Widget _buildStep1Location() {
    return ListView(
      padding: const EdgeInsets.symmetric(horizontal: 24),
      children: [
        Text(
          "STEP 1: LOCATION",
          style: GoogleFonts.spaceMono(
            color: const Color(0xFFFFD700),
            fontSize: 12,
          ),
        ),
        const SizedBox(height: 8),
        Text(
          "Where is the target property?",
          style: GoogleFonts.outfit(
            color: Colors.white,
            fontSize: 24,
            fontWeight: FontWeight.bold,
          ),
        ),
        const SizedBox(height: 16),
        Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: const Color(0xFFFFD700).withOpacity(0.05),
            border: Border.all(color: const Color(0xFFFFD700).withOpacity(0.2)),
            borderRadius: BorderRadius.circular(12),
          ),
          child: Row(
            children: [
              const Icon(Icons.gavel, color: Color(0xFFFFD700)),
              const SizedBox(width: 16),
              Expanded(
                child: Text(
                  "RICS Necessity: Identifying the specific address anchors your legal liability securely to this property alone.",
                  style: GoogleFonts.spaceMono(
                    fontSize: 10,
                    color: Colors.white70,
                  ),
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 32),

        Row(
          children: [
            Expanded(
              flex: 2,
              child: _buildTextField(
                _postcodeController,
                "Postcode",
                Icons.location_on,
              ),
            ),
            const SizedBox(width: 16),
            Container(
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: Colors.white.withOpacity(0.05),
              ),
              child: IconButton(
                icon: const Icon(Icons.search, color: Color(0xFFFFD700)),
                onPressed: _lookupPostcode,
              ),
            ),
          ],
        ),
        if (_addressSuggestions.isNotEmpty)
          Container(
            margin: const EdgeInsets.only(top: 8),
            decoration: BoxDecoration(
              color: Colors.white.withOpacity(0.1),
              borderRadius: BorderRadius.circular(12),
            ),
            child: Column(
              children: _addressSuggestions
                  .map(
                    (addr) => ListTile(
                      title: Text(
                        "${addr['street']}, ${addr['city']}",
                        style: const TextStyle(color: Colors.white),
                      ),
                      onTap: () => _selectAddress(addr),
                    ),
                  )
                  .toList(),
            ),
          ),
        const SizedBox(height: 24),
        Row(
          children: [
            Expanded(
              flex: 1,
              child: _buildTextField(_numberController, "No.", Icons.numbers),
            ),
            const SizedBox(width: 16),
            Expanded(
              flex: 3,
              child: _buildTextField(
                _streetController,
                "Street",
                Icons.add_road,
              ),
            ),
          ],
        ),
        const SizedBox(height: 24),
        _buildTextField(_cityController, "City/Town", Icons.location_city),
      ],
    ).animate().fadeIn().slideX(begin: 0.1, end: 0);
  }

  Widget _buildStep2Architecture() {
    return ListView(
      padding: const EdgeInsets.symmetric(horizontal: 24),
      children: [
        Text(
          "STEP 2: RICS DNA",
          style: GoogleFonts.spaceMono(
            color: const Color(0xFFFFD700),
            fontSize: 12,
          ),
        ),
        const SizedBox(height: 8),
        Text(
          "Define the architectural profile",
          style: GoogleFonts.outfit(
            color: Colors.white,
            fontSize: 24,
            fontWeight: FontWeight.bold,
          ),
        ),
        const SizedBox(height: 16),
        Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: const Color(0xFFFFD700).withOpacity(0.05),
            border: Border.all(color: const Color(0xFFFFD700).withOpacity(0.2)),
            borderRadius: BorderRadius.circular(12),
          ),
          child: Row(
            children: [
              const Icon(Icons.architecture, color: Color(0xFFFFD700)),
              const SizedBox(width: 16),
              Expanded(
                child: Text(
                  "RICS Necessity: Brain AI uses this DNA to accurately weigh the severity of defects (Condition Ratings).",
                  style: GoogleFonts.spaceMono(
                    fontSize: 10,
                    color: Colors.white70,
                  ),
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 32),

        Text(
          "PROPERTY TYPE",
          style: GoogleFonts.spaceMono(fontSize: 10, color: Colors.white54),
        ),
        const SizedBox(height: 8),
        _buildDropdown(
          [
            'Detached',
            'Semi-Detached',
            'Terraced',
            'Flat/Maisonette',
            'Bungalow',
            'Commercial',
          ],
          _selectedType,
          (val) => setState(() => _selectedType = val!),
        ),

        const SizedBox(height: 24),
        Text(
          "CONSTRUCTION AGE (APPROX)",
          style: GoogleFonts.spaceMono(fontSize: 10, color: Colors.white54),
        ),
        const SizedBox(height: 8),
        _buildDropdown(
          ['Pre-1914', '1919-1945', '1946-1979', '1980-1999', 'Post-2000'],
          _constructionAge,
          (val) => setState(() => _constructionAge = val!),
        ),

        const SizedBox(height: 24),
        Row(
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    "FLOORS",
                    style: GoogleFonts.spaceMono(
                      fontSize: 10,
                      color: Colors.white54,
                    ),
                  ),
                  const SizedBox(height: 8),
                  _buildDropdown(
                    ['1', '2', '3', '4+'],
                    _numberOfFloors.toString(),
                    (val) => setState(() => _numberOfFloors = int.parse(val!)),
                  ),
                ],
              ),
            ),
            const SizedBox(width: 16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    "TENURE",
                    style: GoogleFonts.spaceMono(
                      fontSize: 10,
                      color: Colors.white54,
                    ),
                  ),
                  const SizedBox(height: 8),
                  _buildDropdown(
                    ['Freehold', 'Leasehold'],
                    _selectedTenure,
                    (val) => setState(() => _selectedTenure = val!),
                  ),
                ],
              ),
            ),
          ],
        ),
        const SizedBox(height: 24),
        Text(
          "OCCUPANCY STATUS",
          style: GoogleFonts.spaceMono(fontSize: 10, color: Colors.white54),
        ),
        const SizedBox(height: 8),
        _buildDropdown(
          ['Occupied', 'Vacant', 'Under Construction'],
          _occupancyStatus,
          (val) => setState(() => _occupancyStatus = val!),
        ),
      ],
    ).animate().fadeIn().slideX(begin: 0.1, end: 0);
  }

  Widget _buildStep3Environment() {
    return ListView(
      padding: const EdgeInsets.symmetric(horizontal: 24),
      children: [
        Text(
          "STEP 3: ENVIRONMENT & SERVICES",
          style: GoogleFonts.spaceMono(
            color: const Color(0xFFFFD700),
            fontSize: 12,
          ),
        ),
        const SizedBox(height: 8),
        Text(
          "Conditions during inspection",
          style: GoogleFonts.outfit(
            color: Colors.white,
            fontSize: 24,
            fontWeight: FontWeight.bold,
          ),
        ),
        const SizedBox(height: 16),
        Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: const Color(0xFFFFD700).withOpacity(0.05),
            border: Border.all(color: const Color(0xFFFFD700).withOpacity(0.2)),
            borderRadius: BorderRadius.circular(12),
          ),
          child: Row(
            children: [
              const Icon(Icons.shield, color: Color(0xFFFFD700)),
              const SizedBox(width: 16),
              Expanded(
                child: Text(
                  "RICS Necessity: Weather data protects you legally if dormant leaks aren't visible on a dry day.",
                  style: GoogleFonts.spaceMono(
                    fontSize: 10,
                    color: Colors.white70,
                  ),
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 32),

        Text(
          "WEATHER CONDITIONS",
          style: GoogleFonts.spaceMono(fontSize: 10, color: Colors.white54),
        ),
        const SizedBox(height: 8),
        _buildDropdown(
          ['Dry/Sunny', 'Overcast', 'Raining', 'Snowing'],
          _selectedWeather,
          (val) => setState(() => _selectedWeather = val!),
        ),

        const SizedBox(height: 40),
        Text(
          "CONNECTED UTILITIES & SERVICES",
          style: GoogleFonts.spaceMono(fontSize: 10, color: Colors.white54),
        ),
        const SizedBox(height: 16),

        ..._services.keys.map(
          (key) => CheckboxListTile(
            title: Text(key, style: GoogleFonts.outfit(color: Colors.white)),
            value: _services[key],
            activeColor: const Color(0xFFFFD700),
            checkColor: Colors.black,
            tileColor: Colors.white.withOpacity(0.02),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(12),
            ),
            contentPadding: const EdgeInsets.symmetric(
              horizontal: 16,
              vertical: 4,
            ),
            onChanged: (val) {
              setState(() {
                _services[key] = val!;
              });
            },
          ),
        ),

        const SizedBox(height: 40),
        Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: const Color(0xFFFFD700).withOpacity(0.05),
            border: Border.all(color: const Color(0xFFFFD700).withOpacity(0.2)),
            borderRadius: BorderRadius.circular(12),
          ),
          child: Row(
            children: [
              const Icon(Icons.info_outline, color: Color(0xFFFFD700)),
              const SizedBox(width: 16),
              Expanded(
                child: Text(
                  "This data directly populates Category A & F of the final RICS report.",
                  style: GoogleFonts.spaceMono(
                    fontSize: 10,
                    color: Colors.white70,
                  ),
                ),
              ),
            ],
          ),
        ),
      ],
    ).animate().fadeIn().slideX(begin: 0.1, end: 0);
  }

  Widget _buildTextField(
    TextEditingController controller,
    String hint,
    IconData icon,
  ) {
    return TextFormField(
      controller: controller,
      style: GoogleFonts.spaceMono(color: Colors.white),
      decoration: InputDecoration(
        hintText: hint,
        hintStyle: GoogleFonts.spaceMono(color: Colors.white24),
        prefixIcon: Icon(icon, color: Colors.white30),
        filled: true,
        fillColor: Colors.white.withOpacity(0.05),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(16),
          borderSide: BorderSide.none,
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(16),
          borderSide: const BorderSide(color: Color(0xFFFFD700)),
        ),
      ),
    );
  }

  Widget _buildDropdown(
    List<String> items,
    String value,
    void Function(String?) onChanged,
  ) {
    if (!items.contains(value)) items.add(value); // Safeguard
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16),
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.05),
        borderRadius: BorderRadius.circular(16),
      ),
      child: DropdownButtonHideUnderline(
        child: DropdownButton<String>(
          value: value,
          isExpanded: true,
          dropdownColor: const Color(0xFF1A1A24),
          icon: const Icon(Icons.expand_more, color: Color(0xFFFFD700)),
          items: items
              .map(
                (e) => DropdownMenuItem(
                  value: e,
                  child: Text(
                    e,
                    style: GoogleFonts.outfit(
                      color: Colors.white,
                      fontSize: 16,
                    ),
                  ),
                ),
              )
              .toList(),
          onChanged: onChanged,
        ),
      ),
    );
  }
}
