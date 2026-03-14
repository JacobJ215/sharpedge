import 'package:flutter/material.dart';
import 'package:fl_chart/fl_chart.dart';
import 'package:provider/provider.dart';
import '../providers/app_state.dart';
import '../services/api_service.dart';
import '../widgets/stat_chip.dart';

const _kTeal  = Color(0xFF00D4AA);
const _kRed   = Color(0xFFEF4444);
const _kBlue  = Color(0xFF3B82F6);
const _kAmber = Color(0xFFF59E0B);
const _kBg    = Color(0xFF0A0A0A);
const _kCard  = Color(0xFF141414);

final _apiService = ApiService();

class BankrollScreen extends StatefulWidget {
  const BankrollScreen({super.key});

  @override
  State<BankrollScreen> createState() => _BankrollScreenState();
}

class _BankrollScreenState extends State<BankrollScreen> {
  Map<String, dynamic>? _portfolio;
  bool _loading = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadPortfolio();
  }

  Future<void> _loadPortfolio() async {
    final appState = context.read<AppState>();
    if (!appState.isAuthenticated ||
        appState.userId == null ||
        appState.authToken == null) {
      setState(() { _portfolio = null; _error = null; _loading = false; });
      return;
    }
    setState(() { _loading = true; _error = null; });
    try {
      final data = await _apiService.getPortfolio(
          appState.userId!, appState.authToken!);
      setState(() { _portfolio = data; });
    } catch (e) {
      setState(() { _error = e.toString(); });
    } finally {
      setState(() { _loading = false; });
    }
  }

  @override
  Widget build(BuildContext context) {
    final portfolio = _portfolio;
    final roi = (portfolio?['roi'] as num?)?.toDouble() ?? 0.0;
    final roiColor = roi >= 0 ? _kTeal : _kRed;

    return Scaffold(
      backgroundColor: _kBg,
      appBar: AppBar(
        backgroundColor: _kBg,
        toolbarHeight: 56,
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Portfolio',
              style: TextStyle(
                fontSize: 17,
                fontWeight: FontWeight.w700,
                letterSpacing: -0.5,
              ),
            ),
            Text(
              portfolio == null
                  ? 'Performance tracker'
                  : 'ROI ${roi >= 0 ? '+' : ''}${roi.toStringAsFixed(1)}%',
              style: TextStyle(
                fontSize: 11,
                color: portfolio == null ? const Color(0xFF6B7280) : roiColor,
                letterSpacing: 0.1,
                fontWeight: FontWeight.w500,
              ),
            ),
          ],
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh_rounded, size: 18),
            onPressed: _loadPortfolio,
            color: const Color(0xFF4B5563),
          ),
        ],
      ),
      body: _body(),
    );
  }

  Widget _body() {
    if (_loading) {
      return const Center(
        child: CircularProgressIndicator(color: _kTeal, strokeWidth: 2),
      );
    }
    if (_error != null) {
      return Center(
        child: Text(
          'Error: $_error',
          style: const TextStyle(color: _kRed, fontSize: 13),
        ),
      );
    }
    final p = _portfolio;
    if (p == null) {
      return _EmptyState();
    }

    final roi        = (p['roi'] as num?)?.toDouble() ?? 0.0;
    final winRate    = (p['win_rate'] as num?)?.toDouble() ?? 0.0;
    final clvAverage = (p['clv_average'] as num?)?.toDouble() ?? 0.0;
    final drawdown   = (p['drawdown'] as num?)?.toDouble() ?? 0.0;
    final activeBets = (p['active_bets'] as List<dynamic>?) ?? [];
    final history    = (p['history'] as List<dynamic>?) ?? [];
    final roiColor   = roi >= 0 ? _kTeal : _kRed;

    return RefreshIndicator(
      color: _kTeal,
      backgroundColor: _kCard,
      onRefresh: _loadPortfolio,
      child: SingleChildScrollView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _buildRoiHero(roi, roiColor),
            const SizedBox(height: 16),
            _buildStatsGrid(winRate, clvAverage, drawdown),
            if (history.length > 1) ...[
              const SizedBox(height: 24),
              _buildSectionHeader('BALANCE HISTORY'),
              const SizedBox(height: 12),
              _buildChart(history, roiColor),
            ],
            if (activeBets.isNotEmpty) ...[
              const SizedBox(height: 24),
              _buildSectionHeader('ACTIVE BETS'),
              const SizedBox(height: 12),
              ...activeBets.map(
                (bet) => _ActiveBetRow(bet: bet as Map<String, dynamic>),
              ),
            ],
            const SizedBox(height: 24),
          ],
        ),
      ),
    );
  }

  Widget _buildRoiHero(double roi, Color roiColor) {
    final isPositive = roi >= 0;
    return Container(
      width: double.infinity,
      clipBehavior: Clip.antiAlias,
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(14),
        gradient: const LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [Color(0xFF111111), Color(0xFF141414)],
        ),
        border: Border.all(
          color: Colors.white.withValues(alpha: 0.06),
          width: 1,
        ),
      ),
      child: Stack(
        children: [
          // Glow behind number
          Positioned(
            top: -20,
            left: -20,
            width: 180,
            height: 180,
            child: Container(
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                gradient: RadialGradient(
                  colors: [
                    roiColor.withValues(alpha: 0.08),
                    Colors.transparent,
                  ],
                ),
              ),
            ),
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(22, 24, 22, 24),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'TOTAL ROI',
                        style: TextStyle(
                          color: Color(0xFF6B7280),
                          fontSize: 10,
                          fontWeight: FontWeight.w600,
                          letterSpacing: 1.2,
                        ),
                      ),
                      const SizedBox(height: 6),
                      Text(
                        '${roi >= 0 ? '+' : ''}${roi.toStringAsFixed(2)}%',
                        style: TextStyle(
                          fontSize: 48,
                          fontWeight: FontWeight.w700,
                          color: roiColor,
                          letterSpacing: -2.0,
                          height: 1,
                        ),
                      ),
                    ],
                  ),
                ),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                  decoration: BoxDecoration(
                    color: roiColor.withValues(alpha: 0.1),
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(
                      color: roiColor.withValues(alpha: 0.2),
                      width: 1,
                    ),
                  ),
                  child: Row(
                    children: [
                      Icon(
                        isPositive
                            ? Icons.arrow_upward_rounded
                            : Icons.arrow_downward_rounded,
                        color: roiColor,
                        size: 12,
                      ),
                      const SizedBox(width: 4),
                      Text(
                        isPositive ? 'Profitable' : 'Tracking',
                        style: TextStyle(
                          color: roiColor,
                          fontSize: 11,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildStatsGrid(double winRate, double clvAverage, double drawdown) {
    return GridView.count(
      crossAxisCount: 2,
      crossAxisSpacing: 10,
      mainAxisSpacing: 10,
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      childAspectRatio: 2.0,
      children: [
        StatChip(
          label: 'Win Rate',
          value: '${(winRate * 100).toStringAsFixed(1)}%',
          color: _kBlue,
        ),
        StatChip(
          label: 'CLV Average',
          value: '${clvAverage >= 0 ? '+' : ''}${clvAverage.toStringAsFixed(2)}%',
          color: clvAverage >= 0 ? _kTeal : _kRed,
        ),
        StatChip(
          label: 'Max Drawdown',
          value: '-${drawdown.toStringAsFixed(1)}%',
          color: _kAmber,
        ),
        const StatChip(
          label: 'Status',
          value: 'Active',
          color: _kTeal,
        ),
      ],
    );
  }

  Widget _buildSectionHeader(String label) {
    return Row(
      children: [
        Container(
          width: 2,
          height: 14,
          decoration: BoxDecoration(
            color: _kTeal,
            borderRadius: BorderRadius.circular(1),
          ),
        ),
        const SizedBox(width: 8),
        Text(
          label,
          style: const TextStyle(
            fontSize: 10,
            fontWeight: FontWeight.w700,
            color: Color(0xFF6B7280),
            letterSpacing: 1.4,
          ),
        ),
      ],
    );
  }

  Widget _buildChart(List<dynamic> history, Color lineColor) {
    return Container(
      height: 180,
      clipBehavior: Clip.antiAlias,
      decoration: BoxDecoration(
        color: _kCard,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: Colors.white.withValues(alpha: 0.05),
          width: 1,
        ),
      ),
      padding: const EdgeInsets.fromLTRB(12, 16, 12, 12),
      child: LineChart(
        LineChartData(
          gridData: FlGridData(
            show: true,
            drawVerticalLine: false,
            horizontalInterval: 1,
            getDrawingHorizontalLine: (_) => FlLine(
              color: Colors.white.withValues(alpha: 0.04),
              strokeWidth: 1,
            ),
          ),
          titlesData: const FlTitlesData(show: false),
          borderData: FlBorderData(show: false),
          lineBarsData: [
            LineChartBarData(
              spots: history.asMap().entries.map<FlSpot>((e) {
                final val = (e.value as num?)?.toDouble() ?? 0.0;
                return FlSpot(e.key.toDouble(), val);
              }).toList(),
              isCurved: true,
              curveSmoothness: 0.35,
              color: lineColor,
              barWidth: 2,
              dotData: const FlDotData(show: false),
              belowBarData: BarAreaData(
                show: true,
                gradient: LinearGradient(
                  begin: Alignment.topCenter,
                  end: Alignment.bottomCenter,
                  colors: [
                    lineColor.withValues(alpha: 0.18),
                    lineColor.withValues(alpha: 0.0),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// ── Active bet row ────────────────────────────────────────────────────────────

class _ActiveBetRow extends StatelessWidget {
  final Map<String, dynamic> bet;
  const _ActiveBetRow({required this.bet});

  @override
  Widget build(BuildContext context) {
    final event  = bet['event'] as String? ?? 'Unknown event';
    final market = bet['market'] as String? ?? '';
    final stake  = (bet['stake'] as num?)?.toDouble() ?? 0.0;
    final odds   = bet['odds']?.toString() ?? '';

    return Container(
      margin: const EdgeInsets.only(bottom: 7),
      clipBehavior: Clip.antiAlias,
      decoration: BoxDecoration(
        color: _kCard,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: Colors.white.withValues(alpha: 0.05),
          width: 1,
        ),
      ),
      child: Stack(
        children: [
          Positioned(
            top: 0, bottom: 0, left: 0, width: 3,
            child: Container(
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  begin: Alignment.topCenter,
                  end: Alignment.bottomCenter,
                  colors: [_kAmber, _kAmber.withValues(alpha: 0.4)],
                ),
              ),
            ),
          ),
          Padding(
            padding: const EdgeInsets.only(left: 18, right: 14, top: 11, bottom: 11),
            child: Row(
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        event,
                        style: const TextStyle(
                          fontWeight: FontWeight.w600,
                          fontSize: 13,
                          letterSpacing: -0.2,
                          color: Colors.white,
                        ),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                      if (market.isNotEmpty) ...[
                        const SizedBox(height: 3),
                        Text(
                          market,
                          style: const TextStyle(
                            color: Color(0xFF6B7280),
                            fontSize: 11,
                          ),
                        ),
                      ],
                    ],
                  ),
                ),
                Column(
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    Text(
                      '\$${stake.toStringAsFixed(0)}',
                      style: const TextStyle(
                        color: _kAmber,
                        fontWeight: FontWeight.w700,
                        fontSize: 16,
                        letterSpacing: -0.4,
                      ),
                    ),
                    if (odds.isNotEmpty)
                      Text(
                        odds,
                        style: const TextStyle(
                          color: Color(0xFF4B5563),
                          fontSize: 10,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

// ── Empty state ───────────────────────────────────────────────────────────────

class _EmptyState extends StatelessWidget {
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
              child: const Icon(Icons.account_balance_wallet_outlined,
                  color: Color(0xFF374151), size: 22),
            ),
            const SizedBox(height: 16),
            const Text(
              'No portfolio data',
              style: TextStyle(
                color: Colors.white70,
                fontSize: 15,
                fontWeight: FontWeight.w600,
                letterSpacing: -0.3,
              ),
            ),
            const SizedBox(height: 6),
            const Text(
              'Sign in to view your performance metrics\nand active bets',
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
