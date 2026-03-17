import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/app_state.dart';
import '../models/line_movement.dart';
import '../models/value_play.dart';

const _kTeal  = Color(0xFF10B981);
const _kAmber = Color(0xFFF59E0B);
const _kBlue  = Color(0xFF3B82F6);
const _kRed   = Color(0xFFEF4444);
const _kGreen = Color(0xFF10B981);
const _kBg    = Color(0xFF0A0A0A);
const _kCard  = Color(0xFF141414);

class AnalyticsScreen extends StatefulWidget {
  const AnalyticsScreen({super.key});
  @override
  State<AnalyticsScreen> createState() => _AnalyticsScreenState();
}

class _AnalyticsScreenState extends State<AnalyticsScreen>
    with SingleTickerProviderStateMixin {
  late TabController _tabs;

  @override
  void initState() {
    super.initState();
    _tabs = TabController(length: 3, vsync: this);
  }

  @override
  void dispose() {
    _tabs.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final state = context.watch<AppState>();
    return Scaffold(
      backgroundColor: _kBg,
      appBar: AppBar(
        backgroundColor: _kBg,
        toolbarHeight: 48,
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('Analytics', style: TextStyle(fontSize: 17, fontWeight: FontWeight.w700, letterSpacing: -0.5)),
            Text('Lines · ATS · Insights', style: TextStyle(fontSize: 10, color: Colors.grey[600], letterSpacing: 0.2)),
          ],
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh_rounded, size: 18),
            color: const Color(0xFF4B5563),
            onPressed: () => context.read<AppState>().refresh(),
          ),
        ],
        bottom: TabBar(
          controller: _tabs,
          indicatorColor: _kTeal,
          indicatorWeight: 2,
          indicatorSize: TabBarIndicatorSize.label,
          labelColor: _kTeal,
          unselectedLabelColor: const Color(0xFF4B5563),
          labelStyle: const TextStyle(fontSize: 11, fontWeight: FontWeight.w700, letterSpacing: 1.0),
          unselectedLabelStyle: const TextStyle(fontSize: 11, fontWeight: FontWeight.w500, letterSpacing: 0.8),
          tabs: const [Tab(text: 'LINES'), Tab(text: 'ATS RADAR'), Tab(text: 'INSIGHTS')],
        ),
      ),
      body: TabBarView(
        controller: _tabs,
        children: [
          _LinesTab(movements: state.lineMovements, loading: state.loading),
          _AtsRadarTab(movements: state.lineMovements),
          _InsightsTab(plays: state.valuePlays),
        ],
      ),
    );
  }
}

// ── Tab 1: Lines ──────────────────────────────────────────────────────────────

class _LinesTab extends StatelessWidget {
  final List<LineMovement> movements;
  final bool loading;
  const _LinesTab({required this.movements, required this.loading});

  @override
  Widget build(BuildContext context) {
    if (loading) return const Center(child: CircularProgressIndicator(color: _kTeal, strokeWidth: 2));
    if (movements.isEmpty) {
      return const Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.show_chart_rounded, color: Color(0xFF374151), size: 32),
            SizedBox(height: 12),
            Text('No line movement', style: TextStyle(color: Colors.white70, fontSize: 14, fontWeight: FontWeight.w600)),
            SizedBox(height: 4),
            Text('Steam moves will appear here', style: TextStyle(color: Color(0xFF4B5563), fontSize: 12)),
          ],
        ),
      );
    }
    return ListView.builder(
      padding: const EdgeInsets.only(bottom: 24),
      itemCount: movements.length,
      itemBuilder: (_, i) {
        final m = movements[i];
        final isUp = m.direction == 'up';
        final moveColor = isUp ? _kRed : _kTeal;
        return _LineMovementCard(m: m, moveColor: moveColor, isUp: isUp);
      },
    );
  }
}

class _LineMovementCard extends StatelessWidget {
  final LineMovement m;
  final Color moveColor;
  final bool isUp;
  const _LineMovementCard({required this.m, required this.moveColor, required this.isUp});

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 13, 16, 13),
          child: Row(
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(m.event,
                      style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13, letterSpacing: -0.2, color: Colors.white),
                      maxLines: 1, overflow: TextOverflow.ellipsis),
                    const SizedBox(height: 3),
                    Row(
                      children: [
                        Text(m.market, style: const TextStyle(color: Color(0xFF6B7280), fontSize: 11)),
                        const SizedBox(width: 6),
                        Text(isUp ? 'STEAM ↑' : 'SHARP ↓',
                          style: TextStyle(fontSize: 8, fontWeight: FontWeight.w700, color: moveColor, letterSpacing: 0.4)),
                      ],
                    ),
                  ],
                ),
              ),
              Column(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(isUp ? Icons.arrow_upward_rounded : Icons.arrow_downward_rounded, color: moveColor, size: 12),
                      const SizedBox(width: 2),
                      Text(m.movement.abs().toStringAsFixed(1),
                        style: TextStyle(color: moveColor, fontWeight: FontWeight.w700, fontSize: 16, letterSpacing: -0.4)),
                    ],
                  ),
                  const SizedBox(height: 2),
                  Text('${m.openLine.toStringAsFixed(1)} → ${m.currentLine.toStringAsFixed(1)}',
                    style: const TextStyle(color: Color(0xFF6B7280), fontSize: 10)),
                ],
              ),
            ],
          ),
        ),
        Container(height: 0.5, color: Colors.white.withValues(alpha: 0.06), margin: const EdgeInsets.only(left: 32)),
      ],
    );
  }
}

// ── Tab 2: ATS Radar ──────────────────────────────────────────────────────────

class _AtsRadarTab extends StatelessWidget {
  final List<LineMovement> movements;
  const _AtsRadarTab({required this.movements});

  @override
  Widget build(BuildContext context) {
    final targets = movements.where((m) => m.direction == 'down' && m.movement.abs() >= 1.0).toList();
    final fades   = movements.where((m) => m.direction == 'up'   && m.movement.abs() >= 1.0).toList();
    final neutral = movements.where((m) => m.movement.abs() < 1.0).toList();

    if (movements.isEmpty) {
      return const Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.radar_rounded, color: Color(0xFF374151), size: 36),
            SizedBox(height: 14),
            Text('Radar calibrating', style: TextStyle(color: Colors.white70, fontSize: 15, fontWeight: FontWeight.w600)),
            SizedBox(height: 6),
            Text('Line movement data will populate\nthe ATS radar', style: TextStyle(color: Color(0xFF4B5563), fontSize: 12), textAlign: TextAlign.center),
          ],
        ),
      );
    }

    return SingleChildScrollView(
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 32),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Padding(
            padding: EdgeInsets.all(12),
            child: Row(
              children: [
                Icon(Icons.radar_rounded, color: _kTeal, size: 13),
                SizedBox(width: 8),
                Expanded(
                  child: Text(
                    'ATS Radar classifies line moves: sharps driving reverse moves (TARGET) vs public steam (FADE).',
                    style: TextStyle(color: Color(0xFF6B7280), fontSize: 11, height: 1.4),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(child: _RadarColumn(label: 'TARGET', color: _kTeal, icon: Icons.check_circle_outline_rounded, items: targets)),
              const SizedBox(width: 8),
              Expanded(child: _RadarColumn(label: 'NEUTRAL', color: const Color(0xFF6B7280), icon: Icons.remove_circle_outline_rounded, items: neutral)),
              const SizedBox(width: 8),
              Expanded(child: _RadarColumn(label: 'FADE', color: _kRed, icon: Icons.cancel_outlined, items: fades)),
            ],
          ),
          const SizedBox(height: 20),
          const _SectionLabel('KEY NUMBERS', _kAmber),
          const SizedBox(height: 10),
          const _KeyNumbersCard(),
        ],
      ),
    );
  }
}

class _RadarColumn extends StatelessWidget {
  final String label;
  final Color color;
  final IconData icon;
  final List<LineMovement> items;
  const _RadarColumn({required this.label, required this.color, required this.icon, required this.items});

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.symmetric(vertical: 8),
          child: Column(
            children: [
              Icon(icon, color: color, size: 14),
              const SizedBox(height: 3),
              Text(label, style: TextStyle(fontSize: 8, fontWeight: FontWeight.w800, color: color, letterSpacing: 0.8)),
              Text('${items.length}', style: TextStyle(fontSize: 18, fontWeight: FontWeight.w700, color: color, letterSpacing: -0.5, height: 1.1)),
            ],
          ),
        ),
        ...items.take(5).map((m) => _RadarCard(m: m, color: color)),
        if (items.isEmpty)
          Padding(
            padding: const EdgeInsets.symmetric(vertical: 16),
            child: Text('—', textAlign: TextAlign.center, style: TextStyle(color: color.withValues(alpha: 0.3), fontSize: 14)),
          ),
      ],
    );
  }
}

class _RadarCard extends StatelessWidget {
  final LineMovement m;
  final Color color;
  const _RadarCard({required this.m, required this.color});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(8),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(m.event,
            style: const TextStyle(fontSize: 10, fontWeight: FontWeight.w600, color: Colors.white, letterSpacing: -0.1),
            maxLines: 2, overflow: TextOverflow.ellipsis),
          const SizedBox(height: 4),
          Text('${m.openLine.toStringAsFixed(1)}→${m.currentLine.toStringAsFixed(1)}',
            style: TextStyle(fontSize: 9, color: color, fontWeight: FontWeight.w600)),
        ],
      ),
    );
  }
}

class _KeyNumbersCard extends StatelessWidget {
  const _KeyNumbersCard();

  static const _numbers = [
    ('3', 'NFL', 'Field goal — most common winning margin in NFL history', 'critical'),
    ('7', 'NFL', 'TD + PAT — second most common margin, avoid buying through key #', 'critical'),
    ('10', 'NFL', 'FG + TD combination — important for totals and spreads', 'high'),
    ('2.5', 'NBA', 'Common threshold — sharp adjustments concentrate here', 'medium'),
    ('1', 'MLB', 'Single run — runline and first-five key number', 'medium'),
  ];

  @override
  Widget build(BuildContext context) {
    return Column(
      children: _numbers.map((kn) {
          final color = kn.$4 == 'critical' ? _kRed : kn.$4 == 'high' ? _kAmber : const Color(0xFF6B7280);
          return Column(
            children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(14, 11, 14, 11),
                child: Row(
                  children: [
                    SizedBox(
                      width: 34,
                      child: Text(kn.$1, style: TextStyle(fontSize: 13, fontWeight: FontWeight.w800, color: color, letterSpacing: -0.4)),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              Text(kn.$2, style: TextStyle(fontSize: 8, fontWeight: FontWeight.w700, color: color, letterSpacing: 0.3)),
                              const SizedBox(width: 5),
                              Text(kn.$4.toUpperCase(), style: const TextStyle(fontSize: 8, color: Color(0xFF4B5563), letterSpacing: 0.3)),
                            ],
                          ),
                          const SizedBox(height: 3),
                          Text(kn.$3, style: const TextStyle(fontSize: 11, color: Color(0xFF9CA3AF), height: 1.35)),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
              Container(height: 0.5, color: Colors.white.withValues(alpha: 0.05)),
            ],
          );
        }).toList(),
    );
  }
}

// ── Tab 3: Insights ───────────────────────────────────────────────────────────

class _InsightsTab extends StatelessWidget {
  final List<ValuePlay> plays;
  const _InsightsTab({required this.plays});

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 32),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _AgenticBriefCard(plays: plays),
          const SizedBox(height: 20),
          const _SectionLabel('SITUATIONAL EDGES', _kBlue),
          const SizedBox(height: 10),
          const _SituationalEdgesGrid(),
          const SizedBox(height: 20),
          const _SectionLabel('MARKET METRICS', _kTeal),
          const SizedBox(height: 10),
          _MarketMetricsCard(plays: plays),
        ],
      ),
    );
  }
}

class _AgenticBriefCard extends StatelessWidget {
  final List<ValuePlay> plays;
  const _AgenticBriefCard({required this.plays});

  @override
  Widget build(BuildContext context) {
    final premiumCount = plays.where((p) => p.expectedValue * 100 >= 5).length;
    final hasEdge = premiumCount > 0;
    return Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(14, 12, 14, 12),
            child: Row(
              children: [
                const Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(Icons.auto_awesome_rounded, size: 10, color: _kTeal),
                    SizedBox(width: 4),
                    Text('AGENTIC BRIEF', style: TextStyle(fontSize: 9, fontWeight: FontWeight.w700, color: _kTeal, letterSpacing: 0.6)),
                  ],
                ),
                const Spacer(),
                Text('Today', style: TextStyle(fontSize: 10, color: Colors.grey[600])),
              ],
            ),
          ),
          Padding(
            padding: const EdgeInsets.all(14),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  hasEdge
                      ? 'Today\'s slate shows $premiumCount strong-edge signal${premiumCount != 1 ? 's' : ''} with EV above 5%. '
                        'Market conditions suggest sharp positioning. '
                        'Prioritize CLV retention — bet early where line movement confirms your model edge.'
                      : 'Markets are currently efficient with no high-conviction edges detected. '
                        'Monitor for steam moves and reverse line movement. '
                        'Maintain discipline: no edge = no bet. Wait for the market to present opportunity.',
                  style: const TextStyle(fontSize: 13, color: Color(0xFFD1D5DB), height: 1.6, letterSpacing: -0.1),
                ),
                const SizedBox(height: 12),
                Row(
                  children: [
                    const _MetaBadge(label: 'CLV TARGET', value: '> +1.5%', color: _kTeal),
                    const SizedBox(width: 6),
                    _MetaBadge(label: 'PHASE', value: hasEdge ? 'Active' : 'Quiet', color: _kBlue),
                    const SizedBox(width: 6),
                    _MetaBadge(label: 'SIGNALS', value: '${plays.length}', color: _kAmber),
                  ],
                ),
              ],
            ),
          ),
        ],
    );
  }
}

class _MetaBadge extends StatelessWidget {
  final String label, value;
  final Color color;
  const _MetaBadge({required this.label, required this.value, required this.color});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 4),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label, style: TextStyle(fontSize: 7, fontWeight: FontWeight.w700, color: color.withValues(alpha: 0.7), letterSpacing: 0.4)),
          Text(value, style: TextStyle(fontSize: 11, fontWeight: FontWeight.w700, color: color, letterSpacing: -0.2)),
        ],
      ),
    );
  }
}

class _SituationalEdgesGrid extends StatelessWidget {
  const _SituationalEdgesGrid();

  static const _edges = [
    _SituationalEdge('Home Dog', 'Home underdogs receiving < 40% of public tickets historically outperform ATS', '+4.2%', 'NFL/NBA', _kTeal),
    _SituationalEdge('Reverse Line Move', 'Line moves opposite to public betting % — indicates sharp professional money', '+3.8%', 'ALL', _kBlue),
    _SituationalEdge('Back-to-Back', 'Teams on second game in 2 days underperform ATS, especially on the road', '-2.1%', 'NBA', _kRed),
    _SituationalEdge('Post-Bye', 'Teams coming off bye week have extra prep and rest advantage', '+2.9%', 'NFL', _kGreen),
    _SituationalEdge('Divisional Dog', 'Division underdogs know opponents intimately — familiarity edge', '+2.4%', 'NFL', _kAmber),
    _SituationalEdge('Primetime Fade', 'Primetime favorites attract heavy public money — sharps fade overpriced dogs', '+1.9%', 'NFL', _kBlue),
  ];

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        for (int i = 0; i < _edges.length; i += 2)
          Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: Row(
              children: [
                Expanded(child: _EdgeCard(edge: _edges[i])),
                const SizedBox(width: 8),
                if (i + 1 < _edges.length) Expanded(child: _EdgeCard(edge: _edges[i + 1])) else const Expanded(child: SizedBox()),
              ],
            ),
          ),
      ],
    );
  }
}

class _SituationalEdge {
  final String title, description, edge, sport;
  final Color color;
  const _SituationalEdge(this.title, this.description, this.edge, this.sport, this.color);
}

class _EdgeCard extends StatelessWidget {
  final _SituationalEdge edge;
  const _EdgeCard({required this.edge});

  @override
  Widget build(BuildContext context) {
    final isPositive = edge.edge.startsWith('+');
    return Padding(
      padding: const EdgeInsets.all(12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(edge.sport, style: TextStyle(fontSize: 7.5, fontWeight: FontWeight.w700, color: edge.color, letterSpacing: 0.3)),
              Text(edge.edge, style: TextStyle(fontSize: 13, fontWeight: FontWeight.w800, color: isPositive ? _kGreen : _kRed, letterSpacing: -0.3)),
            ],
          ),
          const SizedBox(height: 7),
          Text(edge.title, style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: Colors.white, letterSpacing: -0.2)),
          const SizedBox(height: 4),
          Text(edge.description, style: const TextStyle(fontSize: 10, color: Color(0xFF6B7280), height: 1.4)),
        ],
      ),
    );
  }
}

class _MarketMetricsCard extends StatelessWidget {
  final List<ValuePlay> plays;
  const _MarketMetricsCard({required this.plays});

  @override
  Widget build(BuildContext context) {
    final avgEv = plays.isEmpty ? 0.0 : plays.map((p) => p.expectedValue * 100).reduce((a, b) => a + b) / plays.length;
    final strongEdge = plays.where((p) => p.expectedValue * 100 >= 5).length;
    final positiveEv = plays.where((p) => p.expectedValue > 0).length;
    return Column(
        children: [
          _MetricRow('Average EV', '${avgEv >= 0 ? '+' : ''}${avgEv.toStringAsFixed(2)}%', avgEv >= 0 ? _kTeal : _kRed),
          Container(height: 0.5, color: Colors.white.withValues(alpha: 0.05)),
          _MetricRow('Strong Edge Signals', '$strongEdge', _kBlue),
          Container(height: 0.5, color: Colors.white.withValues(alpha: 0.05)),
          _MetricRow('Positive EV Plays', '$positiveEv / ${plays.length}', _kGreen),
          Container(height: 0.5, color: Colors.white.withValues(alpha: 0.05)),
          _MetricRow('Market State', plays.isEmpty ? '—' : strongEdge > 3 ? 'Inefficient' : 'Efficient', strongEdge > 3 ? _kAmber : const Color(0xFF6B7280)),
        ],
    );
  }
}

class _MetricRow extends StatelessWidget {
  final String label, value;
  final Color color;
  const _MetricRow(this.label, this.value, this.color);

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(14, 11, 14, 11),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: const TextStyle(color: Color(0xFF9CA3AF), fontSize: 12)),
          Text(value, style: TextStyle(color: color, fontSize: 13, fontWeight: FontWeight.w700, letterSpacing: -0.2)),
        ],
      ),
    );
  }
}

// ── Shared utilities ──────────────────────────────────────────────────────────

class _SectionLabel extends StatelessWidget {
  final String text;
  final Color accent;
  const _SectionLabel(this.text, this.accent);

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Container(width: 2, height: 12, decoration: BoxDecoration(color: accent, borderRadius: BorderRadius.circular(1))),
        const SizedBox(width: 7),
        Text(text, style: const TextStyle(fontSize: 10, fontWeight: FontWeight.w700, color: Color(0xFF6B7280), letterSpacing: 1.3)),
      ],
    );
  }
}
