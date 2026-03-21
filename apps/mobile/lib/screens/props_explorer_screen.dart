import 'package:flutter/material.dart';
import '../copy/microcopy.dart';
import '../services/api_service.dart';

const _kTeal = Color(0xFF10B981);
const _kBg = Color(0xFF0A0A0A);
const _kCard = Color(0xFF141414);

final _api = ApiService();

class PropsExplorerScreen extends StatefulWidget {
  const PropsExplorerScreen({super.key});

  @override
  State<PropsExplorerScreen> createState() => _PropsExplorerScreenState();
}

class _PropsExplorerScreenState extends State<PropsExplorerScreen> {
  static const _sports = ['NFL', 'NBA', 'MLB', 'NHL', 'NCAAF', 'NCAAB'];

  String _sport = 'NBA';
  final _marketCtrl = TextEditingController(text: 'player_points');
  List<Map<String, dynamic>> _games = [];
  String? _gameId;
  List<Map<String, dynamic>> _outcomes = [];
  bool _loading = false;
  String? _error;

  @override
  void dispose() {
    _marketCtrl.dispose();
    super.dispose();
  }

  @override
  void initState() {
    super.initState();
    _loadGames();
  }

  Future<void> _loadGames() async {
    setState(() {
      _loading = true;
      _error = null;
      _outcomes = [];
    });
    try {
      final raw = await _api.getOddsGames(sport: _sport);
      _games = raw.map((e) => Map<String, dynamic>.from(e as Map)).toList();
      _gameId = _games.isNotEmpty ? '${_games.first['id']}' : null;
    } catch (e) {
      _error = e.toString();
      _games = [];
      _gameId = null;
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _loadProps() async {
    final gid = _gameId;
    if (gid == null) return;
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final map = await _api.getOddsProps(
        sport: _sport,
        marketKey: _marketCtrl.text.trim(),
        gameId: gid,
      );
      final raw = map['outcomes'];
      if (raw is List) {
        _outcomes = raw.map((e) => Map<String, dynamic>.from(e as Map)).toList();
      } else {
        _outcomes = [];
      }
    } catch (e) {
      _error = e.toString();
      _outcomes = [];
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
        title: const Text(Microcopy.propsPageTitle),
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Text(
            Microcopy.propsPageSubtitle,
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
              onChanged: (v) => setState(() => _gameId = v),
            ),
          ],
          const SizedBox(height: 12),
          TextField(
            controller: _marketCtrl,
            style: const TextStyle(color: Colors.white, fontSize: 14),
            decoration: const InputDecoration(
              labelText: 'Market key (Odds API)',
              labelStyle: TextStyle(color: Color(0xFF6B7280)),
              hintText: 'player_points, player_pass_tds, …',
              hintStyle: TextStyle(color: Color(0xFF52525B)),
            ),
          ),
          const SizedBox(height: 12),
          SizedBox(
            width: double.infinity,
            child: TextButton(
              onPressed: _loading ? null : _loadProps,
              style: TextButton.styleFrom(
                backgroundColor: _kTeal,
                padding: const EdgeInsets.symmetric(vertical: 12),
              ),
              child: const Text(
                'Load props',
                style: TextStyle(color: Colors.white, fontWeight: FontWeight.w600),
              ),
            ),
          ),
          if (_error != null) ...[
            const SizedBox(height: 12),
            Text(_error!, style: const TextStyle(color: Color(0xFFEF4444), fontSize: 12)),
          ],
          if (_loading)
            const Padding(
              padding: EdgeInsets.all(24),
              child: Center(child: CircularProgressIndicator(color: _kTeal)),
            ),
          ..._outcomes.map(
            (o) => Padding(
              padding: const EdgeInsets.only(top: 8),
              child: Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: _kCard,
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: const Color(0xFF27272A)),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      '${o['outcome_name']}',
                      style: const TextStyle(
                        color: Colors.white,
                        fontWeight: FontWeight.w600,
                        fontSize: 13,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      '${o['sportsbook_display']}  ·  ${_fmtOdds(o['price'])}'
                      '${o['point'] != null ? '  ·  ${o['point']}' : ''}',
                      style: const TextStyle(color: Color(0xFF9CA3AF), fontSize: 11),
                    ),
                  ],
                ),
              ),
            ),
          ),
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
