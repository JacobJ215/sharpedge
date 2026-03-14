import 'dart:convert';
import 'package:http/http.dart' as http;
import '../models/value_play.dart';
import '../models/arbitrage_opportunity.dart';
import '../models/line_movement.dart';
import '../models/bankroll.dart';

class ApiService {
  static const String _baseUrl = String.fromEnvironment('API_BASE_URL', defaultValue: 'http://localhost:8000');

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

  Future<Bankroll> getBankroll() async {
    final response = await _client.get(Uri.parse('$_baseUrl/api/bankroll'));
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

  /// GET /api/v1/users/{id}/portfolio — requires auth token
  Future<Map<String, dynamic>> getPortfolio(String userId, String token) async {
    final uri = Uri.parse('$_baseUrlV1/users/$userId/portfolio');
    final response = await _client.get(uri,
        headers: {'Authorization': 'Bearer $token'});
    if (response.statusCode != 200) {
      throw ApiException('getPortfolio failed: ${response.statusCode}');
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

  void dispose() => _client.close();
}

class ApiException implements Exception {
  final String message;
  const ApiException(this.message);

  @override
  String toString() => 'ApiException: $message';
}
