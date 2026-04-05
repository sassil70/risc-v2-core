import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:witness_v2/main.dart'; 

void main() {
  testWidgets('App launches and shows loading indicator initally', (WidgetTester tester) async {
    // Wrap in ProviderScope
    await tester.pumpWidget(const ProviderScope(child: WitnessApp()));

    // Verify loading state (CircularProgressIndicator) because cameras are not mocked/initialized
    expect(find.byType(CircularProgressIndicator), findsOneWidget);
  });
}
