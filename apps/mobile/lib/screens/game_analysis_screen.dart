import 'package:flutter/material.dart';
import '../models/game_analysis.dart';
import '../models/value_play.dart';
import '../services/api_service.dart';
import '../widgets/alpha_badge_widget.dart';

const _kTeal = Color(0xFF10B981);
const _kBg = Color(0xFF0A0A0A);
const _kCard = Color(0xFF141414);
const _kBorder = Color(0xFF1F1F1F);

final _api = ApiService();

class GameAnalysisScreen extends StatefulWidget {
  final ValuePlayV1 play;

  const GameAnalysisScreen({super.key, required this.play});

  @override
  State<GameAnalysisScreen> createState() => _GameAnalysisScreenState();
}

class _GameAnalysisScreenState extends State<GameAnalysisScreen> {
  GameAnalysisSnapshot? _data;
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final snap = await _api.getGameAnalysis(widget.play.id);
      if (mounted) {
        setState(() {
          _data = snap;
          _loading = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _error = e.toString();
          _loading = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: _kBg,
      appBar: AppBar(
        backgroundColor: _kBg,
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('Game analysis'),
            Text(
              widget.play.event,
              style: const TextStyle(
                fontSize: 11,
                fontWeight: FontWeight.w400,
                color: Color(0xFF6B7280),
              ),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
          ],
        ),
      ),
      body: RefreshIndicator(
        color: _kTeal,
        backgroundColor: _kCard,
        onRefresh: _load,
        child: _body(),
      ),
    );
  }

  Widget _body() {
    if (_loading) {
      return ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        children: const [
          SizedBox(height: 120),
          Center(child: CircularProgressIndicator(color: _kTeal, strokeWidth: 2)),
        ],
      );
    }
    if (_error != null) {
      return ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.all(24),
        children: [
          Text(_error!, style: const TextStyle(color: Color(0xFFEF4444), fontSize: 13)),
          const SizedBox(height: 16),
          TextButton(onPressed: _load, child: const Text('Retry')),
        ],
      );
    }
    final d = _data!;
    return ListView(
      physics: const AlwaysScrollableScrollPhysics(),
      padding: const EdgeInsets.all(16),
      children: [
        _panel(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  AlphaBadgeWidget(badge: d.alphaBadge),
                  const SizedBox(width: 8),
                  Text(
                    d.regimeState,
                    style: const TextStyle(color: Color(0xFF6B7280), fontSize: 12),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              Text(
                '${(d.winProbability * 100).toStringAsFixed(1)}% model win prob',
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 20,
                  fontWeight: FontWeight.w700,
                ),
              ),
              Text(
                'Confidence ${d.confidence}',
                style: const TextStyle(color: Color(0xFF9CA3AF), fontSize: 12),
              ),
              const SizedBox(height: 10),
              Text(
                'EV ${d.evPercentage >= 0 ? '+' : ''}${d.evPercentage.toStringAsFixed(2)}%',
                style: TextStyle(
                  color: d.evPercentage >= 0 ? _kTeal : const Color(0xFFEF4444),
                  fontSize: 14,
                  fontWeight: FontWeight.w600,
                ),
              ),
              const SizedBox(height: 4),
              Text(
                'Fair ${d.fairOdds.toStringAsFixed(0)}  ·  Market ${d.marketOdds.toStringAsFixed(0)}',
                style: const TextStyle(color: Color(0xFF6B7280), fontSize: 12),
              ),
              if (d.keyNumberProximity != null && d.keyNumberProximity!.isNotEmpty) ...[
                const SizedBox(height: 8),
                Text(
                  'Key number: ${d.keyNumberProximity}',
                  style: const TextStyle(color: Color(0xFF9CA3AF), fontSize: 11),
                ),
              ],
              const SizedBox(height: 6),
              Text(
                'α ${d.alphaScore.toStringAsFixed(2)}',
                style: const TextStyle(color: Color(0xFF52525B), fontSize: 11),
              ),
            ],
          ),
        ),
        const SizedBox(height: 12),
        const Text(
          'INJURIES',
          style: TextStyle(
            fontSize: 10,
            fontWeight: FontWeight.w700,
            color: Color(0xFF6B7280),
            letterSpacing: 1.2,
          ),
        ),
        const SizedBox(height: 8),
        if (d.injuries.isEmpty)
          _panel(
            child: const Text(
              'No notable injuries matched for this matchup.',
              style: TextStyle(color: Color(0xFF6B7280), fontSize: 13),
            ),
          )
        else
          ...d.injuries.map(_injuryTile),
      ],
    );
  }

  Widget _panel({required Widget child}) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: _kCard,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: _kBorder),
      ),
      child: child,
    );
  }

  Widget _injuryTile(InjuryRow r) {
    final status = r.status ?? '—';
    final keyTag = r.isKeyPlayer ? ' · KEY' : '';
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: _panel(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              r.playerName ?? 'Unknown',
              style: const TextStyle(
                color: Colors.white,
                fontWeight: FontWeight.w600,
                fontSize: 14,
              ),
            ),
            const SizedBox(height: 4),
            Text(
              '${r.team ?? ''} ${r.position != null ? '· ${r.position}' : ''}'
              '$keyTag',
              style: const TextStyle(color: Color(0xFF6B7280), fontSize: 12),
            ),
            const SizedBox(height: 6),
            Text(
              status,
              style: TextStyle(
                color: status.toUpperCase().contains('OUT')
                    ? const Color(0xFFEF4444)
                    : const Color(0xFFF59E0B),
                fontSize: 12,
                fontWeight: FontWeight.w600,
              ),
            ),
            if (r.injuryType != null && r.injuryType!.isNotEmpty)
              Text(
                r.injuryType!,
                style: const TextStyle(color: Color(0xFF52525B), fontSize: 11),
              ),
          ],
        ),
      ),
    );
  }
}
