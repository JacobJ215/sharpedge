import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/app_state.dart';
import '../services/api_service.dart';
import '../models/value_play.dart';
import '../widgets/alpha_badge_widget.dart';
import '../widgets/log_bet_sheet.dart';

// ApiService instance shared within this screen
final _apiService = ApiService();

const _kTeal = Color(0xFF00D4AA);
const _kBg = Color(0xFF0A0E1A);
const _kCard = Color(0xFF0F1421);

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
      case _AlphaFilter.all:
        return plays;
      case _AlphaFilter.premium:
        return plays.where((p) => p.alphaBadge == 'PREMIUM').toList();
      case _AlphaFilter.high:
        return plays.where((p) => p.alphaBadge == 'HIGH').toList();
      case _AlphaFilter.medium:
        return plays.where((p) => p.alphaBadge == 'MEDIUM').toList();
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
                letterSpacing: -0.4,
              ),
            ),
            Text(
              subtitle,
              style: TextStyle(
                fontSize: 11,
                fontWeight: FontWeight.w400,
                color: Colors.grey[500],
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
                    decoration: const BoxDecoration(
                      color: Color(0xFF00D4AA),
                      shape: BoxShape.circle,
                    ),
                  ),
                  const SizedBox(width: 5),
                  Text(
                    'LIVE',
                    style: TextStyle(
                      fontSize: 9,
                      fontWeight: FontWeight.w700,
                      color: Colors.grey[500],
                      letterSpacing: 1.0,
                    ),
                  ),
                ],
              ),
            ),
          IconButton(
            icon: const Icon(Icons.refresh_rounded, size: 18),
            onPressed: _loadPlays,
            color: Colors.grey[600],
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
      padding: const EdgeInsets.fromLTRB(16, 6, 16, 12),
      child: SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        child: Row(
          children: [
            _FilterChip(
              label: 'All',
              selected: _filter == _AlphaFilter.all,
              onTap: () => setState(() => _filter = _AlphaFilter.all),
              color: _kTeal,
            ),
            const SizedBox(width: 8),
            _FilterChip(
              label: 'Premium',
              selected: _filter == _AlphaFilter.premium,
              onTap: () => setState(() => _filter = _AlphaFilter.premium),
              color: const Color(0xFF10B981),
              dot: const Color(0xFF10B981),
            ),
            const SizedBox(width: 8),
            _FilterChip(
              label: 'High',
              selected: _filter == _AlphaFilter.high,
              onTap: () => setState(() => _filter = _AlphaFilter.high),
              color: const Color(0xFF3B82F6),
              dot: const Color(0xFF3B82F6),
            ),
            const SizedBox(width: 8),
            _FilterChip(
              label: 'Medium',
              selected: _filter == _AlphaFilter.medium,
              onTap: () => setState(() => _filter = _AlphaFilter.medium),
              color: const Color(0xFFF59E0B),
              dot: const Color(0xFFF59E0B),
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
        padding: const EdgeInsets.only(bottom: 16),
        itemBuilder: (context, i) {
          final play = plays[i];
          return Dismissible(
            key: Key(play.id),
            direction: DismissDirection.startToEnd,
            background: Container(
              alignment: Alignment.centerLeft,
              padding: const EdgeInsets.only(left: 24),
              color: const Color(0xFF10B981).withValues(alpha: 0.15),
              child: const Row(
                children: [
                  Icon(Icons.add_circle_outline, color: Color(0xFF10B981)),
                  SizedBox(width: 8),
                  Text('Log Bet',
                    style: TextStyle(
                      color: Color(0xFF10B981),
                      fontWeight: FontWeight.w600,
                    )),
                ],
              ),
            ),
            confirmDismiss: (direction) async {
              await showModalBottomSheet<Map<String, dynamic>>(
                context: context,
                isScrollControlled: true,
                backgroundColor: _kCard,
                shape: const RoundedRectangleBorder(
                  borderRadius: BorderRadius.vertical(top: Radius.circular(16)),
                ),
                builder: (_) => LogBetSheet(play: play),
              );
              return false; // Don't remove card from list
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
            Icon(Icons.analytics_outlined, color: Colors.grey[700], size: 40),
            const SizedBox(height: 14),
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
            Text(
              'Adjust filters or pull to refresh\nfor the latest market data',
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

class _PlayCard extends StatelessWidget {
  final ValuePlayV1 play;

  const _PlayCard({required this.play});

  Color get _evColor {
    final ev = play.expectedValue * 100;
    if (ev >= 5) return _kTeal;
    if (ev >= 2) return const Color(0xFF3B82F6);
    if (ev >= 0) return Colors.grey;
    return const Color(0xFFEF4444);
  }

  @override
  Widget build(BuildContext context) {
    final ev = play.expectedValue * 100;
    final evColor = _evColor;

    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 5),
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
            child: Container(color: evColor),
          ),
          Padding(
            padding: const EdgeInsets.only(left: 18, right: 14, top: 10, bottom: 10),
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
                        '${play.market}  ·  ${play.team}  ·  ${play.book}',
                        style: TextStyle(color: Colors.grey[500], fontSize: 11),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                      const SizedBox(height: 6),
                      Row(
                        children: [
                          AlphaBadgeWidget(badge: play.alphaBadge),
                          const SizedBox(width: 6),
                          Text(
                            play.regimeState,
                            style: TextStyle(
                              color: Colors.grey[600],
                              fontSize: 10,
                              fontWeight: FontWeight.w500,
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
                Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    Text(
                      '${ev >= 0 ? '+' : ''}${ev.toStringAsFixed(1)}%',
                      style: TextStyle(
                        color: evColor,
                        fontWeight: FontWeight.w700,
                        fontSize: 15,
                        letterSpacing: -0.3,
                      ),
                    ),
                    Text(
                      'EV',
                      style: TextStyle(
                        color: Colors.grey[600],
                        fontSize: 10,
                        fontWeight: FontWeight.w500,
                        letterSpacing: 0.5,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      'α ${play.alphaScore.toStringAsFixed(2)}',
                      style: TextStyle(
                        color: Colors.grey[500],
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

class _FilterChip extends StatelessWidget {
  final String label;
  final bool selected;
  final VoidCallback onTap;
  final Color color;
  final Color? dot;

  const _FilterChip({
    required this.label,
    required this.selected,
    required this.onTap,
    required this.color,
    this.dot,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 160),
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 7),
        decoration: BoxDecoration(
          color: selected
              ? color.withValues(alpha: 0.15)
              : _kCard,
          borderRadius: BorderRadius.circular(20),
          border: Border.all(
            color: selected
                ? color.withValues(alpha: 0.5)
                : Colors.white.withValues(alpha: 0.06),
            width: 1,
          ),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            if (dot != null) ...[
              Container(
                width: 5,
                height: 5,
                decoration: BoxDecoration(
                  color: selected ? dot : Colors.grey[700],
                  shape: BoxShape.circle,
                ),
              ),
              const SizedBox(width: 5),
            ],
            Text(
              label,
              style: TextStyle(
                fontSize: 12,
                fontWeight: FontWeight.w600,
                color: selected ? color : Colors.grey[500],
                letterSpacing: 0.1,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
