import 'package:firebase_core/firebase_core.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
import 'providers/app_state.dart';
import 'screens/home_screen.dart';
import 'screens/value_plays_screen.dart';
import 'screens/bankroll_screen.dart';
import 'screens/copilot_screen.dart';
import 'screens/analytics_screen.dart';
import 'screens/markets_screen.dart';
import 'screens/feed_screen.dart';
import 'screens/login_screen.dart';
import 'services/api_service.dart';
import 'services/notification_service.dart';

const _supabaseUrl = String.fromEnvironment('SUPABASE_URL');
const _supabaseAnonKey = String.fromEnvironment('SUPABASE_ANON_KEY');

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  try {
    await Firebase.initializeApp();
    await NotificationService.initialize();
  } catch (_) {
    // Firebase not configured — push notifications unavailable.
  }
  await Supabase.initialize(
    url: _supabaseUrl.isNotEmpty
        ? _supabaseUrl
        : 'https://pkghoghcxufszfyyysmf.supabase.co',
    anonKey: _supabaseAnonKey.isNotEmpty ? _supabaseAnonKey : '',
  );
  runApp(
    ChangeNotifierProvider(
      create: (_) => AppState()..refresh(),
      child: const SharpEdgeApp(),
    ),
  );
}

// ── Global design tokens ──────────────────────────────────────────────────────
const kBg     = Color(0xFF0A0A0A);   // deepest background
const kCard   = Color(0xFF141414);   // card surface
const kTeal   = Color(0xFF10B981);
const kAmber  = Color(0xFFF59E0B);
const kBlue   = Color(0xFF3B82F6);
const kRed    = Color(0xFFEF4444);

class SharpEdgeApp extends StatelessWidget {
  const SharpEdgeApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'SharpEdge',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(
          seedColor: kTeal,
          brightness: Brightness.dark,
        ).copyWith(
          primary: kTeal,
          secondary: kAmber,
          surface: kCard,
          onSurface: Colors.white,
        ),
        useMaterial3: true,
        scaffoldBackgroundColor: kBg,
        cardTheme: CardThemeData(
          color: kCard,
          elevation: 0,
          shape: RoundedRectangleBorder(
            borderRadius: const BorderRadius.all(Radius.circular(12)),
            side: BorderSide(
              color: Colors.white.withValues(alpha: 0.05),
              width: 1,
            ),
          ),
          clipBehavior: Clip.antiAlias,
        ),
        appBarTheme: const AppBarTheme(
          backgroundColor: kBg,
          elevation: 0,
          scrolledUnderElevation: 0,
          centerTitle: false,
          systemOverlayStyle: SystemUiOverlayStyle(
            statusBarBrightness: Brightness.dark,
            statusBarIconBrightness: Brightness.light,
          ),
          titleTextStyle: TextStyle(
            color: Colors.white,
            fontSize: 17,
            fontWeight: FontWeight.w700,
            letterSpacing: -0.4,
          ),
        ),
        textTheme: const TextTheme(
          bodyMedium: TextStyle(
            fontSize: 13,
            fontWeight: FontWeight.w500,
            letterSpacing: -0.1,
            color: Colors.white,
          ),
          bodySmall: TextStyle(
            fontSize: 12,
            fontWeight: FontWeight.w400,
            letterSpacing: -0.1,
          ),
        ),
        dividerTheme: DividerThemeData(
          color: Colors.white.withValues(alpha: 0.05),
          thickness: 1,
        ),
      ),
      home: const _AuthGate(),
    );
  }
}

class _AuthGate extends StatelessWidget {
  const _AuthGate();

  @override
  Widget build(BuildContext context) {
    final isAuthenticated = context.watch<AppState>().isAuthenticated;
    if (!isAuthenticated) {
      return const LoginScreen();
    }
    return const _Shell();
  }
}

class _Shell extends StatefulWidget {
  const _Shell();

  @override
  State<_Shell> createState() => _ShellState();
}

class _ShellState extends State<_Shell> {
  int _index = 0;

  @override
  void initState() {
    super.initState();
    // Register FCM device token now that user is authenticated.
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final appState = context.read<AppState>();
      if (appState.userId != null && appState.authToken != null) {
        NotificationService.registerToken(
          userId: appState.userId!,
          authToken: appState.authToken!,
          baseUrl: ApiService.baseUrl,
        );
      }
    });
  }

  static const _screens = [
    HomeScreen(),
    ValuePlaysScreen(),
    FeedScreen(),
    AnalyticsScreen(),
    MarketsScreen(),
    CopilotScreen(),
    BankrollScreen(),
  ];

  static const _navItems = [
    _NavItem(icon: Icons.show_chart_outlined,             selectedIcon: Icons.show_chart,             label: 'Portfolio'),
    _NavItem(icon: Icons.trending_up_outlined,            selectedIcon: Icons.trending_up,            label: 'Value Plays'),
    _NavItem(icon: Icons.dynamic_feed_outlined,           selectedIcon: Icons.dynamic_feed,           label: 'Feed'),
    _NavItem(icon: Icons.analytics_outlined,              selectedIcon: Icons.analytics,              label: 'Analytics'),
    _NavItem(icon: Icons.candlestick_chart_outlined,      selectedIcon: Icons.candlestick_chart,      label: 'Markets'),
    _NavItem(icon: Icons.auto_awesome_outlined,           selectedIcon: Icons.auto_awesome,           label: 'Copilot'),
    _NavItem(icon: Icons.account_balance_wallet_outlined, selectedIcon: Icons.account_balance_wallet, label: 'Bankroll'),
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: IndexedStack(index: _index, children: _screens),
      bottomNavigationBar: _BottomNav(
        index: _index,
        items: _navItems,
        onTap: (i) => setState(() => _index = i),
      ),
    );
  }
}

// ── Custom bottom navigation (Stake / Grok inspired) ─────────────────────────

class _NavItem {
  final IconData icon;
  final IconData selectedIcon;
  final String label;
  const _NavItem({required this.icon, required this.selectedIcon, required this.label});
}

class _BottomNav extends StatelessWidget {
  final int index;
  final List<_NavItem> items;
  final ValueChanged<int> onTap;

  const _BottomNav({
    required this.index,
    required this.items,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final bottom = MediaQuery.of(context).padding.bottom;
    return Container(
      decoration: BoxDecoration(
        color: kCard,
        border: Border(
          top: BorderSide(
            color: Colors.white.withValues(alpha: 0.06),
            width: 1,
          ),
        ),
      ),
      child: SafeArea(
        top: false,
        child: SizedBox(
          height: 56,
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceAround,
            children: List.generate(items.length, (i) {
              final selected = i == index;
              final item = items[i];
              return _NavButton(
                icon: selected ? item.selectedIcon : item.icon,
                label: item.label,
                selected: selected,
                onTap: () => onTap(i),
              );
            }),
          ),
        ),
      ),
    );
  }
}

class _NavButton extends StatelessWidget {
  final IconData icon;
  final String label;
  final bool selected;
  final VoidCallback onTap;

  const _NavButton({
    required this.icon,
    required this.label,
    required this.selected,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final color = selected ? kTeal : const Color(0xFF4B5563);
    return GestureDetector(
      onTap: onTap,
      behavior: HitTestBehavior.opaque,
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 4),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(icon, size: 22, color: color),
            const SizedBox(height: 3),
            Text(
              label,
              style: TextStyle(
                fontSize: 10,
                fontWeight: selected ? FontWeight.w600 : FontWeight.w500,
                color: color,
                letterSpacing: 0.1,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
