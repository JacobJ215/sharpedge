import 'dart:convert';
import 'package:http/http.dart' as http;
import '../models/value_play.dart';
import '../models/arbitrage_opportunity.dart';
import '../models/line_movement.dart';
import '../models/bankroll.dart';
import '../models/portfolio.dart';
import '../models/game_analysis.dart';

class ApiService {
  static const String _baseUrl = String.fromEnvironment('API_BASE_URL', defaultValue: 'http://localhost:8000');

  // Public base URL accessor (used by CopilotScreen for SSE streaming)
  static String get baseUrl => _baseUrl;

  // v1 API base
  static String get _baseUrlV1 => '$_baseUrl/api/v1';

  final http.Client _client;

  ApiService({http.Client? client}) : _client = client ?? http.Client();

  Future<List<ValuePlay>> getValuePlays() async {
    final response = await _client.get(Uri.parse('$_baseUrl/api/value-plays'));
    if (response.statusCode != 200) {
      throw ApiException('Failed to load value plays: ${response.statusCode}');
    }
    final List<dynamic> data = jsonDecode(response.body) as List<dynamic>;
    return data.map((j) => ValuePlay.fromJson(j as Map<String, dynamic>)).toList();
  }

  Future<List<ArbitrageOpportunity>> getArbitrageOpportunities() async {
    final response = await _client.get(Uri.parse('$_baseUrl/api/arbitrage'));
    if (response.statusCode != 200) {
      throw ApiException('Failed to load arbitrage: ${response.statusCode}');
    }
    final List<dynamic> data = jsonDecode(response.body) as List<dynamic>;
    return data
        .map((j) => ArbitrageOpportunity.fromJson(j as Map<String, dynamic>))
        .toList();
  }

  Future<List<LineMovement>> getLineMovements() async {
    final response = await _client.get(Uri.parse('$_baseUrl/api/line-movements'));
    if (response.statusCode != 200) {
      throw ApiException('Failed to load line movements: ${response.statusCode}');
    }
    final List<dynamic> data = jsonDecode(response.body) as List<dynamic>;
    return data
        .map((j) => LineMovement.fromJson(j as Map<String, dynamic>))
        .toList();
  }

  /// When [userId] is set, must be Supabase Auth UUID (server maps to internal user row).
  Future<Bankroll> getBankroll({String? userId}) async {
    final uri = userId != null && userId.isNotEmpty
        ? Uri.parse('$_baseUrl/api/bankroll').replace(queryParameters: {'user_id': userId})
        : Uri.parse('$_baseUrl/api/bankroll');
    final response = await _client.get(uri);
    if (response.statusCode != 200) {
      throw ApiException('Failed to load bankroll: ${response.statusCode}');
    }
    return Bankroll.fromJson(jsonDecode(response.body) as Map<String, dynamic>);
  }

  /// GET /api/v1/value-plays — returns alpha-enriched plays
  Future<List<ValuePlayV1>> getValuePlaysV1({
    double? minAlpha,
    String? sport,
    int limit = 50,
    String? token,
  }) async {
    final params = <String, String>{
      if (minAlpha != null) 'min_alpha': minAlpha.toString(),
      if (sport != null) 'sport': sport,
      'limit': limit.toString(),
    };
    final uri = Uri.parse('$_baseUrlV1/value-plays').replace(queryParameters: params);
    final headers = <String, String>{};
    if (token != null) headers['Authorization'] = 'Bearer $token';
    final response = await _client.get(uri, headers: headers);
    if (response.statusCode != 200) {
      throw ApiException('getValuePlaysV1 failed: ${response.statusCode}');
    }
    final data = jsonDecode(response.body) as List<dynamic>;
    return data.map((j) => ValuePlayV1.fromJson(j as Map<String, dynamic>)).toList();
  }

  /// GET /api/v1/prediction-markets/correlation — returns PM correlation data
  Future<List<ArbitrageOpportunity>> getPmCorrelation({String? token}) async {
    final uri = Uri.parse('$_baseUrlV1/prediction-markets/correlation');
    final headers = <String, String>{};
    if (token != null) headers['Authorization'] = 'Bearer $token';
    final response = await _client.get(uri, headers: headers);
    if (response.statusCode != 200) {
      throw ApiException('getPmCorrelation failed: ${response.statusCode}');
    }
    final data = jsonDecode(response.body) as List<dynamic>;
    final results = <ArbitrageOpportunity>[];
    for (final item in data) {
      try {
        results.add(ArbitrageOpportunity.fromJson(item as Map<String, dynamic>));
      } catch (_) {
        // Skip items that do not match the full ArbitrageOpportunity schema
      }
    }
    return results;
  }

  /// GET /api/v1/line-movement — returns line movement data from the live scanner
  Future<List<LineMovement>> getLineMovement({String? token}) async {
    final uri = Uri.parse('$_baseUrlV1/line-movement');
    final headers = <String, String>{};
    if (token != null) headers['Authorization'] = 'Bearer $token';
    final response = await _client.get(uri, headers: headers);
    if (response.statusCode != 200) {
      throw ApiException('getLineMovement failed: ${response.statusCode}');
    }
    final data = jsonDecode(response.body) as List<dynamic>;
    final results = <LineMovement>[];
    for (final item in data) {
      try {
        results.add(LineMovement.fromJson(item as Map<String, dynamic>));
      } catch (_) {
        // Skip items that do not match the full LineMovement schema
      }
    }
    return results;
  }

  /// GET /api/v1/users/{id}/portfolio — requires auth token
  Future<PortfolioSnapshot> getPortfolio({
    required String userId,
    required String token,
  }) async {
    final uri = Uri.parse('$_baseUrlV1/users/$userId/portfolio');
    final response = await _client.get(
      uri,
      headers: {'Authorization': 'Bearer $token'},
    );
    if (response.statusCode != 200) {
      throw ApiException('getPortfolio failed: ${response.statusCode}');
    }
    final map = jsonDecode(response.body) as Map<String, dynamic>;
    return PortfolioSnapshot.fromJson(map);
  }

  /// GET /api/v1/games/{gameId}/analysis — public
  Future<GameAnalysisSnapshot> getGameAnalysis(String gameId) async {
    final uri = Uri.parse('$_baseUrlV1/games/$gameId/analysis');
    final response = await _client.get(uri);
    if (response.statusCode != 200) {
      throw ApiException('getGameAnalysis failed: ${response.statusCode}');
    }
    final map = jsonDecode(response.body) as Map<String, dynamic>;
    return GameAnalysisSnapshot.fromJson(map);
  }

  /// GET /api/v1/odds/games — public (requires server ODDS_API_KEY)
  Future<List<dynamic>> getOddsGames({
    required String sport,
    String? marketsCsv,
  }) async {
    final params = <String, String>{'sport': sport};
    if (marketsCsv != null && marketsCsv.isNotEmpty) {
      params['markets'] = marketsCsv;
    }
    final uri = Uri.parse('$_baseUrlV1/odds/games').replace(queryParameters: params);
    final response = await _client.get(uri);
    if (response.statusCode != 200) {
      throw ApiException('getOddsGames failed: ${response.statusCode} ${response.body}');
    }
    return jsonDecode(response.body) as List<dynamic>;
  }

  /// GET /api/v1/odds/line-comparison — public
  Future<Map<String, dynamic>> getOddsLineComparison({
    required String sport,
    String? gameId,
    String? query,
  }) async {
    final params = <String, String>{'sport': sport};
    if (gameId != null && gameId.isNotEmpty) params['game_id'] = gameId;
    if (query != null && query.isNotEmpty) params['q'] = query;
    final uri = Uri.parse('$_baseUrlV1/odds/line-comparison').replace(queryParameters: params);
    final response = await _client.get(uri);
    if (response.statusCode != 200) {
      throw ApiException(
        'getOddsLineComparison failed: ${response.statusCode} ${response.body}',
      );
    }
    return jsonDecode(response.body) as Map<String, dynamic>;
  }

  /// GET /api/v1/odds/props — public
  Future<Map<String, dynamic>> getOddsProps({
    required String sport,
    required String marketKey,
    String? gameId,
    String? query,
  }) async {
    final params = <String, String>{
      'sport': sport,
      'market_key': marketKey,
    };
    if (gameId != null && gameId.isNotEmpty) params['game_id'] = gameId;
    if (query != null && query.isNotEmpty) params['q'] = query;
    final uri = Uri.parse('$_baseUrlV1/odds/props').replace(queryParameters: params);
    final response = await _client.get(uri);
    if (response.statusCode != 200) {
      throw ApiException('getOddsProps failed: ${response.statusCode} ${response.body}');
    }
    return jsonDecode(response.body) as Map<String, dynamic>;
  }

  /// POST /api/v1/bankroll/simulate — public endpoint
  Future<Map<String, dynamic>> simulateBankroll({
    required double bankroll,
    required double betSize,
    required int numBets,
    required double winRate,
  }) async {
    final uri = Uri.parse('$_baseUrlV1/bankroll/simulate');
    final response = await _client.post(uri,
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({
        'bankroll': bankroll,
        'bet_size': betSize,
        'num_bets': numBets,
        'win_rate': winRate,
      }),
    );
    if (response.statusCode != 200) {
      throw ApiException('simulateBankroll failed: ${response.statusCode}');
    }
    return jsonDecode(response.body) as Map<String, dynamic>;
  }

  /// POST /api/v1/bets — log a confirmed bet (requires auth)
  Future<Map<String, dynamic>> logBet({
    required String playId,
    required String event,
    required String market,
    required String team,
    required String book,
    required double stake,
    required String token,
  }) async {
    final uri = Uri.parse('$_baseUrlV1/bets');
    final response = await _client.post(
      uri,
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer $token',
      },
      body: jsonEncode({
        'play_id': playId,
        'event': event,
        'market': market,
        'team': team,
        'book': book,
        'stake': stake,
      }),
    );
    // Accept 200 or 201 — endpoint may return either
    if (response.statusCode != 200 && response.statusCode != 201) {
      throw ApiException('logBet failed: ${response.statusCode}');
    }
    return jsonDecode(response.body) as Map<String, dynamic>;
  }

  void dispose() => _client.close();
}

class ApiException implements Exception {
  final String message;
  const ApiException(this.message);

  @override
  String toString() => 'ApiException: $message';
}
