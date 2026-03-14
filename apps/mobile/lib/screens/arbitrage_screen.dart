import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/app_state.dart';
import '../models/arbitrage_opportunity.dart';
import '../widgets/play_card.dart';

const _kAmber = Color(0xFFF59E0B);
const _kBg    = Color(0xFF0A0A0A);
const _kCard  = Color(0xFF141414);

class ArbitrageScreen extends StatelessWidget {
  const ArbitrageScreen({super.key});

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
              'Arbitrage',
              style: TextStyle(
                fontSize: 17,
                fontWeight: FontWeight.w700,
                letterSpacing: -0.5,
              ),
            ),
            Text(
              state.arbitrage.isEmpty
                  ? 'No opportunities'
                  : '${state.arbitrage.length} active  ·  risk-free profit',
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
      body: _body(context, state),
    );
  }

  Widget _body(BuildContext context, AppState state) {
    if (state.loading) {
      return const Center(
        child: CircularProgressIndicator(color: _kAmber, strokeWidth: 2),
      );
    }
    if (state.error != null) {
      return Center(
        child: Text(
          'Error: ${state.error}',
          style: const TextStyle(color: Color(0xFFEF4444), fontSize: 13),
        ),
      );
    }
    final opps = state.arbitrage;
    if (opps.isEmpty) {
      return const _EmptyState();
    }
    return ListView.builder(
      itemCount: opps.length,
      padding: const EdgeInsets.only(bottom: 24),
      itemBuilder: (context, i) {
        final opp = opps[i];
        return PlayCard(
          title: opp.event,
          subtitle: opp.market,
          accentColor: _kAmber,
          trailing: _ArbTrailing(profit: opp.profitPercent),
          onTap: () => _showLegsSheet(context, opp),
        );
      },
    );
  }

  void _showLegsSheet(BuildContext context, ArbitrageOpportunity opp) {
    showModalBottomSheet(
      context: context,
      backgroundColor: _kCard,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
        side: BorderSide(color: Color(0x0DFFFFFF), width: 1),
      ),
      builder: (_) => Padding(
        padding: const EdgeInsets.fromLTRB(20, 20, 20, 36),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Handle
            Center(
              child: Container(
                width: 36,
                height: 4,
                margin: const EdgeInsets.only(bottom: 20),
                decoration: BoxDecoration(
                  color: Colors.white.withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
            ),
            Row(
              children: [
                Container(
                  width: 3,
                  height: 16,
                  decoration: BoxDecoration(
                    color: _kAmber,
                    borderRadius: BorderRadius.circular(2),
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Text(
                    opp.event,
                    style: const TextStyle(
                      fontSize: 15,
                      fontWeight: FontWeight.w700,
                      letterSpacing: -0.3,
                    ),
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 6),
            Padding(
              padding: const EdgeInsets.only(left: 13),
              child: Text(
                '+${opp.profitPercent.toStringAsFixed(2)}% guaranteed profit',
                style: const TextStyle(
                  color: _kAmber,
                  fontSize: 12,
                  fontWeight: FontWeight.w600,
                  letterSpacing: 0.1,
                ),
              ),
            ),
            const SizedBox(height: 20),
            Divider(
              color: Colors.white.withValues(alpha: 0.06),
              height: 1,
            ),
            const SizedBox(height: 16),
            const Text(
              'LEGS',
              style: TextStyle(
                fontSize: 10,
                fontWeight: FontWeight.w700,
                color: Color(0xFF6B7280),
                letterSpacing: 1.4,
              ),
            ),
            const SizedBox(height: 10),
            ...opp.legs.map(
              (leg) => Container(
                margin: const EdgeInsets.only(bottom: 8),
                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                decoration: BoxDecoration(
                  color: Colors.white.withValues(alpha: 0.03),
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(
                    color: Colors.white.withValues(alpha: 0.06),
                    width: 1,
                  ),
                ),
                child: Row(
                  children: [
                    Container(
                      width: 28,
                      height: 28,
                      decoration: BoxDecoration(
                        color: Colors.white.withValues(alpha: 0.04),
                        borderRadius: BorderRadius.circular(7),
                      ),
                      child: const Icon(Icons.sports_rounded,
                          size: 14, color: Color(0xFF4B5563)),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            leg.book,
                            style: const TextStyle(
                              fontSize: 13,
                              fontWeight: FontWeight.w600,
                              letterSpacing: -0.1,
                            ),
                          ),
                          Text(
                            leg.side,
                            style: const TextStyle(
                              fontSize: 11,
                              color: Color(0xFF6B7280),
                              fontWeight: FontWeight.w400,
                            ),
                          ),
                        ],
                      ),
                    ),
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.end,
                      children: [
                        Text(
                          '${leg.odds > 0 ? '+' : ''}${leg.odds.toStringAsFixed(0)}',
                          style: const TextStyle(
                            fontSize: 14,
                            fontWeight: FontWeight.w700,
                            color: Color(0xFF3B82F6),
                            letterSpacing: -0.2,
                          ),
                        ),
                        Text(
                          '\$${leg.stake.toStringAsFixed(2)}',
                          style: const TextStyle(
                            fontSize: 12,
                            fontWeight: FontWeight.w600,
                            color: _kAmber,
                          ),
                        ),
                      ],
                    ),
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

// ── Trailing ──────────────────────────────────────────────────────────────────

class _ArbTrailing extends StatelessWidget {
  final double profit;
  const _ArbTrailing({required this.profit});

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisAlignment: MainAxisAlignment.center,
      crossAxisAlignment: CrossAxisAlignment.end,
      children: [
        Text(
          '+${profit.toStringAsFixed(2)}%',
          style: const TextStyle(
            color: _kAmber,
            fontWeight: FontWeight.w700,
            fontSize: 16,
            letterSpacing: -0.4,
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
              child: const Icon(Icons.swap_horiz_outlined,
                  color: Color(0xFF374151), size: 22),
            ),
            const SizedBox(height: 16),
            const Text(
              'No arbitrage found',
              style: TextStyle(
                color: Colors.white70,
                fontSize: 15,
                fontWeight: FontWeight.w600,
                letterSpacing: -0.3,
              ),
            ),
            const SizedBox(height: 6),
            const Text(
              'Market inefficiencies will appear here\nwhen pricing diverges across books',
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
