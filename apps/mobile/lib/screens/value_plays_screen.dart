import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/app_state.dart';
import '../services/api_service.dart';
import '../models/value_play.dart';
import '../widgets/alpha_badge_widget.dart';
import '../widgets/log_bet_sheet.dart';

final _apiService = ApiService();

const _kTeal  = Color(0xFF00D4AA);
const _kBg    = Color(0xFF0A0A0A);
const _kCard  = Color(0xFF141414);

enum _AlphaFilter { all, premium, high, medium }

class ValuePlaysScreen extends StatefulWidget {
  const ValuePlaysScreen({super.key});

  @override
  State<ValuePlaysScreen> createState() => _ValuePlaysScreenState();
}

class _ValuePlaysScreenState extends State<ValuePlaysScreen> {
  _AlphaFilter _filter = _AlphaFilter.all;
  List<ValuePlayV1> _plays = [];
  bool _loading = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadPlays();
  }

  Future<void> _loadPlays() async {
    final appState = context.read<AppState>();
    setState(() { _loading = true; _error = null; });
    try {
      final plays = await _apiService.getValuePlaysV1(token: appState.authToken);
      setState(() { _plays = plays; });
    } catch (e) {
      setState(() { _error = e.toString(); });
    } finally {
      setState(() { _loading = false; });
    }
  }

  List<ValuePlayV1> _applyFilter(List<ValuePlayV1> plays) {
    switch (_filter) {
      case _AlphaFilter.all:     return plays;
      case _AlphaFilter.premium: return plays.where((p) => p.alphaBadge == 'PREMIUM').toList();
      case _AlphaFilter.high:    return plays.where((p) => p.alphaBadge == 'HIGH').toList();
      case _AlphaFilter.medium:  return plays.where((p) => p.alphaBadge == 'MEDIUM').toList();
    }
  }

  @override
  Widget build(BuildContext context) {
    final premiumCount = _plays.where((p) => p.alphaBadge == 'PREMIUM').length;
    final subtitle = _plays.isEmpty
        ? 'No active signals'
        : '${_plays.length} active  ·  $premiumCount premium';

    return Scaffold(
      backgroundColor: _kBg,
      appBar: AppBar(
        backgroundColor: _kBg,
        toolbarHeight: 56,
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Value Plays',
              style: TextStyle(
                fontSize: 17,
                fontWeight: FontWeight.w700,
                letterSpacing: -0.5,
              ),
            ),
            Text(
              subtitle,
              style: const TextStyle(
                fontSize: 11,
                fontWeight: FontWeight.w400,
                color: Color(0xFF6B7280),
                letterSpacing: 0.1,
              ),
            ),
          ],
        ),
        actions: [
          if (!_loading)
            Padding(
              padding: const EdgeInsets.only(right: 4),
              child: Row(
                children: [
                  Container(
                    width: 6,
                    height: 6,
                    decoration: BoxDecoration(
                      color: _kTeal,
                      shape: BoxShape.circle,
                      boxShadow: [
                        BoxShadow(
                          color: _kTeal.withValues(alpha: 0.6),
                          blurRadius: 5,
                          spreadRadius: 1,
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(width: 5),
                  const Text(
                    'LIVE',
                    style: TextStyle(
                      fontSize: 9,
                      fontWeight: FontWeight.w700,
                      color: Color(0xFF6B7280),
                      letterSpacing: 1.0,
                    ),
                  ),
                ],
              ),
            ),
          IconButton(
            icon: const Icon(Icons.refresh_rounded, size: 18),
            onPressed: _loadPlays,
            color: const Color(0xFF4B5563),
          ),
        ],
      ),
      body: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _buildFilterRow(),
          Expanded(child: _body()),
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
            _FilterPill(
              label: 'All',
              selected: _filter == _AlphaFilter.all,
              onTap: () => setState(() => _filter = _AlphaFilter.all),
              color: _kTeal,
            ),
            const SizedBox(width: 8),
            _FilterPill(
              label: 'Premium',
              selected: _filter == _AlphaFilter.premium,
              onTap: () => setState(() => _filter = _AlphaFilter.premium),
              color: const Color(0xFF10B981),
              dotColor: const Color(0xFF10B981),
            ),
            const SizedBox(width: 8),
            _FilterPill(
              label: 'High',
              selected: _filter == _AlphaFilter.high,
              onTap: () => setState(() => _filter = _AlphaFilter.high),
              color: const Color(0xFF3B82F6),
              dotColor: const Color(0xFF3B82F6),
            ),
            const SizedBox(width: 8),
            _FilterPill(
              label: 'Medium',
              selected: _filter == _AlphaFilter.medium,
              onTap: () => setState(() => _filter = _AlphaFilter.medium),
              color: const Color(0xFFF59E0B),
              dotColor: const Color(0xFFF59E0B),
            ),
          ],
        ),
      ),
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
          style: const TextStyle(color: Color(0xFFEF4444), fontSize: 13),
        ),
      );
    }
    final plays = _applyFilter(_plays);
    if (plays.isEmpty) {
      return _buildEmptyState();
    }
    return RefreshIndicator(
      color: _kTeal,
      backgroundColor: _kCard,
      onRefresh: _loadPlays,
      child: ListView.builder(
        itemCount: plays.length,
        padding: const EdgeInsets.only(bottom: 24),
        itemBuilder: (context, i) {
          final play = plays[i];
          return Dismissible(
            key: Key(play.id),
            direction: DismissDirection.startToEnd,
            background: Container(
              alignment: Alignment.centerLeft,
              padding: const EdgeInsets.only(left: 24),
              decoration: BoxDecoration(
                color: const Color(0xFF10B981).withValues(alpha: 0.1),
              ),
              child: const Row(
                children: [
                  Icon(Icons.add_circle_outline, color: Color(0xFF10B981), size: 18),
                  SizedBox(width: 8),
                  Text(
                    'Log Bet',
                    style: TextStyle(
                      color: Color(0xFF10B981),
                      fontWeight: FontWeight.w600,
                      fontSize: 13,
                    ),
                  ),
                ],
              ),
            ),
            confirmDismiss: (direction) async {
              await showModalBottomSheet<Map<String, dynamic>>(
                context: context,
                isScrollControlled: true,
                backgroundColor: _kCard,
                shape: const RoundedRectangleBorder(
                  borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
                ),
                builder: (_) => LogBetSheet(play: play),
              );
              return false;
            },
            child: _PlayCard(play: play),
          );
        },
      ),
    );
  }

  Widget _buildEmptyState() {
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
              child: const Icon(Icons.analytics_outlined,
                  color: Color(0xFF374151), size: 24),
            ),
            const SizedBox(height: 16),
            const Text(
              'No signals detected',
              style: TextStyle(
                color: Colors.white70,
                fontSize: 15,
                fontWeight: FontWeight.w600,
                letterSpacing: -0.3,
              ),
            ),
            const SizedBox(height: 6),
            const Text(
              'Adjust filters or pull to refresh\nfor the latest market data',
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

// ── Play card ─────────────────────────────────────────────────────────────────

class _PlayCard extends StatelessWidget {
  final ValuePlayV1 play;
  const _PlayCard({required this.play});

  Color get _evColor {
    final ev = play.expectedValue * 100;
    if (ev >= 5)  return _kTeal;
    if (ev >= 2)  return const Color(0xFF3B82F6);
    if (ev >= 0)  return const Color(0xFF6B7280);
    return const Color(0xFFEF4444);
  }

  @override
  Widget build(BuildContext context) {
    final ev = play.expectedValue * 100;
    final evColor = _evColor;

    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 14, 16, 14),
          child: Row(
            children: [
              Container(
                width: 2,
                height: 36,
                decoration: BoxDecoration(
                  color: evColor.withValues(alpha: 0.65),
                  borderRadius: BorderRadius.circular(1),
                ),
              ),
              const SizedBox(width: 14),
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
                          height: 1.3,
                        ),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                      const SizedBox(height: 3),
                      Text(
                        '${play.market}  ·  ${play.team}  ·  ${play.book}',
                        style: const TextStyle(
                          color: Color(0xFF6B7280),
                          fontSize: 11,
                        ),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                      const SizedBox(height: 8),
                      Row(
                        children: [
                          AlphaBadgeWidget(badge: play.alphaBadge),
                          const SizedBox(width: 6),
                          Text(
                            play.regimeState,
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
                const SizedBox(width: 12),
                Column(
                  mainAxisAlignment: MainAxisAlignment.center,
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
                      'EV',
                      style: TextStyle(
                        color: Color(0xFF4B5563),
                        fontSize: 10,
                        fontWeight: FontWeight.w600,
                        letterSpacing: 0.5,
                      ),
                    ),
                    const SizedBox(height: 6),
                    Text(
                      'α ${play.alphaScore.toStringAsFixed(2)}',
                      style: const TextStyle(
                        color: Color(0xFF374151),
                        fontSize: 10,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        Container(
          height: 0.5,
          color: Colors.white.withValues(alpha: 0.07),
          margin: const EdgeInsets.only(left: 32),
        ),
      ],
    );
  }
}

// ── Filter pill ───────────────────────────────────────────────────────────────

class _FilterPill extends StatelessWidget {
  final String label;
  final bool selected;
  final VoidCallback onTap;
  final Color color;
  final Color? dotColor;

  const _FilterPill({
    required this.label,
    required this.selected,
    required this.onTap,
    required this.color,
    this.dotColor,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 150),
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
        decoration: BoxDecoration(
          color: selected ? color.withValues(alpha: 0.1) : Colors.transparent,
          borderRadius: BorderRadius.circular(20),
          border: Border.all(
            color: selected
                ? color.withValues(alpha: 0.35)
                : Colors.white.withValues(alpha: 0.07),
            width: 0.5,
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
