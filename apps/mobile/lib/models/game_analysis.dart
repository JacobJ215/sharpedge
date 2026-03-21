// GET /api/v1/games/{game_id}/analysis

class InjuryRow {
  final String? team;
  final String? playerName;
  final String? position;
  final String? status;
  final String? injuryType;
  final bool isKeyPlayer;
  final double? impactRating;

  const InjuryRow({
    this.team,
    this.playerName,
    this.position,
    this.status,
    this.injuryType,
    this.isKeyPlayer = false,
    this.impactRating,
  });

  factory InjuryRow.fromJson(Map<String, dynamic> j) => InjuryRow(
        team: j['team'] as String?,
        playerName: j['player_name'] as String?,
        position: j['position'] as String?,
        status: j['status'] as String?,
        injuryType: j['injury_type'] as String?,
        isKeyPlayer: j['is_key_player'] == true,
        impactRating: (j['impact_rating'] as num?)?.toDouble(),
      );
}

class GameAnalysisSnapshot {
  final String gameId;
  final double winProbability;
  final String confidence;
  final double evPercentage;
  final double fairOdds;
  final double marketOdds;
  final String regimeState;
  final String? keyNumberProximity;
  final double alphaScore;
  final String alphaBadge;
  final List<InjuryRow> injuries;

  const GameAnalysisSnapshot({
    required this.gameId,
    required this.winProbability,
    required this.confidence,
    required this.evPercentage,
    required this.fairOdds,
    required this.marketOdds,
    required this.regimeState,
    this.keyNumberProximity,
    required this.alphaScore,
    required this.alphaBadge,
    required this.injuries,
  });

  factory GameAnalysisSnapshot.fromJson(Map<String, dynamic> j) {
    final model = j['model_prediction'] as Map<String, dynamic>? ?? {};
    final ev = j['ev_breakdown'] as Map<String, dynamic>? ?? {};
    final rawInj = j['injuries'];
    final injuries = <InjuryRow>[];
    if (rawInj is List<dynamic>) {
      for (final e in rawInj) {
        if (e is Map<String, dynamic>) {
          injuries.add(InjuryRow.fromJson(e));
        } else if (e is Map) {
          injuries.add(InjuryRow.fromJson(Map<String, dynamic>.from(e)));
        }
      }
    }
    return GameAnalysisSnapshot(
      gameId: '${j['game_id'] ?? ''}',
      winProbability: (model['win_probability'] as num?)?.toDouble() ?? 0,
      confidence: '${model['confidence'] ?? 'MEDIUM'}',
      evPercentage: (ev['ev_percentage'] as num?)?.toDouble() ?? 0,
      fairOdds: (ev['fair_odds'] as num?)?.toDouble() ?? 0,
      marketOdds: (ev['market_odds'] as num?)?.toDouble() ?? 0,
      regimeState: '${j['regime_state'] ?? 'UNKNOWN'}',
      keyNumberProximity: j['key_number_proximity'] as String?,
      alphaScore: (j['alpha_score'] as num?)?.toDouble() ?? 0,
      alphaBadge: '${j['alpha_badge'] ?? 'SPECULATIVE'}',
      injuries: injuries,
    );
  }
}
