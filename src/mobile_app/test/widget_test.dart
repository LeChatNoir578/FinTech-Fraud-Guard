import 'package:flutter_test/flutter_test.dart';
import 'package:mobile_app/main.dart';

void main() {
  testWidgets('FinTech Fraud Guard login smoke test', (WidgetTester tester) async {
    // Build our app and trigger a frame.
    await tester.pumpWidget(const FinTechFraudGuardApp());

    // Verify that the title and login options are rendered.
    expect(find.text('FinTech Fraud Guard'), findsOneWidget);
    expect(find.text('Usuario Normal'), findsOneWidget);
  });
}
