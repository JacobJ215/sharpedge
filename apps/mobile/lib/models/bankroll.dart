class Bankroll {
  final double balance;
  final double startingBalance;
  final double totalWagered;
  final double totalReturned;
  final int betsPlaced;
  final int betsWon;
  final int betsLost;
  final int betsPending;
  final double roi;
  final double winRate;
  final List<BankrollEntry> history;

  const Bankroll({
    required this.balance,
    required this.startingBalance,
    required this.totalWagered,
    required this.totalReturned,
    required this.betsPlaced,
    required this.betsWon,
    required this.betsLost,
    required this.betsPending,
    required this.roi,
    required this.winRate,
    required this.history,
  });

  double get profit => balance - startingBalance;

  factory Bankroll.fromJson(Map<String, dynamic> json) => Bankroll(
        balance: (json['balance'] as num).toDouble(),
        startingBalance: (json['starting_balance'] as num).toDouble(),
        totalWagered: (json['total_wagered'] as num).toDouble(),
        totalReturned: (json['total_returned'] as num).toDouble(),
        betsPlaced: json['bets_placed'] as int,
        betsWon: json['bets_won'] as int,
        betsLost: json['bets_lost'] as int,
        betsPending: json['bets_pending'] as int,
        roi: (json['roi'] as num).toDouble(),
        winRate: (json['win_rate'] as num).toDouble(),
        history: (json['history'] as List<dynamic>)
            .map((e) => BankrollEntry.fromJson(e as Map<String, dynamic>))
            .toList(),
      );
}

class BankrollEntry {
  final double balance;
  final DateTime at;

  const BankrollEntry({required this.balance, required this.at});

  factory BankrollEntry.fromJson(Map<String, dynamic> json) => BankrollEntry(
        balance: (json['balance'] as num).toDouble(),
        at: DateTime.parse(json['at'] as String),
      );
}
