// Parsed GET /api/v1/users/{id}/portfolio (breakdown slices + unit size).

class PortfolioSplitRow {
  final String label;
  final int totalBets;
  final int wins;
  final int losses;
  final double winRate;
  final double roi;

  const PortfolioSplitRow({
    required this.label,
    required this.totalBets,
    required this.wins,
    required this.losses,
    required this.winRate,
    required this.roi,
  });

  static double _num(dynamic v, [double d = 0]) => v is num ? v.toDouble() : d;

  static int _int(dynamic v, [int d = 0]) {
    if (v is int) return v;
    if (v is num) return v.toInt();
    return d;
  }

  static PortfolioSplitRow fromSport(Map<String, dynamic> j) => PortfolioSplitRow(
        label: '${j['sport'] ?? ''}',
        totalBets: _int(j['total_bets']),
        wins: _int(j['wins']),
        losses: _int(j['losses']),
        winRate: _num(j['win_rate']),
        roi: _num(j['roi']),
      );

  static PortfolioSplitRow fromBetType(Map<String, dynamic> j) => PortfolioSplitRow(
        label: '${j['bet_type'] ?? ''}',
        totalBets: _int(j['total_bets']),
        wins: _int(j['wins']),
        losses: _int(j['losses']),
        winRate: _num(j['win_rate']),
        roi: _num(j['roi']),
      );

  static PortfolioSplitRow fromBook(Map<String, dynamic> j) => PortfolioSplitRow(
        label: '${j['sportsbook'] ?? ''}',
        totalBets: _int(j['total_bets']),
        wins: _int(j['wins']),
        losses: _int(j['losses']),
        winRate: _num(j['win_rate']),
        roi: _num(j['roi']),
      );

  static PortfolioSplitRow fromJuice(Map<String, dynamic> j) => PortfolioSplitRow(
        label: '${j['bucket'] ?? ''}',
        totalBets: _int(j['total_bets']),
        wins: _int(j['wins']),
        losses: _int(j['losses']),
        winRate: _num(j['win_rate']),
        roi: _num(j['roi']),
      );
}

class ActivePortfolioBet {
  final String id;
  final String event;
  final double stake;
  final String book;

  const ActivePortfolioBet({
    required this.id,
    required this.event,
    required this.stake,
    required this.book,
  });

  factory ActivePortfolioBet.fromJson(Map<String, dynamic> j) => ActivePortfolioBet(
        id: '${j['id'] ?? ''}',
        event: '${j['event'] ?? ''}',
        stake: (j['stake'] as num?)?.toDouble() ?? 0,
        book: '${j['book'] ?? ''}',
      );
}

class RoiHistoryPoint {
  final String date;
  final double roi;

  const RoiHistoryPoint({required this.date, required this.roi});

  factory RoiHistoryPoint.fromJson(Map<String, dynamic> j) => RoiHistoryPoint(
        date: '${j['date'] ?? ''}',
        roi: (j['roi'] as num?)?.toDouble() ?? 0,
      );
}

class BankrollHistoryPoint {
  final String date;
  final double bankroll;

  const BankrollHistoryPoint({required this.date, required this.bankroll});

  factory BankrollHistoryPoint.fromJson(Map<String, dynamic> j) => BankrollHistoryPoint(
        date: '${j['date'] ?? ''}',
        bankroll: (j['bankroll'] as num?)?.toDouble() ?? 0,
      );
}

class PortfolioSnapshot {
  /// Server sends win rate as 0–1 fraction.
  final double unitSize;
  final double roiPct;
  final double winRateFraction;
  /// Average CLV from settled bets (same units as server).
  final double clvAverage;
  /// Peak-to-trough drawdown in profit dollars (API `drawdown`).
  final double drawdown;
  final int totalBets;
  final int wins;
  final int losses;
  final List<ActivePortfolioBet> activeBets;
  final List<RoiHistoryPoint> roiHistory;
  final List<BankrollHistoryPoint> bankrollHistory;
  final List<PortfolioSplitRow> bySport;
  final List<PortfolioSplitRow> byBetType;
  final List<PortfolioSplitRow> byBook;
  final List<PortfolioSplitRow> byJuice;

  const PortfolioSnapshot({
    required this.unitSize,
    required this.roiPct,
    required this.winRateFraction,
    this.clvAverage = 0,
    this.drawdown = 0,
    this.totalBets = 0,
    this.wins = 0,
    this.losses = 0,
    this.activeBets = const [],
    this.roiHistory = const [],
    this.bankrollHistory = const [],
    required this.bySport,
    required this.byBetType,
    required this.byBook,
    required this.byJuice,
  });

  factory PortfolioSnapshot.fromJson(Map<String, dynamic> j) {
    List<PortfolioSplitRow> mapList(
      dynamic list,
      PortfolioSplitRow Function(Map<String, dynamic>) f,
    ) {
      if (list is! List<dynamic>) return [];
      final out = <PortfolioSplitRow>[];
      for (final e in list) {
        if (e is Map<String, dynamic>) {
          out.add(f(e));
        } else if (e is Map) {
          out.add(f(Map<String, dynamic>.from(e)));
        }
      }
      return out;
    }

    List<ActivePortfolioBet> mapActive(dynamic list) {
      if (list is! List<dynamic>) return [];
      final out = <ActivePortfolioBet>[];
      for (final e in list) {
        if (e is Map<String, dynamic>) {
          out.add(ActivePortfolioBet.fromJson(e));
        } else if (e is Map) {
          out.add(ActivePortfolioBet.fromJson(Map<String, dynamic>.from(e)));
        }
      }
      return out;
    }

    List<RoiHistoryPoint> mapRoi(dynamic list) {
      if (list is! List<dynamic>) return [];
      final out = <RoiHistoryPoint>[];
      for (final e in list) {
        if (e is Map<String, dynamic>) {
          out.add(RoiHistoryPoint.fromJson(e));
        } else if (e is Map) {
          out.add(RoiHistoryPoint.fromJson(Map<String, dynamic>.from(e)));
        }
      }
      return out;
    }

    List<BankrollHistoryPoint> mapBankrollHist(dynamic list) {
      if (list is! List<dynamic>) return [];
      final out = <BankrollHistoryPoint>[];
      for (final e in list) {
        if (e is Map<String, dynamic>) {
          out.add(BankrollHistoryPoint.fromJson(e));
        } else if (e is Map) {
          out.add(BankrollHistoryPoint.fromJson(Map<String, dynamic>.from(e)));
        }
      }
      return out;
    }

    return PortfolioSnapshot(
      unitSize: (j['unit_size'] as num?)?.toDouble() ?? 0,
      roiPct: (j['roi'] as num?)?.toDouble() ?? 0,
      winRateFraction: (j['win_rate'] as num?)?.toDouble() ?? 0,
      clvAverage: (j['clv_average'] as num?)?.toDouble() ?? 0,
      drawdown: (j['drawdown'] as num?)?.toDouble() ?? 0,
      totalBets: PortfolioSplitRow._int(j['total_bets']),
      wins: PortfolioSplitRow._int(j['wins']),
      losses: PortfolioSplitRow._int(j['losses']),
      activeBets: mapActive(j['active_bets']),
      roiHistory: mapRoi(j['roi_history']),
      bankrollHistory: mapBankrollHist(j['bankroll_history']),
      bySport: mapList(j['by_sport'], PortfolioSplitRow.fromSport),
      byBetType: mapList(j['by_bet_type'], PortfolioSplitRow.fromBetType),
      byBook: mapList(j['by_book'], PortfolioSplitRow.fromBook),
      byJuice: mapList(j['by_juice'], PortfolioSplitRow.fromJuice),
    );
  }
}
