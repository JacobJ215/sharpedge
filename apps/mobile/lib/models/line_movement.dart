class LineMovement {
  final String id;
  final String event;
  final String market;
  final double openLine;
  final double currentLine;
  final double movement;
  final String direction;
  final List<LineSnapshot> history;
  final DateTime timestamp;

  const LineMovement({
    required this.id,
    required this.event,
    required this.market,
    required this.openLine,
    required this.currentLine,
    required this.movement,
    required this.direction,
    required this.history,
    required this.timestamp,
  });

  factory LineMovement.fromJson(Map<String, dynamic> json) => LineMovement(
        id: json['id'] as String,
        event: json['event'] as String,
        market: json['market'] as String,
        openLine: (json['open_line'] as num).toDouble(),
        currentLine: (json['current_line'] as num).toDouble(),
        movement: (json['movement'] as num).toDouble(),
        direction: json['direction'] as String,
        history: (json['history'] as List<dynamic>)
            .map((s) => LineSnapshot.fromJson(s as Map<String, dynamic>))
            .toList(),
        timestamp: DateTime.parse(json['timestamp'] as String),
      );
}

class LineSnapshot {
  final double line;
  final DateTime at;

  const LineSnapshot({required this.line, required this.at});

  factory LineSnapshot.fromJson(Map<String, dynamic> json) => LineSnapshot(
        line: (json['line'] as num).toDouble(),
        at: DateTime.parse(json['at'] as String),
      );
}
