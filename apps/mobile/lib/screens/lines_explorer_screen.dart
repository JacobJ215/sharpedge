import 'package:flutter/material.dart';
import '../copy/microcopy.dart';
import '../services/api_service.dart';

const _kTeal = Color(0xFF10B981);
const _kBg = Color(0xFF0A0A0A);
const _kCard = Color(0xFF141414);

final _api = ApiService();

class LinesExplorerScreen extends StatefulWidget {
  const LinesExplorerScreen({super.key});

  @override
  State<LinesExplorerScreen> createState() => _LinesExplorerScreenState();
}

class _LinesExplorerScreenState extends State<LinesExplorerScreen> {
  static const _sports = ['NFL', 'NBA', 'MLB', 'NHL', 'NCAAF', 'NCAAB'];

  String _sport = 'NFL';
  List<Map<String, dynamic>> _games = [];
  String? _gameId;
  Map<String, dynamic>? _comparison;
  bool _loading = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadGames();
  }

  Future<void> _loadGames() async {
    setState(() {
      _loading = true;
      _error = null;
      _comparison = null;
    });
    try {
      final raw = await _api.getOddsGames(sport: _sport);
      _games = raw.map((e) => Map<String, dynamic>.from(e as Map)).toList();
      _gameId = _games.isNotEmpty ? '${_games.first['id']}' : null;
      if (_gameId != null) {
        _comparison = await _api.getOddsLineComparison(sport: _sport, gameId: _gameId);
      }
    } catch (e) {
      _error = e.toString();
      _games = [];
      _gameId = null;
      _comparison = null;
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _loadComparison() async {
    final gid = _gameId;
    if (gid == null) return;
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      _comparison = await _api.getOddsLineComparison(sport: _sport, gameId: gid);
    } catch (e) {
      _error = e.toString();
      _comparison = null;
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: _kBg,
      appBar: AppBar(
        backgroundColor: _kBg,
        title: const Text(Microcopy.linesPageTitle),
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Text(
            Microcopy.linesPageSubtitle,
            style: const TextStyle(color: Color(0xFF6B7280), fontSize: 12),
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              DropdownButton<String>(
                value: _sport,
                dropdownColor: _kCard,
                style: const TextStyle(color: Colors.white, fontSize: 14),
                items: _sports
                    .map((s) => DropdownMenuItem(value: s, child: Text(s)))
                    .toList(),
                onChanged: (v) {
                  if (v == null) return;
                  setState(() => _sport = v);
                  _loadGames();
                },
              ),
              const SizedBox(width: 12),
              TextButton(
                onPressed: _loading ? null : _loadGames,
                child: const Text('Refresh'),
              ),
            ],
          ),
          if (_games.isNotEmpty) ...[
            const SizedBox(height: 8),
            DropdownButtonFormField<String>(
              value: _gameId,
              dropdownColor: _kCard,
              decoration: const InputDecoration(
                labelText: 'Game',
                labelStyle: TextStyle(color: Color(0xFF6B7280)),
              ),
              style: const TextStyle(color: Colors.white),
              items: _games
                  .map(
                    (g) => DropdownMenuItem(
                      value: '${g['id']}',
                      child: Text(
                        '${g['away_team']} @ ${g['home_team']}',
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                  )
                  .toList(),
              onChanged: (v) {
                setState(() => _gameId = v);
                _loadComparison();
              },
            ),
          ],
          if (_error != null) ...[
            const SizedBox(height: 12),
            Text(_error!, style: const TextStyle(color: Color(0xFFEF4444), fontSize: 12)),
          ],
          if (_loading) const Center(child: Padding(padding: EdgeInsets.all(24), child: CircularProgressIndicator(color: _kTeal))),
          if (!_loading && _comparison != null) ...[
            const SizedBox(height: 16),
            _lineBlock('Spread (home)', _comparison!['spread_home']),
            _lineBlock('Spread (away)', _comparison!['spread_away']),
            _lineBlock('Total over', _comparison!['total_over']),
            _lineBlock('Total under', _comparison!['total_under']),
            _lineBlock('ML home', _comparison!['moneyline_home']),
            _lineBlock('ML away', _comparison!['moneyline_away']),
          ],
        ],
      ),
    );
  }

  Widget _lineBlock(String title, dynamic raw) {
    if (raw is! List || raw.isEmpty) return const SizedBox.shrink();
    return Padding(
      padding: const EdgeInsets.only(bottom: 14),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title.toUpperCase(),
            style: const TextStyle(
              color: Color(0xFF6B7280),
              fontSize: 10,
              fontWeight: FontWeight.w700,
              letterSpacing: 0.8,
            ),
          ),
          const SizedBox(height: 6),
          ...raw.map((row) {
            final m = Map<String, dynamic>.from(row as Map);
            final best = m['is_best'] == true;
            return Container(
              margin: const EdgeInsets.only(bottom: 4),
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
              decoration: BoxDecoration(
                color: best ? const Color(0xFF064E3B).withValues(alpha: 0.35) : _kCard,
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: const Color(0xFF27272A)),
              ),
              child: Row(
                children: [
                  Expanded(
                    child: Text(
                      '${m['sportsbook_display']}',
                      style: const TextStyle(color: Colors.white, fontSize: 12),
                    ),
                  ),
                  Text(
                    '${m['side']}',
                    style: const TextStyle(color: Color(0xFF9CA3AF), fontSize: 11),
                  ),
                  const SizedBox(width: 8),
                  Text(
                    '${m['line'] ?? '—'}  /  ${_fmtOdds(m['odds'])}',
                    style: const TextStyle(
                      color: _kTeal,
                      fontSize: 12,
                      fontWeight: FontWeight.w600,
                      fontFamily: 'monospace',
                    ),
                  ),
                ],
              ),
            );
          }),
        ],
      ),
    );
  }

  String _fmtOdds(dynamic o) {
    if (o is! num) return '—';
    final i = o.round();
    return i > 0 ? '+$i' : '$i';
  }
}
