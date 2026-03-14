import 'package:flutter/material.dart';
import 'package:fl_chart/fl_chart.dart';
import 'package:provider/provider.dart';
import '../providers/app_state.dart';
import '../services/api_service.dart';
import '../widgets/stat_chip.dart';

const _kTeal = Color(0xFF00D4AA);
const _kRed = Color(0xFFEF4444);
const _kBlue = Color(0xFF3B82F6);
const _kAmber = Color(0xFFF59E0B);
const _kBg = Color(0xFF0A0E1A);
const _kCard = Color(0xFF0F1421);

// ApiService instance shared within this screen
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
      final data =
          await _apiService.getPortfolio(appState.userId!, appState.authToken!);
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
    final roiLabel = portfolio == null
        ? 'Performance tracker'
        : 'ROI ${roi >= 0 ? '+' : ''}${roi.toStringAsFixed(1)}%';

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
                  letterSpacing: -0.4),
            ),
            Text(
              roiLabel,
              style: TextStyle(
                  fontSize: 11, color: Colors.grey[500], letterSpacing: 0.1),
            ),
          ],
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh_rounded, size: 18),
            onPressed: _loadPortfolio,
            color: Colors.grey[600],
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

    final roi = (p['roi'] as num?)?.toDouble() ?? 0.0;
    final winRate = (p['win_rate'] as num?)?.toDouble() ?? 0.0;
    final clvAverage = (p['clv_average'] as num?)?.toDouble() ?? 0.0;
    final drawdown = (p['drawdown'] as num?)?.toDouble() ?? 0.0;
    final activeBets = (p['active_bets'] as List<dynamic>?) ?? [];
    final history = (p['history'] as List<dynamic>?) ?? [];

    final roiColor = roi >= 0 ? _kTeal : _kRed;

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
            Container(
              height: 1,
              margin: const EdgeInsets.symmetric(vertical: 14),
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  colors: [
                    Colors.transparent,
                    Colors.white.withValues(alpha: 0.08),
                    Colors.transparent,
                  ],
                ),
              ),
            ),
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
              ...activeBets.map((bet) =>
                  _ActiveBetRow(bet: bet as Map<String, dynamic>)),
            ],
            const SizedBox(height: 24),
          ],
        ),
      ),
    );
  }

  Widget _buildRoiHero(double roi, Color roiColor) {
    return Container(
      width: double.infinity,
      clipBehavior: Clip.antiAlias,
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(10),
        gradient: const LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [Color(0xFF111827), Color(0xFF0F1421)],
        ),
        border: Border.all(
          color: Colors.white.withValues(alpha: 0.08),
          width: 1,
        ),
      ),
      child: Padding(
        padding: const EdgeInsets.fromLTRB(20, 22, 20, 22),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'TOTAL ROI',
              style: TextStyle(
                color: Colors.grey[500],
                fontSize: 10,
                fontWeight: FontWeight.w600,
                letterSpacing: 1.2,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              '${roi >= 0 ? '+' : ''}${roi.toStringAsFixed(2)}%',
              style: TextStyle(
                fontSize: 36,
                fontWeight: FontWeight.w700,
                color: roiColor,
                letterSpacing: -1.5,
                height: 1,
              ),
            ),
          ],
        ),
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
        StatChip(
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
          style: TextStyle(
            fontSize: 10,
            fontWeight: FontWeight.w700,
            color: Colors.grey[500],
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
        borderRadius: BorderRadius.circular(10),
        border: Border.all(
          color: Colors.white.withValues(alpha: 0.06),
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
              curveSmoothness: 0.3,
              color: lineColor,
              barWidth: 2,
              dotData: const FlDotData(show: false),
              belowBarData: BarAreaData(
                show: true,
                gradient: LinearGradient(
                  begin: Alignment.topCenter,
                  end: Alignment.bottomCenter,
                  colors: [
                    lineColor.withValues(alpha: 0.15),
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

class _ActiveBetRow extends StatelessWidget {
  final Map<String, dynamic> bet;
  const _ActiveBetRow({required this.bet});

  @override
  Widget build(BuildContext context) {
    final event = bet['event'] as String? ?? 'Unknown event';
    final market = bet['market'] as String? ?? '';
    final stake = (bet['stake'] as num?)?.toDouble() ?? 0.0;
    final odds = bet['odds']?.toString() ?? '';

    return Container(
      margin: const EdgeInsets.only(bottom: 7),
      clipBehavior: Clip.antiAlias,
      decoration: BoxDecoration(
        color: _kCard,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(
          color: Colors.white.withValues(alpha: 0.06),
          width: 1,
        ),
      ),
      child: Stack(
        children: [
          Positioned(
            top: 0, bottom: 0, left: 0, width: 3,
            child: Container(color: _kAmber),
          ),
          Padding(
            padding: const EdgeInsets.only(
                left: 18, right: 14, top: 10, bottom: 10),
            child: Row(
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(event,
                          style: const TextStyle(
                            fontWeight: FontWeight.w600,
                            fontSize: 13,
                            letterSpacing: -0.2,
                            color: Colors.white,
                          ),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis),
                      if (market.isNotEmpty) ...[
                        const SizedBox(height: 3),
                        Text(market,
                            style: TextStyle(
                                color: Colors.grey[500], fontSize: 11)),
                      ],
                    ],
                  ),
                ),
                Column(
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    Text('\$${stake.toStringAsFixed(0)}',
                        style: const TextStyle(
                          color: _kAmber,
                          fontWeight: FontWeight.w700,
                          fontSize: 15,
                          letterSpacing: -0.3,
                        )),
                    if (odds.isNotEmpty)
                      Text(odds,
                          style: TextStyle(
                            color: Colors.grey[600],
                            fontSize: 10,
                            fontWeight: FontWeight.w500,
                          )),
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

class _EmptyState extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.account_balance_wallet_outlined,
                color: Colors.grey[700], size: 40),
            const SizedBox(height: 14),
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
            Text(
              'Sign in to view your performance metrics\nand active bets',
              style: TextStyle(
                color: Colors.grey[600],
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
