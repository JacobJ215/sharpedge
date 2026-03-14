import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/app_state.dart';
import '../widgets/play_card.dart';

const _kBlue  = Color(0xFF3B82F6);
const _kRed   = Color(0xFFEF4444);
const _kTeal  = Color(0xFF00D4AA);
const _kBg    = Color(0xFF0A0A0A);

class LineMovementScreen extends StatelessWidget {
  const LineMovementScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final state = context.watch<AppState>();

    return Scaffold(
      backgroundColor: _kBg,
      appBar: AppBar(
        backgroundColor: _kBg,
        toolbarHeight: 56,
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Line Movement',
              style: TextStyle(
                fontSize: 17,
                fontWeight: FontWeight.w700,
                letterSpacing: -0.5,
              ),
            ),
            Text(
              state.lineMovements.isEmpty
                  ? 'No steam moves detected'
                  : '${state.lineMovements.length} moves  ·  last 24h',
              style: const TextStyle(
                fontSize: 11,
                color: Color(0xFF6B7280),
                letterSpacing: 0.1,
              ),
            ),
          ],
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh_rounded, size: 18),
            onPressed: () => context.read<AppState>().refresh(),
            color: const Color(0xFF4B5563),
          ),
        ],
      ),
      body: _body(state),
    );
  }

  Widget _body(AppState state) {
    if (state.loading) {
      return const Center(
        child: CircularProgressIndicator(color: _kBlue, strokeWidth: 2),
      );
    }
    if (state.error != null) {
      return Center(
        child: Text(
          'Error: ${state.error}',
          style: const TextStyle(color: _kRed, fontSize: 13),
        ),
      );
    }
    final movements = state.lineMovements;
    if (movements.isEmpty) {
      return const _EmptyState();
    }
    return ListView.builder(
      itemCount: movements.length,
      padding: const EdgeInsets.only(bottom: 24),
      itemBuilder: (context, i) {
        final m = movements[i];
        final isUp = m.direction == 'up';
        final moveColor = isUp ? _kRed : _kTeal;
        return PlayCard(
          title: m.event,
          subtitle: m.market,
          accentColor: moveColor,
          trailing: _LineTrailing(
            movement: m.movement,
            openLine: m.openLine,
            currentLine: m.currentLine,
            isUp: isUp,
            color: moveColor,
          ),
        );
      },
    );
  }
}

// ── Line trailing widget ──────────────────────────────────────────────────────

class _LineTrailing extends StatelessWidget {
  final double movement;
  final double openLine;
  final double currentLine;
  final bool isUp;
  final Color color;

  const _LineTrailing({
    required this.movement,
    required this.openLine,
    required this.currentLine,
    required this.isUp,
    required this.color,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisAlignment: MainAxisAlignment.center,
      crossAxisAlignment: CrossAxisAlignment.end,
      children: [
        Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              isUp ? Icons.arrow_upward_rounded : Icons.arrow_downward_rounded,
              color: color,
              size: 13,
            ),
            const SizedBox(width: 2),
            Text(
              movement.abs().toStringAsFixed(1),
              style: TextStyle(
                color: color,
                fontWeight: FontWeight.w700,
                fontSize: 16,
                letterSpacing: -0.4,
              ),
            ),
          ],
        ),
        const SizedBox(height: 3),
        Text(
          '${openLine.toStringAsFixed(1)} → ${currentLine.toStringAsFixed(1)}',
          style: const TextStyle(
            color: Color(0xFF6B7280),
            fontSize: 10,
            fontWeight: FontWeight.w400,
            letterSpacing: 0.1,
          ),
        ),
      ],
    );
  }
}

// ── Empty state ───────────────────────────────────────────────────────────────

class _EmptyState extends StatelessWidget {
  const _EmptyState();

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 52,
              height: 52,
              decoration: BoxDecoration(
                color: Colors.white.withValues(alpha: 0.03),
                borderRadius: BorderRadius.circular(14),
                border: Border.all(
                  color: Colors.white.withValues(alpha: 0.06),
                  width: 1,
                ),
              ),
              child: const Icon(Icons.show_chart_rounded,
                  color: Color(0xFF374151), size: 22),
            ),
            const SizedBox(height: 16),
            const Text(
              'No line movement',
              style: TextStyle(
                color: Colors.white70,
                fontSize: 15,
                fontWeight: FontWeight.w600,
                letterSpacing: -0.3,
              ),
            ),
            const SizedBox(height: 6),
            const Text(
              'Market data will appear here\nas odds shift across sportsbooks',
              style: TextStyle(
                color: Color(0xFF6B7280),
                fontSize: 12,
                fontWeight: FontWeight.w400,
              ),
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }
}
