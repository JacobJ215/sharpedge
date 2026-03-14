import 'package:flutter_test/flutter_test.dart';
import 'package:sharpedge_mobile/main.dart';

void main() {
  testWidgets('App smoke test', (WidgetTester tester) async {
    await tester.pumpWidget(const SharpEdgeApp());
    expect(find.text('SharpEdge'), findsWidgets);
  });
}
