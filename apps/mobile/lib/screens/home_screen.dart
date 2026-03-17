import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:fl_chart/fl_chart.dart';
import '../providers/app_state.dart';
import '../models/value_play.dart';
import '../models/arbitrage_opportunity.dart';

const _kTeal  = Color(0xFF10B981);
const _kAmber = Color(0xFFF59E0B);
const _kBlue  = Color(0xFF3B82F6);
const _kCard  = Color(0xFF141414);
const _kBg    = Color(0xFF0A0A0A);

class HomeScreen extends StatelessWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final state = context.watch<AppState>();
    if (state.loading) {
      return const Scaffold(
        backgroundColor: _kBg,
        body: Center(child: CircularProgressIndicator(color: _kTeal, strokeWidth: 2)),
      );
    }
    if (state.error != null) {
      return Scaffold(
        backgroundColor: _kBg,
        body: _ErrorView(error: state.error!, onRetry: () => context.read<AppState>().refresh()),
      );
    }
    final highEv = state.valuePlays.where((p) => p.expectedValue * 100 >= 3).length;
    return Scaffold(
      backgroundColor: _kBg,
      body: RefreshIndicator(
        color: _kTeal,
        backgroundColor: _kCard,
        onRefresh: () => context.read<AppState>().refresh(),
        child: CustomScrollView(
          physics: const AlwaysScrollableScrollPhysics(),
          slivers: [
            _HomeAppBar(),
            SliverPadding(
              padding: const EdgeInsets.fromLTRB(16, 0, 16, 32),
              sliver: SliverList(
                delegate: SliverChildListDelegate([
                  _GreetingHero(
                    signalCount: state.valuePlays.length + state.arbitrage.length,
                    highEvCount: highEv,
                  ),
                  const SizedBox(height: 16),
                  _SummaryRow(
                    valuePlaysCount: state.valuePlays.length,
                    arbCount: state.arbitrage.length,
                    highEvCount: highEv,
                  ),
                  const SizedBox(height: 20),
                  const _SectionHeader(
                    label: 'ROI CURVE',
                    accent: _kTeal,
                    icon: Icons.show_chart_rounded,
                    live: false,
                  ),
                  const SizedBox(height: 10),
                  const _RoiCurveChart(),
                  const SizedBox(height: 20),
                  const _SectionHeader(
                    label: 'BANKROLL CURVE',
                    accent: _kBlue,
                    icon: Icons.account_balance_wallet_rounded,
                    live: false,
                  ),
                  const SizedBox(height: 10),
                  const _BankrollCurveChart(),
                  const SizedBox(height: 20),
                  if (state.valuePlays.isNotEmpty) ...[
                    const _SectionHeader(
                      label: 'SHARP SPOTS',
                      accent: _kBlue,
                      icon: Icons.bolt_rounded,
                      live: true,
                    ),
                    const SizedBox(height: 10),
                    _SharpSpotsRow(plays: state.valuePlays.take(5).toList()),
                    const SizedBox(height: 20),
                  ],
                  _SectionHeader(
                    label: 'TOP VALUE PLAYS',
                    accent: _kTeal,
                    icon: Icons.trending_up_rounded,
                    live: state.valuePlays.isNotEmpty,
                  ),
                  const SizedBox(height: 10),
                  if (state.valuePlays.isEmpty)
                    const _EmptyState(
                      icon: Icons.analytics_outlined,
                      title: 'No signals detected',
                      subtitle: 'Value opportunities will appear here',
                    )
                  else
                    ...state.valuePlays.take(3).map((p) => _ValueRow(play: p)),
                  const SizedBox(height: 20),
                  _SectionHeader(
                    label: 'ARBITRAGE ALERTS',
                    accent: _kAmber,
                    icon: Icons.compare_arrows_rounded,
                    live: state.arbitrage.isNotEmpty,
                  ),
                  const SizedBox(height: 10),
                  if (state.arbitrage.isEmpty)
                    const _EmptyState(
                      icon: Icons.swap_horiz_outlined,
                      title: 'No arbitrage found',
                      subtitle: 'Market inefficiencies will appear here',
                    )
                  else
                    ...state.arbitrage.take(3).map((a) => _ArbRow(arb: a)),
                  const SizedBox(height: 8),
                ]),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// ── App bar ───────────────────────────────────────────────────────────────────

class _HomeAppBar extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return SliverAppBar(
      expandedHeight: 116,
      pinned: true,
      backgroundColor: _kBg,
      surfaceTintColor: Colors.transparent,
      flexibleSpace: FlexibleSpaceBar(
        titlePadding: const EdgeInsets.fromLTRB(16, 0, 16, 14),
        title: Row(
          crossAxisAlignment: CrossAxisAlignment.end,
          children: [
            Container(
              width: 28,
              height: 28,
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(7),
                border: Border.all(
                  color: _kTeal.withValues(alpha: 0.3),
                  width: 0.5,
                ),
              ),
              child: const Icon(Icons.show_chart_rounded, color: _kTeal, size: 16),
            ),
            const SizedBox(width: 9),
            Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'SharpEdge',
                  style: TextStyle(
                    fontSize: 17,
                    fontWeight: FontWeight.w700,
                    color: Colors.white,
                    letterSpacing: -0.5,
                    height: 1.1,
                  ),
                ),
                Text(
                  'INTELLIGENCE PLATFORM',
                  style: TextStyle(
                    fontSize: 8,
                    fontWeight: FontWeight.w600,
                    color: Colors.grey[600],
                    letterSpacing: 1.0,
                  ),
                ),
              ],
            ),
          ],
        ),
        background: Stack(
          children: [
            // Deep gradient
            Container(
              decoration: const BoxDecoration(
                gradient: LinearGradient(
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                  colors: [Color(0xFF0A0A0A), Color(0xFF0A0A0A)],
                ),
              ),
            ),
            // Faint teal glow top-left
            Positioned(
              top: -30,
              left: -30,
              width: 180,
              height: 180,
              child: Container(
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  gradient: RadialGradient(
                    colors: [
                      _kTeal.withValues(alpha: 0.05),
                      Colors.transparent,
                    ],
                  ),
                ),
              ),
            ),
            // Refresh button
            Positioned(
              top: 6,
              right: 4,
              child: Builder(
                builder: (ctx) => IconButton(
                  icon: const Icon(Icons.refresh_rounded,
                      color: Color(0xFF374151), size: 20),
                  onPressed: () => ctx.read<AppState>().refresh(),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// ── Greeting hero ─────────────────────────────────────────────────────────────

class _GreetingHero extends StatelessWidget {
  final int signalCount;
  final int highEvCount;

  const _GreetingHero({
    required this.signalCount,
    required this.highEvCount,
  });

  String get _greeting {
    final hour = DateTime.now().hour;
    if (hour < 12) return 'Good morning.';
    if (hour < 17) return 'Good afternoon.';
    return 'Good evening.';
  }

  @override
  Widget build(BuildContext context) {
    return Stack(
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(18, 18, 18, 18),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  _greeting,
                  style: TextStyle(
                    fontSize: 13,
                    fontWeight: FontWeight.w500,
                    color: Colors.grey[600],
                    letterSpacing: 0.1,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  signalCount == 0
                      ? 'No active signals'
                      : '$signalCount active signals',
                  style: const TextStyle(
                    fontSize: 22,
                    fontWeight: FontWeight.w700,
                    color: Colors.white,
                    letterSpacing: -0.8,
                    height: 1.1,
                  ),
                ),
                const SizedBox(height: 12),
                Row(
                  children: [
                    if (highEvCount > 0) ...[
                      Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 10, vertical: 4),
                        decoration: BoxDecoration(
                          color: _kTeal.withValues(alpha: 0.1),
                          borderRadius: BorderRadius.circular(20),
                          border: Border.all(
                            color: _kTeal.withValues(alpha: 0.3),
                            width: 1,
                          ),
                        ),
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            const Icon(Icons.bolt_rounded, color: _kTeal, size: 11),
                            const SizedBox(width: 3),
                            Text(
                              '$highEvCount HIGH EV',
                              style: const TextStyle(
                                fontSize: 10,
                                fontWeight: FontWeight.w700,
                                color: _kTeal,
                                letterSpacing: 0.5,
                              ),
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(width: 8),
                    ],
                    Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 10, vertical: 4),
                      decoration: BoxDecoration(
                        color: Colors.white.withValues(alpha: 0.04),
                        borderRadius: BorderRadius.circular(20),
                        border: Border.all(
                          color: Colors.white.withValues(alpha: 0.08),
                          width: 1,
                        ),
                      ),
                      child: const Text(
                        'MARKETS OPEN',
                        style: TextStyle(
                          fontSize: 10,
                          fontWeight: FontWeight.w600,
                          color: Color(0xFF6B7280),
                          letterSpacing: 0.5,
                        ),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ],
    );
  }
}

// ── Summary row ───────────────────────────────────────────────────────────────

class _SummaryRow extends StatelessWidget {
  final int valuePlaysCount;
  final int arbCount;
  final int highEvCount;

  const _SummaryRow({
    required this.valuePlaysCount,
    required this.arbCount,
    required this.highEvCount,
  });

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Expanded(
          child: _SummaryCard(
            value: '$valuePlaysCount',
            label: 'Value Plays',
            color: _kTeal,
            icon: Icons.trending_up_rounded,
          ),
        ),
        const SizedBox(width: 10),
        Expanded(
          child: _SummaryCard(
            value: '$arbCount',
            label: 'Arb Opps',
            color: _kAmber,
            icon: Icons.compare_arrows_rounded,
          ),
        ),
        const SizedBox(width: 10),
        Expanded(
          child: _SummaryCard(
            value: '$highEvCount',
            label: 'High EV',
            color: _kBlue,
            icon: Icons.bolt_rounded,
          ),
        ),
      ],
    );
  }
}

class _SummaryCard extends StatelessWidget {
  final String value;
  final String label;
  final Color color;
  final IconData icon;
  const _SummaryCard({
    required this.value,
    required this.label,
    required this.color,
    required this.icon,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(14, 14, 14, 14),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, color: color, size: 16),
            const SizedBox(height: 10),
            Text(
              value,
              style: TextStyle(
                fontSize: 30,
                fontWeight: FontWeight.w600,
                color: color,
                height: 1,
                letterSpacing: -1.2,
              ),
            ),
            const SizedBox(height: 4),
            Text(
              label,
              style: const TextStyle(
                fontSize: 10,
                fontWeight: FontWeight.w400,
                color: Color(0xFF555555),
                letterSpacing: 0.1,
              ),
            ),
          ],
      ),
    );
  }
}

// ── Section header ────────────────────────────────────────────────────────────

class _SectionHeader extends StatelessWidget {
  final String label;
  final Color accent;
  final IconData icon;
  final bool live;

  const _SectionHeader({
    required this.label,
    required this.accent,
    required this.icon,
    this.live = false,
  });

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Container(
          width: 2, height: 14,
          decoration: BoxDecoration(
            color: accent,
            borderRadius: BorderRadius.circular(1),
          ),
        ),
        const SizedBox(width: 8),
        Icon(icon, size: 13, color: accent),
        const SizedBox(width: 6),
        Text(
          label,
          style: const TextStyle(
            fontSize: 10,
            fontWeight: FontWeight.w700,
            color: Color(0xFF6B7280),
            letterSpacing: 1.4,
          ),
        ),
        if (live) ...[
          const SizedBox(width: 8),
          Container(
            width: 5, height: 5,
            decoration: BoxDecoration(
              color: accent,
              shape: BoxShape.circle,
              boxShadow: [
                BoxShadow(
                  color: accent.withValues(alpha: 0.6),
                  blurRadius: 5,
                  spreadRadius: 1,
                ),
              ],
            ),
          ),
          const SizedBox(width: 4),
          Text(
            'LIVE',
            style: TextStyle(
              fontSize: 9,
              fontWeight: FontWeight.w700,
              color: accent,
              letterSpacing: 1.0,
            ),
          ),
        ],
      ],
    );
  }
}

// ── Inline cards ──────────────────────────────────────────────────────────────

class _ValueRow extends StatelessWidget {
  final ValuePlay play;
  const _ValueRow({required this.play});

  @override
  Widget build(BuildContext context) {
    final ev = play.expectedValue * 100;
    final color = ev >= 0 ? _kTeal : const Color(0xFFEF4444);
    return _InlineCard(
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  play.event,
                  style: const TextStyle(
                    fontWeight: FontWeight.w600,
                    fontSize: 13,
                    letterSpacing: -0.2,
                    color: Colors.white,
                  ),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
                const SizedBox(height: 3),
                Text(
                  '${play.market}  ·  ${play.book}',
                  style: const TextStyle(color: Color(0xFF6B7280), fontSize: 11),
                ),
              ],
            ),
          ),
          Column(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Text(
                '${ev >= 0 ? '+' : ''}${ev.toStringAsFixed(1)}%',
                style: TextStyle(
                  color: color,
                  fontWeight: FontWeight.w700,
                  fontSize: 15,
                  letterSpacing: -0.3,
                ),
              ),
              const Text(
                'EV',
                style: TextStyle(
                  color: Color(0xFF4B5563),
                  fontSize: 10,
                  fontWeight: FontWeight.w500,
                  letterSpacing: 0.5,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _ArbRow extends StatelessWidget {
  final ArbitrageOpportunity arb;
  const _ArbRow({required this.arb});

  @override
  Widget build(BuildContext context) {
    return _InlineCard(
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  arb.event,
                  style: const TextStyle(
                    fontWeight: FontWeight.w600,
                    fontSize: 13,
                    letterSpacing: -0.2,
                    color: Colors.white,
                  ),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
                const SizedBox(height: 3),
                Text(
                  arb.market,
                  style: const TextStyle(color: Color(0xFF6B7280), fontSize: 11),
                ),
              ],
            ),
          ),
          Column(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Text(
                '+${arb.profitPercent.toStringAsFixed(2)}%',
                style: const TextStyle(
                  color: _kAmber,
                  fontWeight: FontWeight.w700,
                  fontSize: 15,
                  letterSpacing: -0.3,
                ),
              ),
              const Text(
                'PROFIT',
                style: TextStyle(
                  color: Color(0xFF4B5563),
                  fontSize: 10,
                  fontWeight: FontWeight.w500,
                  letterSpacing: 0.5,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

// ── Shared primitives ─────────────────────────────────────────────────────────

class _InlineCard extends StatelessWidget {
  final Widget child;

  const _InlineCard({
    required this.child,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.symmetric(vertical: 12),
          child: child,
        ),
        Container(
          height: 0.5,
          color: Colors.white.withValues(alpha: 0.07),
        ),
      ],
    );
  }
}

// ── Sharp spots ───────────────────────────────────────────────────────────────

class _SharpSpotsRow extends StatelessWidget {
  final List<ValuePlay> plays;
  const _SharpSpotsRow({required this.plays});

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 114,
      child: ListView.builder(
        scrollDirection: Axis.horizontal,
        padding: EdgeInsets.zero,
        itemCount: plays.length,
        itemBuilder: (_, i) => _MatchupCard(play: plays[i]),
      ),
    );
  }
}

class _MatchupCard extends StatelessWidget {
  final ValuePlay play;
  const _MatchupCard({required this.play});

  @override
  Widget build(BuildContext context) {
    final ev = play.expectedValue * 100;
    final Color color;
    final String edgeLabel;
    if (ev >= 5) {
      color = _kTeal;
      edgeLabel = 'STRONG EDGE';
    } else if (ev >= 2) {
      color = _kBlue;
      edgeLabel = 'MODERATE';
    } else {
      color = const Color(0xFF6B7280);
      edgeLabel = 'NEUTRAL';
    }

    return Container(
      width: 164,
      margin: const EdgeInsets.only(right: 10),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: Colors.white.withValues(alpha: 0.05), width: 0.5),
      ),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(Icons.bolt_rounded, size: 8, color: color),
                const SizedBox(width: 2),
                Text(
                  edgeLabel,
                  style: TextStyle(
                    fontSize: 7.5,
                    fontWeight: FontWeight.w700,
                    color: color,
                    letterSpacing: 0.4,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 7),
            Text(
              play.event,
              style: const TextStyle(
                fontSize: 11,
                fontWeight: FontWeight.w600,
                color: Colors.white,
                letterSpacing: -0.2,
                height: 1.25,
              ),
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
            ),
            const Spacer(),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      '${ev >= 0 ? '+' : ''}${ev.toStringAsFixed(1)}%',
                      style: TextStyle(
                        fontSize: 17,
                        fontWeight: FontWeight.w700,
                        color: color,
                        letterSpacing: -0.4,
                        height: 1,
                      ),
                    ),
                    const Text(
                      'EV',
                      style: TextStyle(
                        fontSize: 8,
                        fontWeight: FontWeight.w600,
                        color: Color(0xFF4B5563),
                        letterSpacing: 0.5,
                      ),
                    ),
                  ],
                ),
                Text(
                  play.book,
                  style: const TextStyle(
                    fontSize: 9,
                    color: Color(0xFF555555),
                    fontWeight: FontWeight.w500,
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

// ── ROI Curve ─────────────────────────────────────────────────────────────────

class _RoiCurveChart extends StatelessWidget {
  const _RoiCurveChart();

  static const _data = [
    FlSpot(0, 0),
    FlSpot(0.5, 1.2),
    FlSpot(1, 2.4),
    FlSpot(1.5, 3.3),
    FlSpot(2, 4.2),
    FlSpot(2.5, 5.4),
    FlSpot(3, 6.0),
    FlSpot(3.5, 6.6),
    FlSpot(4, 7.1),
  ];

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 160,
      child: Padding(
        padding: const EdgeInsets.fromLTRB(8, 16, 16, 8),
        child: LineChart(
          LineChartData(
            minX: 0,
            maxX: 4,
            minY: 0,
            maxY: 9,
            clipData: const FlClipData.all(),
            gridData: FlGridData(
              show: true,
              drawVerticalLine: false,
              horizontalInterval: 2,
              getDrawingHorizontalLine: (_) => FlLine(
                color: Colors.white.withValues(alpha: 0.05),
                strokeWidth: 0.5,
              ),
            ),
            borderData: FlBorderData(show: false),
            titlesData: FlTitlesData(
              leftTitles: AxisTitles(
                sideTitles: SideTitles(
                  showTitles: true,
                  interval: 2,
                  reservedSize: 32,
                  getTitlesWidget: (v, _) => Text(
                    '${v.toInt()}%',
                    style: const TextStyle(
                      color: Color(0xFF4B5563),
                      fontSize: 9,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ),
              ),
              bottomTitles: AxisTitles(
                sideTitles: SideTitles(
                  showTitles: true,
                  interval: 2,
                  reservedSize: 20,
                  getTitlesWidget: (v, _) {
                    final labels = {0.0: 'Jan', 2.0: 'Feb', 4.0: 'Mar'};
                    final label = labels[v];
                    if (label == null) return const SizedBox.shrink();
                    return Text(
                      label,
                      style: const TextStyle(
                        color: Color(0xFF4B5563),
                        fontSize: 9,
                        fontWeight: FontWeight.w500,
                      ),
                    );
                  },
                ),
              ),
              rightTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
              topTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
            ),
            lineBarsData: [
              LineChartBarData(
                spots: _data,
                isCurved: true,
                curveSmoothness: 0.35,
                color: _kTeal,
                barWidth: 2,
                isStrokeCapRound: true,
                dotData: const FlDotData(show: false),
                belowBarData: BarAreaData(
                  show: true,
                  gradient: LinearGradient(
                    begin: Alignment.topCenter,
                    end: Alignment.bottomCenter,
                    colors: [
                      _kTeal.withValues(alpha: 0.28),
                      _kTeal.withValues(alpha: 0.0),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

// ── Bankroll Curve ────────────────────────────────────────────────────────────

class _BankrollCurveChart extends StatelessWidget {
  const _BankrollCurveChart();

  static const _data = [
    FlSpot(0, 1000),
    FlSpot(0.5, 1008),
    FlSpot(1, 1020),
    FlSpot(1.5, 1031),
    FlSpot(2, 1042),
    FlSpot(2.5, 1072),
    FlSpot(3, 1090),
    FlSpot(3.5, 1103),
    FlSpot(4, 1113),
  ];

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 160,
      child: Padding(
        padding: const EdgeInsets.fromLTRB(8, 16, 16, 8),
        child: LineChart(
          LineChartData(
            minX: 0,
            maxX: 4,
            minY: 0,
            maxY: 1300,
            clipData: const FlClipData.all(),
            gridData: FlGridData(
              show: true,
              drawVerticalLine: false,
              horizontalInterval: 300,
              getDrawingHorizontalLine: (_) => FlLine(
                color: Colors.white.withValues(alpha: 0.05),
                strokeWidth: 0.5,
              ),
            ),
            borderData: FlBorderData(show: false),
            titlesData: FlTitlesData(
              leftTitles: AxisTitles(
                sideTitles: SideTitles(
                  showTitles: true,
                  interval: 300,
                  reservedSize: 40,
                  getTitlesWidget: (v, _) {
                    if (v == 0) {
                      return const Text(
                        '\$0',
                        style: TextStyle(color: Color(0xFF4B5563), fontSize: 9, fontWeight: FontWeight.w500),
                      );
                    }
                    return Text(
                      '\$${v.toInt()}',
                      style: const TextStyle(color: Color(0xFF4B5563), fontSize: 9, fontWeight: FontWeight.w500),
                    );
                  },
                ),
              ),
              bottomTitles: AxisTitles(
                sideTitles: SideTitles(
                  showTitles: true,
                  interval: 2,
                  reservedSize: 20,
                  getTitlesWidget: (v, _) {
                    final labels = {0.0: 'Jan', 2.0: 'Feb', 4.0: 'Mar'};
                    final label = labels[v];
                    if (label == null) return const SizedBox.shrink();
                    return Text(
                      label,
                      style: const TextStyle(color: Color(0xFF4B5563), fontSize: 9, fontWeight: FontWeight.w500),
                    );
                  },
                ),
              ),
              rightTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
              topTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
            ),
            lineBarsData: [
              LineChartBarData(
                spots: _data,
                isCurved: true,
                curveSmoothness: 0.35,
                color: _kBlue,
                barWidth: 2,
                isStrokeCapRound: true,
                dotData: const FlDotData(show: false),
                belowBarData: BarAreaData(
                  show: true,
                  gradient: LinearGradient(
                    begin: Alignment.topCenter,
                    end: Alignment.bottomCenter,
                    colors: [
                      _kBlue.withValues(alpha: 0.28),
                      _kBlue.withValues(alpha: 0.0),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _EmptyState extends StatelessWidget {
  final IconData icon;
  final String title;
  final String subtitle;

  const _EmptyState({
    required this.icon,
    required this.title,
    required this.subtitle,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(vertical: 24, horizontal: 16),
      decoration: BoxDecoration(
        color: _kCard,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(
          color: Colors.white.withValues(alpha: 0.06),
          width: 0.5,
        ),
      ),
      child: Column(
        children: [
          Icon(icon, color: const Color(0xFF374151), size: 28),
          const SizedBox(height: 10),
          Text(
            title,
            style: const TextStyle(
              color: Colors.white70,
              fontSize: 13,
              fontWeight: FontWeight.w600,
              letterSpacing: -0.2,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            subtitle,
            style: const TextStyle(color: Color(0xFF4B5563), fontSize: 11),
            textAlign: TextAlign.center,
          ),
        ],
      ),
    );
  }
}

class _ErrorView extends StatelessWidget {
  final String error;
  final VoidCallback onRetry;

  const _ErrorView({required this.error, required this.onRetry});

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.wifi_off_rounded, color: Color(0xFFEF4444), size: 44),
            const SizedBox(height: 16),
            const Text(
              'Unable to connect',
              style: TextStyle(
                fontSize: 16,
                fontWeight: FontWeight.w700,
                letterSpacing: -0.3,
              ),
            ),
            const SizedBox(height: 6),
            Text(
              error,
              style: const TextStyle(color: Color(0xFF6B7280), fontSize: 12),
              textAlign: TextAlign.center,
              maxLines: 3,
              overflow: TextOverflow.ellipsis,
            ),
            const SizedBox(height: 24),
            FilledButton.icon(
              style: FilledButton.styleFrom(
                backgroundColor: _kTeal,
                foregroundColor: Colors.black,
                padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 10),
                textStyle: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600),
              ),
              onPressed: onRetry,
              icon: const Icon(Icons.refresh_rounded, size: 16),
              label: const Text('Retry'),
            ),
          ],
        ),
      ),
    );
  }
}
