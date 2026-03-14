class ValuePlay {
  final String id;
  final String event;
  final String market;
  final String team;
  final double ourOdds;
  final double bookOdds;
  final double expectedValue;
  final String book;
  final DateTime timestamp;

  const ValuePlay({
    required this.id,
    required this.event,
    required this.market,
    required this.team,
    required this.ourOdds,
    required this.bookOdds,
    required this.expectedValue,
    required this.book,
    required this.timestamp,
  });

  factory ValuePlay.fromJson(Map<String, dynamic> json) => ValuePlay(
        id: json['id'] as String,
        event: json['event'] as String,
        market: json['market'] as String,
        team: json['team'] as String,
        ourOdds: (json['our_odds'] as num).toDouble(),
        bookOdds: (json['book_odds'] as num).toDouble(),
        expectedValue: (json['expected_value'] as num).toDouble(),
        book: json['book'] as String,
        timestamp: DateTime.parse(json['timestamp'] as String),
      );
}

class ValuePlayV1 {
  final String id, event, market, team, book, timestamp;
  final double ourOdds, bookOdds, expectedValue, alphaScore;
  final String alphaBadge, regimeState;

  const ValuePlayV1({
    required this.id,
    required this.event,
    required this.market,
    required this.team,
    required this.book,
    required this.timestamp,
    required this.ourOdds,
    required this.bookOdds,
    required this.expectedValue,
    required this.alphaScore,
    required this.alphaBadge,
    required this.regimeState,
  });

  factory ValuePlayV1.fromJson(Map<String, dynamic> j) => ValuePlayV1(
        id: j['id'] as String,
        event: j['event'] as String,
        market: j['market'] as String,
        team: j['team'] as String,
        book: j['book'] as String,
        timestamp: j['timestamp'] as String,
        ourOdds: (j['our_odds'] as num).toDouble(),
        bookOdds: (j['book_odds'] as num).toDouble(),
        expectedValue: (j['expected_value'] as num).toDouble(),
        alphaScore: (j['alpha_score'] as num).toDouble(),
        alphaBadge: j['alpha_badge'] as String,
        regimeState: j['regime_state'] as String,
      );
}
