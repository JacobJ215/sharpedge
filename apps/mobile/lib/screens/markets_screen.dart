import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/app_state.dart';
import '../models/value_play.dart';
import '../widgets/alpha_badge_widget.dart';
import 'copilot_screen.dart';

const _kTeal   = Color(0xFF10B981);
const _kAmber  = Color(0xFFF59E0B);
const _kBlue   = Color(0xFF3B82F6);
const _kViolet = Color(0xFF8B5CF6);
const _kBg     = Color(0xFF0A0A0A);
const _kCard   = Color(0xFF141414);

enum _PmFilter { all, kalshi, polymarket, highEdge }

String _extractPlatform(String event) {
  final lower = event.toLowerCase();
  if (lower.contains('kalshi')) return 'Kalshi';
  if (lower.contains('polymarket')) return 'Polymarket';
  return event.split('-').first;
}

class MarketsScreen extends StatefulWidget {
  const MarketsScreen({super.key});

  @override
  State<MarketsScreen> createState() => _MarketsScreenState();
}

class _MarketsScreenState extends State<MarketsScreen> {
  _PmFilter _filter = _PmFilter.all;

  List<ValuePlayV1> _applyFilter(List<ValuePlayV1> plays) {
    switch (_filter) {
      case _PmFilter.all:
        return plays;
      case _PmFilter.kalshi:
        return plays.where((p) => _extractPlatform(p.event) == 'Kalshi').toList();
      case _PmFilter.polymarket:
        return plays.where((p) => _extractPlatform(p.event) == 'Polymarket').toList();
      case _PmFilter.highEdge:
        return plays.where((p) => p.expectedValue * 100 >= 5).toList();
    }
  }

  @override
  Widget build(BuildContext context) {
    final state = context.watch<AppState>();
    final allPlays = state.pmPlays;
    final filtered = _applyFilter(allPlays);
    final premiumCount = allPlays.where((p) => p.alphaBadge == 'PREMIUM').length;

    return Scaffold(
      backgroundColor: _kBg,
      appBar: AppBar(
        backgroundColor: _kBg,
        toolbarHeight: 56,
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Markets',
              style: TextStyle(fontSize: 17, fontWeight: FontWeight.w700, letterSpacing: -0.5),
            ),
            Text(
              allPlays.isEmpty
                  ? 'Scanning Kalshi · Polymarket'
                  : '${allPlays.length} active  ·  $premiumCount premium',
              style: const TextStyle(fontSize: 11, color: Color(0xFF6B7280), letterSpacing: 0.1),
            ),
          ],
        ),
        actions: [
          if (!state.loading) ...[
            Container(
              width: 6,
              height: 6,
              decoration: BoxDecoration(
                color: _kTeal,
                shape: BoxShape.circle,
                boxShadow: [
                  BoxShadow(color: _kTeal.withValues(alpha: 0.6), blurRadius: 5, spreadRadius: 1),
                ],
              ),
            ),
            const SizedBox(width: 5),
            const Text(
              'LIVE',
              style: TextStyle(fontSize: 9, fontWeight: FontWeight.w700, color: Color(0xFF6B7280), letterSpacing: 1.0),
            ),
            const SizedBox(width: 4),
          ],
          IconButton(
            icon: const Icon(Icons.refresh_rounded, size: 18),
            onPressed: () => context.read<AppState>().refresh(),
            color: const Color(0xFF4B5563),
          ),
        ],
      ),
      body: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _AgenticBrief(plays: allPlays),
          _buildFilterRow(),
          Expanded(child: _body(state, filtered)),
        ],
      ),
    );
  }

  Widget _buildFilterRow() {
    return Container(
      padding: const EdgeInsets.fromLTRB(16, 4, 16, 12),
      child: SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        child: Row(
          children: [
            _FilterPill(label: 'All', selected: _filter == _PmFilter.all, color: _kTeal, onTap: () => setState(() => _filter = _PmFilter.all)),
            const SizedBox(width: 8),
            _FilterPill(label: 'Kalshi', selected: _filter == _PmFilter.kalshi, color: _kBlue, onTap: () => setState(() => _filter = _PmFilter.kalshi)),
            const SizedBox(width: 8),
            _FilterPill(label: 'Polymarket', selected: _filter == _PmFilter.polymarket, color: _kViolet, onTap: () => setState(() => _filter = _PmFilter.polymarket)),
            const SizedBox(width: 8),
            _FilterPill(label: 'High Edge', selected: _filter == _PmFilter.highEdge, color: _kAmber, onTap: () => setState(() => _filter = _PmFilter.highEdge)),
          ],
        ),
      ),
    );
  }

  Widget _body(AppState state, List<ValuePlayV1> filtered) {
    if (state.loading) {
      return const Center(child: CircularProgressIndicator(color: _kTeal, strokeWidth: 2));
    }
    if (state.error != null) {
      return Center(
        child: Text(
          'Error: ${state.error}',
          style: const TextStyle(color: Color(0xFFEF4444), fontSize: 13),
        ),
      );
    }
    if (filtered.isEmpty) {
      return _buildEmpty();
    }
    return RefreshIndicator(
      color: _kTeal,
      backgroundColor: _kCard,
      onRefresh: () => context.read<AppState>().refresh(),
      child: ListView.builder(
        padding: const EdgeInsets.only(bottom: 24),
        itemCount: filtered.length,
        itemBuilder: (_, i) => _PmEdgeCard(play: filtered[i]),
      ),
    );
  }

  Widget _buildEmpty() {
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
                border: Border.all(color: Colors.white.withValues(alpha: 0.06)),
              ),
              child: const Icon(Icons.candlestick_chart_outlined, color: Color(0xFF374151), size: 24),
            ),
            const SizedBox(height: 16),
            const Text(
              'No market edges',
              style: TextStyle(color: Colors.white70, fontSize: 15, fontWeight: FontWeight.w600, letterSpacing: -0.3),
            ),
            const SizedBox(height: 6),
            Text(
              _filter == _PmFilter.all
                  ? 'Prediction market edges appear here\nwhen models detect probability dislocations'
                  : 'No ${_filter.name} edges at this time',
              style: const TextStyle(color: Color(0xFF6B7280), fontSize: 12),
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }
}

// ── Agentic Brief ──────────────────────────────────────────────────────────────

class _AgenticBrief extends StatelessWidget {
  final List<ValuePlayV1> plays;
  const _AgenticBrief({required this.plays});

  String _generateBrief() {
    if (plays.isEmpty) {
      return 'No prediction market edges detected. Markets appear efficiently priced across '
          'Kalshi and Polymarket — regime scanning is active. '
          'Watch for probability dislocations during high-volatility news events.';
    }
    final premium = plays.where((p) => p.alphaBadge == 'PREMIUM').length;
    final highEdge = plays.where((p) => p.expectedValue * 100 >= 5).length;
    final kalshiCount = plays.where((p) => _extractPlatform(p.event) == 'Kalshi').length;
    final polyCount = plays.where((p) => _extractPlatform(p.event) == 'Polymarket').length;
    final topPlay = plays.reduce((a, b) => a.expectedValue > b.expectedValue ? a : b);
    final topEv = (topPlay.expectedValue * 100).toStringAsFixed(1);
    return '${plays.length} active edge${plays.length != 1 ? 's' : ''} ($kalshiCount Kalshi, $polyCount Polymarket). '
        '$premium premium signal${premium != 1 ? 's' : ''}, $highEdge high-edge ≥5% EV. '
        'Top: ${topPlay.market} at +$topEv% — '
        'regime-adjusted thresholds active, model vs. market pricing dislocations tracked.';
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 4),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                width: 2,
                height: 12,
                decoration: BoxDecoration(
                  color: _kViolet,
                  borderRadius: BorderRadius.circular(1),
                ),
              ),
              const SizedBox(width: 7),
              const Text(
                'AI BRIEF',
                style: TextStyle(fontSize: 10, fontWeight: FontWeight.w700, color: Color(0xFF6B7280), letterSpacing: 1.3),
              ),
              const Spacer(),
              GestureDetector(
                onTap: () => Navigator.of(context).push(
                  MaterialPageRoute<void>(builder: (_) => const CopilotScreen()),
                ),
                child: const Text(
                  'Ask Copilot →',
                  style: TextStyle(fontSize: 10, color: _kViolet, fontWeight: FontWeight.w600),
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            _generateBrief(),
            style: const TextStyle(fontSize: 12, color: Color(0xFF9CA3AF), height: 1.5, letterSpacing: -0.1),
          ),
          const SizedBox(height: 12),
          Container(height: 0.5, color: Colors.white.withValues(alpha: 0.06)),
        ],
      ),
    );
  }
}

// ── PM Edge Card ───────────────────────────────────────────────────────────────

class _PmEdgeCard extends StatelessWidget {
  final ValuePlayV1 play;
  const _PmEdgeCard({required this.play});

  Color get _evColor {
    final ev = play.expectedValue * 100;
    if (ev >= 5) return _kTeal;
    if (ev >= 2) return _kBlue;
    if (ev >= 0) return const Color(0xFF6B7280);
    return const Color(0xFFEF4444);
  }

  Color get _platformColor {
    final platform = _extractPlatform(play.event);
    if (platform == 'Kalshi') return _kBlue;
    if (platform == 'Polymarket') return _kViolet;
    return const Color(0xFF6B7280);
  }

  @override
  Widget build(BuildContext context) {
    final ev = play.expectedValue * 100;
    final evColor = _evColor;
    final platform = _extractPlatform(play.event);

    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 14, 16, 14),
          child: Row(
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      play.market,
                      style: const TextStyle(
                        fontWeight: FontWeight.w600,
                        fontSize: 13,
                        letterSpacing: -0.2,
                        color: Colors.white,
                        height: 1.3,
                      ),
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                    ),
                    const SizedBox(height: 3),
                    Text(
                      play.event,
                      style: const TextStyle(color: Color(0xFF6B7280), fontSize: 11),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                    const SizedBox(height: 8),
                    Row(
                      children: [
                        Text(
                          platform,
                          style: TextStyle(
                            fontSize: 9,
                            fontWeight: FontWeight.w700,
                            color: _platformColor,
                            letterSpacing: 0.5,
                          ),
                        ),
                        const SizedBox(width: 8),
                        AlphaBadgeWidget(badge: play.alphaBadge),
                        const SizedBox(width: 6),
                        Text(
                          play.regimeState,
                          style: const TextStyle(color: Color(0xFF4B5563), fontSize: 10, fontWeight: FontWeight.w500),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 12),
              Column(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  Text(
                    '${ev >= 0 ? '+' : ''}${ev.toStringAsFixed(1)}%',
                    style: TextStyle(
                      color: evColor,
                      fontWeight: FontWeight.w700,
                      fontSize: 18,
                      letterSpacing: -0.5,
                      height: 1,
                    ),
                  ),
                  const SizedBox(height: 2),
                  const Text(
                    'EDGE',
                    style: TextStyle(color: Color(0xFF4B5563), fontSize: 10, fontWeight: FontWeight.w600, letterSpacing: 0.5),
                  ),
                  const SizedBox(height: 6),
                  Text(
                    'α ${play.alphaScore.toStringAsFixed(2)}',
                    style: const TextStyle(color: Color(0xFF374151), fontSize: 10, fontWeight: FontWeight.w500),
                  ),
                ],
              ),
            ],
          ),
        ),
        Container(
          height: 0.5,
          color: Colors.white.withValues(alpha: 0.07),
          margin: const EdgeInsets.only(left: 16),
        ),
      ],
    );
  }
}

// ── Filter Pill ────────────────────────────────────────────────────────────────

class _FilterPill extends StatelessWidget {
  final String label;
  final bool selected;
  final Color color;
  final VoidCallback onTap;
  const _FilterPill({required this.label, required this.selected, required this.color, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 150),
        padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 6),
        decoration: BoxDecoration(
          border: Border(
            bottom: BorderSide(color: selected ? color : Colors.transparent, width: 1.5),
          ),
        ),
        child: Text(
          label,
          style: TextStyle(
            fontSize: 12,
            fontWeight: selected ? FontWeight.w600 : FontWeight.w400,
            color: selected ? color : const Color(0xFF666666),
          ),
        ),
      ),
    );
  }
}
