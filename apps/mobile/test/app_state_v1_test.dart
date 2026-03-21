/// RED stubs for WIRE-04: AppState v1 migration.
///
/// These tests fail because AppState.refresh() still calls getValuePlays()
/// (old stub route) instead of getValuePlaysV1() (the v1 alpha endpoint).
///
/// Tests pass once Wave 2 wires refresh() to use getValuePlaysV1 with auth token.
library;

import 'package:flutter_test/flutter_test.dart';
import 'package:sharpedge_mobile/providers/app_state.dart';
import 'package:sharpedge_mobile/services/api_service.dart';
import 'package:sharpedge_mobile/models/value_play.dart';
import 'package:sharpedge_mobile/models/arbitrage_opportunity.dart';
import 'package:sharpedge_mobile/models/line_movement.dart';
import 'package:sharpedge_mobile/models/bankroll.dart';
import 'package:sharpedge_mobile/models/portfolio.dart';

/// A subclass of ApiService that tracks which methods were called.
/// Overrides only the methods relevant to the test.
class MockApiService extends ApiService {
  bool getValuePlaysCalled = false;
  bool getValuePlaysV1Called = false;
  String? lastAuthToken;

  @override
  Future<List<ValuePlay>> getValuePlays() async {
    getValuePlaysCalled = true;
    return [];
  }

  @override
  Future<List<ValuePlayV1>> getValuePlaysV1({
    double? minAlpha,
    String? sport,
    int limit = 50,
    String? token,
  }) async {
    getValuePlaysV1Called = true;
    lastAuthToken = token;
    return [];
  }

  @override
  Future<List<ArbitrageOpportunity>> getArbitrageOpportunities() async => [];

  @override
  Future<List<LineMovement>> getLineMovements() async => [];

  @override
  Future<Bankroll> getBankroll({String? userId}) async => const Bankroll(
        balance: 1000.0,
        startingBalance: 1000.0,
        totalWagered: 0.0,
        totalReturned: 0.0,
        betsPlaced: 0,
        betsWon: 0,
        betsLost: 0,
        betsPending: 0,
        roi: 0.0,
        winRate: 0.0,
        history: [],
      );

  @override
  Future<PortfolioSnapshot> getPortfolio({
    required String userId,
    required String token,
  }) async =>
      const PortfolioSnapshot(
        unitSize: 0,
        roiPct: 0,
        winRateFraction: 0,
        bySport: [],
        byBetType: [],
        byBook: [],
        byJuice: [],
      );
}

void main() {
  group('AppState v1 migration — WIRE-04 RED stubs', () {
    test(
      'test_refresh_calls_get_value_plays_v1: refresh() calls getValuePlaysV1 not getValuePlays',
      () async {
        // RED: AppState.refresh() still calls getValuePlays() (old route).
        // This test will fail because getValuePlaysV1Called == false
        // after refresh() when auth is set.
        final mock = MockApiService();
        final state = AppState(api: mock);

        state.setAuthenticated(userId: 'user-123', token: 'test-token');
        await state.refresh();

        // Expect v1 method was called (not the old stub route)
        expect(
          mock.getValuePlaysV1Called,
          isTrue,
          reason: 'AppState.refresh() must call getValuePlaysV1 when authenticated (WIRE-04)',
        );
        expect(
          mock.getValuePlaysCalled,
          isFalse,
          reason: 'AppState.refresh() must NOT call the old getValuePlays route when authenticated',
        );
      },
    );

    test(
      'test_refresh_forwards_auth_token: refresh() passes _authToken to API calls',
      () async {
        // RED: AppState.refresh() does not pass _authToken to API calls yet.
        final mock = MockApiService();
        final state = AppState(api: mock);

        state.setAuthenticated(userId: 'user-456', token: 'bearer-abc123');
        await state.refresh();

        expect(
          mock.lastAuthToken,
          equals('bearer-abc123'),
          reason: 'AppState.refresh() must forward _authToken to getValuePlaysV1 (WIRE-04)',
        );
      },
    );
  });
}
