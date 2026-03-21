import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
import '../services/api_service.dart';
import '../models/value_play.dart';
import '../models/arbitrage_opportunity.dart';
import '../models/line_movement.dart';
import '../models/bankroll.dart';
import '../models/portfolio.dart';

class AppState extends ChangeNotifier {
  AppState({ApiService? api}) : _api = api ?? ApiService();

  final ApiService _api;

  List<ValuePlay> valuePlays = [];
  List<ValuePlayV1> pmPlays = [];
  List<ArbitrageOpportunity> arbitrage = [];
  List<LineMovement> lineMovements = [];
  Bankroll? bankroll;
  PortfolioSnapshot? portfolio;

  bool loading = false;
  String? error;

  bool _isAuthenticated = false;
  String? _userId;
  String? _authToken;

  bool get isAuthenticated => _isAuthenticated;
  String? get userId => _userId;
  String? get authToken => _authToken;

  /// Returns the user's current tier from Supabase JWT app_metadata.
  String get currentTier {
    final meta = Supabase.instance.client.auth.currentUser?.appMetadata;
    return (meta?['tier'] as String?) ?? 'free';
  }

  /// Returns true if user has Pro or Sharp access.
  bool get hasProAccess {
    final tier = currentTier;
    return tier == 'pro' || tier == 'sharp';
  }

  /// Returns true if user has Sharp access.
  bool get hasSharpAccess => currentTier == 'sharp';

  /// Returns true if the current user is the platform operator.
  /// Operator-only — gates execution/swarm screens. Never true for subscribers.
  bool get isOperator {
    final meta = Supabase.instance.client.auth.currentUser?.appMetadata;
    return meta?['is_operator'] == true;
  }

  void setAuthenticated({required String userId, required String token}) {
    _isAuthenticated = true;
    _userId = userId;
    _authToken = token;
    notifyListeners();
  }

  void clearAuth() {
    _isAuthenticated = false;
    _userId = null;
    _authToken = null;
    portfolio = null;
    notifyListeners();
  }

  Future<PortfolioSnapshot?> _tryLoadPortfolio() async {
    if (_userId == null || _authToken == null) return null;
    try {
      return await _api.getPortfolio(userId: _userId!, token: _authToken!);
    } catch (_) {
      return null;
    }
  }

  Future<void> refresh() async {
    loading = true;
    error = null;
    notifyListeners();

    try {
      if (_authToken != null && _userId != null) {
        // Authenticated path — use v1 endpoints (+ bankroll keyed by Supabase user id)
        final results = await Future.wait([
          _api.getValuePlaysV1(token: _authToken),
          _api.getValuePlaysV1(sport: 'prediction_markets', token: _authToken),
          _api.getPmCorrelation(token: _authToken),
          _api.getLineMovement(token: _authToken),
          _api.getBankroll(userId: _userId),
          _tryLoadPortfolio(),
        ]);
        // v1 value plays go into the legacy valuePlays list via adapter
        final v1Plays = results[0] as List<ValuePlayV1>;
        valuePlays = v1Plays
            .map(
              (p) => ValuePlay(
                id: p.id,
                event: p.event,
                market: p.market,
                team: p.team,
                ourOdds: p.ourOdds,
                bookOdds: p.bookOdds,
                expectedValue: p.expectedValue,
                book: p.book,
                timestamp: DateTime.parse(p.timestamp),
              ),
            )
            .toList();
        pmPlays = results[1] as List<ValuePlayV1>;
        arbitrage = results[2] as List<ArbitrageOpportunity>;
        lineMovements = results[3] as List<LineMovement>;
        bankroll = results[4] as Bankroll;
        portfolio = results[5] as PortfolioSnapshot?;
        error = null;
      } else if (_authToken != null) {
        // Token without user id — skip personalized bankroll
        final results = await Future.wait([
          _api.getValuePlaysV1(token: _authToken),
          _api.getValuePlaysV1(sport: 'prediction_markets', token: _authToken),
          _api.getPmCorrelation(token: _authToken),
          _api.getLineMovement(token: _authToken),
        ]);
        final v1Plays = results[0] as List<ValuePlayV1>;
        valuePlays = v1Plays
            .map(
              (p) => ValuePlay(
                id: p.id,
                event: p.event,
                market: p.market,
                team: p.team,
                ourOdds: p.ourOdds,
                bookOdds: p.bookOdds,
                expectedValue: p.expectedValue,
                book: p.book,
                timestamp: DateTime.parse(p.timestamp),
              ),
            )
            .toList();
        pmPlays = results[1] as List<ValuePlayV1>;
        arbitrage = results[2] as List<ArbitrageOpportunity>;
        lineMovements = results[3] as List<LineMovement>;
        portfolio = null;
        error = null;
      } else {
        // Unauthenticated path — use legacy endpoints
        final results = await Future.wait([
          _api.getValuePlays(),
          _api.getArbitrageOpportunities(),
          _api.getLineMovements(),
          _api.getBankroll(),
        ]);
        valuePlays = results[0] as List<ValuePlay>;
        arbitrage = results[1] as List<ArbitrageOpportunity>;
        lineMovements = results[2] as List<LineMovement>;
        bankroll = results[3] as Bankroll;
        portfolio = null;
        error = null;
      }

      // Cache value plays after successful refresh
      try {
        final prefs = await SharedPreferences.getInstance();
        final json = jsonEncode(
          valuePlays.map((p) => {
            'id': p.id,
            'event': p.event,
            'market': p.market,
            'team': p.team,
            'our_odds': p.ourOdds,
            'book_odds': p.bookOdds,
            'expected_value': p.expectedValue,
            'book': p.book,
            'timestamp': p.timestamp.toIso8601String(),
          }).toList(),
        );
        await prefs.setString('cached_value_plays', json);
      } catch (_) {
        // Cache write failure is non-fatal — silently ignore
      }
    } on SocketException {
      await _loadFromCache();
    } on TimeoutException {
      await _loadFromCache();
    } catch (e) {
      error = e.toString();
    } finally {
      loading = false;
      notifyListeners();
    }
  }

  Future<void> _loadFromCache() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final cached = prefs.getString('cached_value_plays');
      if (cached != null && cached.isNotEmpty) {
        final list = jsonDecode(cached) as List<dynamic>;
        valuePlays = list
            .map((j) => ValuePlay.fromJson(j as Map<String, dynamic>))
            .toList();
        error = null;
      } else {
        error = 'Network unavailable — no cached data';
      }
    } catch (_) {
      error = 'Network unavailable — no cached data';
    }
  }

  @override
  void dispose() {
    _api.dispose();
    super.dispose();
  }
}
