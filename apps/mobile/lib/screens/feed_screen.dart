import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/app_state.dart';

const _kTeal  = Color(0xFF10B981);
const _kAmber = Color(0xFFF59E0B);
const _kBlue  = Color(0xFF3B82F6);
const _kRed   = Color(0xFFEF4444);
const _kGreen = Color(0xFF10B981);
const _kBg    = Color(0xFF0A0A0A);
const _kCard  = Color(0xFF141414);

const _kViolet = Color(0xFF8B5CF6);

enum _FeedFilter { all, steam, sharp, value, arb, pm }

String _extractPlatform(String event) {
  final lower = event.toLowerCase();
  if (lower.contains('kalshi')) return 'Kalshi';
  if (lower.contains('polymarket')) return 'Polymarket';
  return event.split('-').first;
}

class FeedScreen extends StatefulWidget {
  const FeedScreen({super.key});
  @override
  State<FeedScreen> createState() => _FeedScreenState();
}

class _FeedScreenState extends State<FeedScreen> {
  _FeedFilter _filter = _FeedFilter.all;

  @override
  Widget build(BuildContext context) {
    final state = context.watch<AppState>();
    final items = _buildFeedItems(state);
    final filtered = _filter == _FeedFilter.all ? items : items.where((item) => item.type == _filter).toList();

    return Scaffold(
      backgroundColor: _kBg,
      appBar: AppBar(
        backgroundColor: _kBg,
        toolbarHeight: 56,
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('Feed', style: TextStyle(fontSize: 17, fontWeight: FontWeight.w700, letterSpacing: -0.5)),
            Text('${filtered.length} signal${filtered.length != 1 ? 's' : ''}  ·  live',
              style: const TextStyle(fontSize: 11, color: Color(0xFF6B7280), letterSpacing: 0.1)),
          ],
        ),
        actions: [
          if (!state.loading) ...[
            Container(
              width: 6, height: 6,
              decoration: BoxDecoration(
                color: _kTeal, shape: BoxShape.circle,
                boxShadow: [BoxShadow(color: _kTeal.withValues(alpha: 0.6), blurRadius: 5, spreadRadius: 1)],
              ),
            ),
            const SizedBox(width: 5),
            const Text('LIVE', style: TextStyle(fontSize: 9, fontWeight: FontWeight.w700, color: Color(0xFF6B7280), letterSpacing: 1.0)),
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
        children: [
          _buildFilterRow(),
          Expanded(
            child: state.loading
                ? const Center(child: CircularProgressIndicator(color: _kTeal, strokeWidth: 2))
                : filtered.isEmpty
                    ? _buildEmptyState()
                    : RefreshIndicator(
                        color: _kTeal,
                        backgroundColor: _kCard,
                        onRefresh: () => context.read<AppState>().refresh(),
                        child: ListView.builder(
                          padding: const EdgeInsets.only(bottom: 24),
                          itemCount: filtered.length,
                          itemBuilder: (_, i) => _FeedItemCard(item: filtered[i]),
                        ),
                      ),
          ),
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
            _FeedFilterPill(label: 'All', filter: _FeedFilter.all, selected: _filter == _FeedFilter.all, color: _kTeal, onTap: () => setState(() => _filter = _FeedFilter.all)),
            const SizedBox(width: 8),
            _FeedFilterPill(label: 'Steam', filter: _FeedFilter.steam, selected: _filter == _FeedFilter.steam, color: _kRed, onTap: () => setState(() => _filter = _FeedFilter.steam)),
            const SizedBox(width: 8),
            _FeedFilterPill(label: 'Sharp', filter: _FeedFilter.sharp, selected: _filter == _FeedFilter.sharp, color: _kBlue, onTap: () => setState(() => _filter = _FeedFilter.sharp)),
            const SizedBox(width: 8),
            _FeedFilterPill(label: 'Value', filter: _FeedFilter.value, selected: _filter == _FeedFilter.value, color: _kGreen, onTap: () => setState(() => _filter = _FeedFilter.value)),
            const SizedBox(width: 8),
            _FeedFilterPill(label: 'Arb', filter: _FeedFilter.arb, selected: _filter == _FeedFilter.arb, color: _kAmber, onTap: () => setState(() => _filter = _FeedFilter.arb)),
            const SizedBox(width: 8),
            _FeedFilterPill(label: 'PM', filter: _FeedFilter.pm, selected: _filter == _FeedFilter.pm, color: _kViolet, onTap: () => setState(() => _filter = _FeedFilter.pm)),
          ],
        ),
      ),
    );
  }

  List<_FeedItem> _buildFeedItems(AppState state) {
    final items = <_FeedItem>[];

    // Steam / sharp moves from line movements
    for (final m in state.lineMovements) {
      final isLarge = m.movement.abs() >= 1.5;
      final isSteam = m.direction == 'up';
      items.add(_FeedItem(
        type: isSteam ? _FeedFilter.steam : _FeedFilter.sharp,
        event: m.event,
        context: m.market,
        title: isSteam ? (isLarge ? 'Large Steam Move' : 'Line Movement') : 'Reverse Line Move',
        analysis: isSteam
            ? 'Line moved up ${m.movement.abs().toStringAsFixed(1)} pts from open (${m.openLine.toStringAsFixed(1)}→${m.currentLine.toStringAsFixed(1)}). '
              'Heavy public action driving this move. Watch for reversal if sharp money disagrees.'
            : 'Line dropped ${m.movement.abs().toStringAsFixed(1)} pts despite public backing opposite side. '
              'Classic reverse line move pattern — sharp money indicator. High CLV potential.',
        badge: isSteam ? 'STEAM' : 'SHARP',
        badgeColor: isSteam ? _kRed : _kBlue,
        confidence: isLarge ? 'HIGH' : 'MODERATE',
      ));
    }

    // Sharp action from high-alpha value plays
    for (final p in state.valuePlays.where((p) => p.expectedValue * 100 >= 3)) {
      final ev = p.expectedValue * 100;
      items.add(_FeedItem(
        type: _FeedFilter.sharp,
        event: p.event,
        context: '${p.market}  ·  ${p.book}',
        title: 'Sharp Edge Detected',
        analysis: 'Model finds +${ev.toStringAsFixed(1)}% EV. Market pricing appears to undervalue our probability estimate. '
            'High CLV potential — prioritize early entry before line correction.',
        badge: 'SHARP',
        badgeColor: _kBlue,
        confidence: ev >= 5 ? 'HIGH' : 'MODERATE',
      ));
    }

    // Value plays with moderate EV
    for (final p in state.valuePlays.where((p) => p.expectedValue * 100 >= 1 && p.expectedValue * 100 < 3)) {
      final ev = p.expectedValue * 100;
      items.add(_FeedItem(
        type: _FeedFilter.value,
        event: p.event,
        context: '${p.market}  ·  ${p.book}',
        title: 'Value Alert',
        analysis: '+${ev.toStringAsFixed(1)}% EV. Moderate edge — size per Kelly with fraction. '
            'Monitor for confirmation via line movement toward your position.',
        badge: 'VALUE',
        badgeColor: _kGreen,
        confidence: 'MODERATE',
      ));
    }

    // Prediction market edges
    for (final p in state.pmPlays.where((p) => p.expectedValue * 100 >= 2)) {
      final ev = p.expectedValue * 100;
      final platform = _extractPlatform(p.event);
      items.add(_FeedItem(
        type: _FeedFilter.pm,
        event: p.market,
        context: '$platform  ·  ${p.regimeState}',
        title: 'PM Edge Detected',
        analysis: '+${ev.toStringAsFixed(1)}% EV on $platform. '
            '${p.alphaBadge == 'PREMIUM' ? 'Premium alpha — model finds significant probability dislocation vs. market pricing.' : 'Model edge detected against current market consensus.'} '
            'Regime-adjusted threshold active.',
        badge: 'PM EDGE',
        badgeColor: _kViolet,
        confidence: p.alphaBadge == 'PREMIUM' || ev >= 5 ? 'HIGH' : 'MODERATE',
      ));
    }

    // Arbitrage opportunities
    for (final a in state.arbitrage) {
      items.add(_FeedItem(
        type: _FeedFilter.arb,
        event: a.event,
        context: a.market,
        title: 'Arbitrage Opportunity',
        analysis: '+${a.profitPercent.toStringAsFixed(2)}% guaranteed profit across ${a.legs.length} legs. '
            'Book discrepancy detected — act quickly before books adjust lines.',
        badge: 'ARB',
        badgeColor: _kAmber,
        confidence: a.profitPercent >= 1 ? 'HIGH' : 'MODERATE',
      ));
    }

    // Sort by confidence
    items.sort((a, b) {
      const order = {'HIGH': 0, 'MODERATE': 1};
      return (order[a.confidence] ?? 2).compareTo(order[b.confidence] ?? 2);
    });

    return items;
  }

  Widget _buildEmptyState() {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 52, height: 52,
              decoration: BoxDecoration(
                color: Colors.white.withValues(alpha: 0.03),
                borderRadius: BorderRadius.circular(14),
                border: Border.all(color: Colors.white.withValues(alpha: 0.06), width: 1),
              ),
              child: const Icon(Icons.dynamic_feed_outlined, color: Color(0xFF374151), size: 24),
            ),
            const SizedBox(height: 16),
            const Text('Feed is quiet', style: TextStyle(color: Colors.white70, fontSize: 15, fontWeight: FontWeight.w600, letterSpacing: -0.3)),
            const SizedBox(height: 6),
            Text(
              _filter == _FeedFilter.all
                  ? 'Intelligence signals will appear\nas markets become active'
                  : 'No ${_filter.name} signals at this time',
              style: const TextStyle(color: Color(0xFF6B7280), fontSize: 12),
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }
}

class _FeedItem {
  final _FeedFilter type;
  final String event, context, title, analysis, badge, confidence;
  final Color badgeColor;
  const _FeedItem({
    required this.type,
    required this.event,
    required this.context,
    required this.title,
    required this.analysis,
    required this.badge,
    required this.badgeColor,
    required this.confidence,
  });
}

class _FeedItemCard extends StatelessWidget {
  final _FeedItem item;
  const _FeedItemCard({required this.item});

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 14, 16, 14),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Icon(Icons.bolt_rounded, size: 8, color: item.badgeColor),
                            const SizedBox(width: 2),
                            Text(item.badge, style: TextStyle(fontSize: 8, fontWeight: FontWeight.w700, color: item.badgeColor, letterSpacing: 0.5)),
                          ],
                        ),
                        const Spacer(),
                        Text(item.confidence,
                          style: TextStyle(
                            fontSize: 8, fontWeight: FontWeight.w700, letterSpacing: 0.3,
                            color: item.confidence == 'HIGH' ? _kGreen : const Color(0xFF4B5563),
                          )),
                      ],
                    ),
                    const SizedBox(height: 6),
                    Text(item.event,
                      style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 13, letterSpacing: -0.3, color: Colors.white),
                      maxLines: 1, overflow: TextOverflow.ellipsis),
                    const SizedBox(height: 2),
                    Text(item.context, style: const TextStyle(color: Color(0xFF6B7280), fontSize: 11)),
                    const SizedBox(height: 8),
                    Text(item.analysis,
                      style: const TextStyle(color: Color(0xFF9CA3AF), fontSize: 12, height: 1.5, letterSpacing: -0.1)),
                  ],
                ),
              ),
            ],
          ),
        ),
        Container(height: 0.5, color: Colors.white.withValues(alpha: 0.07)),
      ],
    );
  }
}

class _FeedFilterPill extends StatelessWidget {
  final String label;
  final _FeedFilter filter;
  final bool selected;
  final Color color;
  final VoidCallback onTap;
  const _FeedFilterPill({required this.label, required this.filter, required this.selected, required this.color, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 150),
        padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 6),
        decoration: BoxDecoration(
          border: Border(
            bottom: BorderSide(
              color: selected ? color : Colors.transparent,
              width: 1.5,
            ),
          ),
        ),
        child: Text(label,
          style: TextStyle(
            fontSize: 12,
            fontWeight: selected ? FontWeight.w600 : FontWeight.w400,
            color: selected ? color : const Color(0xFF666666),
          )),
      ),
    );
  }
}
