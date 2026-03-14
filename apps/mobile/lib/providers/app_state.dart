import 'package:flutter/foundation.dart';
import '../services/api_service.dart';
import '../models/value_play.dart';
import '../models/arbitrage_opportunity.dart';
import '../models/line_movement.dart';
import '../models/bankroll.dart';

class AppState extends ChangeNotifier {
  AppState({ApiService? api}) : _api = api ?? ApiService();

  final ApiService _api;

  List<ValuePlay> valuePlays = [];
  List<ArbitrageOpportunity> arbitrage = [];
  List<LineMovement> lineMovements = [];
  Bankroll? bankroll;

  bool loading = false;
  String? error;

  bool _isAuthenticated = false;
  String? _userId;
  String? _authToken;

  bool get isAuthenticated => _isAuthenticated;
  String? get userId => _userId;
  String? get authToken => _authToken;

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
    notifyListeners();
  }

  Future<void> refresh() async {
    loading = true;
    error = null;
    notifyListeners();

    try {
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
      error = null;
    } catch (e) {
      error = e.toString();
    } finally {
      loading = false;
      notifyListeners();
    }
  }

  @override
  void dispose() {
    _api.dispose();
    super.dispose();
  }
}
