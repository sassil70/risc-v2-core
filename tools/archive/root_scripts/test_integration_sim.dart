import 'dart:io';
import 'dart:convert';
import 'package:http/http.dart' as http;

// CONFIG
const baseUrl = 'http://localhost:8001/api';
// Use the file we copied earlier
const audioPath = 'c:\\Users\\Salim B Assil\\Documents\\Smart_Inspection_Project\\RISC_V2_Core_System\\test_audio_command.m4a'; 

Future<void> main() async {
  print('🧪 STARTING DART CLIENT SIMULATION (Integration Test)');
  
  final audioFile = File(audioPath);
  if (!audioFile.existsSync()) {
    print('❌ Error: Audio file not found at $audioPath');
    exit(1);
  }

  try {
    // --- STEP 1: GENERATE PLAN (Voice Architect) ---
    print('\n🔊 Step 1: Sending Audio to Architect...');
    var request = http.MultipartRequest('POST', Uri.parse('$baseUrl/floorplan/init'));
    request.files.add(await http.MultipartFile.fromPath('file', audioFile.path));
    request.fields['property_type'] = 'Detached House';
    request.fields['floors'] = '2';

    final streamedResponse = await request.send();
    final response = await http.Response.fromStream(streamedResponse);

    if (response.statusCode != 200) {
      print('❌ Architect Failed: ${response.statusCode} - ${response.body}');
      exit(1);
    }

    final planMap = json.decode(response.body);
    print('✅ Architect Success! Plan Received.');
    // Validate Structure
    if (planMap['floors'] == null) {
       print('❌ Invalid Plan Structure (No floors)');
       exit(1);
    }
    
    // --- STEP 2: PROCESS PLAN (Simulating Logic in plan_confirmation_screen) ---
    print('\n🔄 Step 2: Processing Plan (Mobile Logic Simulation)...');
    List<Map<String, dynamic>> processedRooms = [];
    final floors = planMap['floors'] as List<dynamic>;
    
    for (int i = 0; i < floors.length; i++) {
        final floor = floors[i];
        final rooms = floor['rooms'] as List<dynamic>;
        for (var room in rooms) {
            processedRooms.add({
                'id': room['id'], 
                'name': room['name'],
                'type': room['type'],
                'floor': i,
                'status': 'red',
                'contexts': room['contexts'] // The Key Verify
            });
        }
    }
    
    if (processedRooms.isEmpty) {
        print('⚠️ Warning: No rooms found in plan.');
    } else {
        print('✅ Processed ${processedRooms.length} rooms.');
        print('🔍 Checking Contexts for first room...');
        if (processedRooms[0]['contexts'] != null) {
            print('✅ Contexts Preserved: ${processedRooms[0]['contexts'].length} tags.');
        } else {
             print('❌ CRITICAL FAILURE: Contexts Lost!');
             exit(1);
        }
    }

    // --- STEP 3: INIT PROPERTY (Session Start) ---
    print('\n🚀 Step 3: Initializing Property Session...');
    final initData = {
        'address': {'postcode': 'TEST', 'street': 'Sim St'},
        'property_type': 'Detached',
        'floor_plan': {'rooms': processedRooms} 
    };
    
    final initRes = await http.post(
        Uri.parse('$baseUrl/property/init'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode(initData)
    );
    
    if (initRes.statusCode == 200) {
        final initJson = json.decode(initRes.body);
        print('✅ Session Started! ID: ${initJson['session_id']}');
    } else {
        print('❌ Init Failed: ${initRes.statusCode}');
        exit(1);
    }
    
    print('\n🏆 INTEGRATION TEST PASSED: Full Cycle Complete.');

  } catch (e) {
    print('❌ Exception: $e');
    exit(1);
  }
}
