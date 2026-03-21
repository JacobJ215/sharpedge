import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';
import 'package:sharpedge_mobile/main.dart';
import 'package:sharpedge_mobile/providers/app_state.dart';

void main() {
  testWidgets('App smoke test', (WidgetTester tester) async {
    await tester.pumpWidget(
      ChangeNotifierProvider<AppState>(
        create: (_) => AppState(),
        child: const SharpEdgeApp(),
      ),
    );
    await tester.pump();
    expect(find.text('SharpEdge'), findsWidgets);
  });
}
