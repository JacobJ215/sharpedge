class ArbitrageOpportunity {
  final String id;
  final String event;
  final String market;
  final double profitPercent;
  final List<ArbitrageLeg> legs;
  final DateTime timestamp;

  const ArbitrageOpportunity({
    required this.id,
    required this.event,
    required this.market,
    required this.profitPercent,
    required this.legs,
    required this.timestamp,
  });

  factory ArbitrageOpportunity.fromJson(Map<String, dynamic> json) =>
      ArbitrageOpportunity(
        id: json['id'] as String,
        event: json['event'] as String,
        market: json['market'] as String,
        profitPercent: (json['profit_percent'] as num).toDouble(),
        legs: (json['legs'] as List<dynamic>)
            .map((l) => ArbitrageLeg.fromJson(l as Map<String, dynamic>))
            .toList(),
        timestamp: DateTime.parse(json['timestamp'] as String),
      );
}

class ArbitrageLeg {
  final String book;
  final String side;
  final double odds;
  final double stake;

  const ArbitrageLeg({
    required this.book,
    required this.side,
    required this.odds,
    required this.stake,
  });

  factory ArbitrageLeg.fromJson(Map<String, dynamic> json) => ArbitrageLeg(
        book: json['book'] as String,
        side: json['side'] as String,
        odds: (json['odds'] as num).toDouble(),
        stake: (json['stake'] as num).toDouble(),
      );
}
