/// RED stubs for WIRE-04: Offline cache behavior.
///
/// These tests fail because AppState has no offline cache implemented:
/// - On network failure, error is set but valuePlays is empty (no cache read)
/// - SharedPreferences key 'cached_value_plays' is never written
///
/// Tests pass once Wave 2 implements SharedPreferences-backed offline cache.
library;

import 'dart:io';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sharpedge_mobile/providers/app_state.dart';
import 'package:sharpedge_mobile/services/api_service.dart';
import 'package:sharpedge_mobile/models/value_play.dart';
import 'package:sharpedge_mobile/models/arbitrage_opportunity.dart';
import 'package:sharpedge_mobile/models/line_movement.dart';
import 'package:sharpedge_mobile/models/bankroll.dart';

Bankroll _emptyBankroll() => const Bankroll(
      balance: 0.0,
      startingBalance: 0.0,
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

/// A subclass of ApiService that throws SocketException on all calls.
class NetworkFailureApiService extends ApiService {
  @override
  Future<List<ValuePlay>> getValuePlays() async {
    throw const SocketException('Network unreachable');
  }

  @override
  Future<List<ValuePlayV1>> getValuePlaysV1({
    double? minAlpha,
    String? sport,
    int limit = 50,
    String? token,
  }) async {
    throw const SocketException('Network unreachable');
  }

  @override
  Future<List<ArbitrageOpportunity>> getArbitrageOpportunities() async {
    throw const SocketException('Network unreachable');
  }

  @override
  Future<List<LineMovement>> getLineMovements() async {
    throw const SocketException('Network unreachable');
  }

  @override
  Future<Bankroll> getBankroll() async {
    throw const SocketException('Network unreachable');
  }
}

/// A subclass of ApiService that returns a successful response.
class SuccessApiService extends ApiService {
  final List<ValuePlay> plays;

  SuccessApiService({required this.plays});

  @override
  Future<List<ValuePlay>> getValuePlays() async => plays;

  @override
  Future<List<ValuePlayV1>> getValuePlaysV1({
    double? minAlpha,
    String? sport,
    int limit = 50,
    String? token,
  }) async =>
      [];

  @override
  Future<List<ArbitrageOpportunity>> getArbitrageOpportunities() async => [];

  @override
  Future<List<LineMovement>> getLineMovements() async => [];

  @override
  Future<Bankroll> getBankroll() async => _emptyBankroll();
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  group('Offline cache — WIRE-04 RED stubs', () {
    setUp(() {
      SharedPreferences.setMockInitialValues({});
    });

    test(
      'test_offline_cache_returns_last_feed_on_network_failure: '
      'AppState returns last cached feed when API throws SocketException',
      () async {
        // RED: AppState has no cache — valuePlays will be empty after network failure.
        // Pre-populate SharedPreferences with a fake cached feed.
        SharedPreferences.setMockInitialValues({
          'cached_value_plays': '[{"id":"cached-1","event":"NFL Game","market":"ML",'
              '"team":"Chiefs","our_odds":0.55,"book_odds":0.50,'
              '"expected_value":0.10,"book":"draftkings",'
              '"timestamp":"2026-03-15T00:00:00.000Z"}]',
        });

        final state = AppState(api: NetworkFailureApiService());
        await state.refresh();

        // RED: expects non-empty from cache — fails because no cache implemented
        expect(
          state.valuePlays,
          isNotEmpty,
          reason: 'AppState should return cached value plays on network failure (WIRE-04)',
        );
        expect(
          state.valuePlays.first.id,
          equals('cached-1'),
          reason: 'Cached play should be returned when API is unreachable',
        );
      },
    );

    test(
      'test_cache_written_after_successful_refresh: '
      "SharedPreferences key 'cached_value_plays' is populated after successful refresh",
      () async {
        // RED: AppState never writes to SharedPreferences — key will be absent.
        final fakePlay = ValuePlay(
          id: 'play-1',
          event: 'NBA Game',
          market: 'ML',
          team: 'Lakers',
          ourOdds: 0.60,
          bookOdds: 0.55,
          expectedValue: 0.09,
          book: 'fanduel',
          timestamp: DateTime.parse('2026-03-15T00:00:00Z'),
        );

        final state = AppState(api: SuccessApiService(plays: [fakePlay]));
        await state.refresh();

        final prefs = await SharedPreferences.getInstance();
        final cachedJson = prefs.getString('cached_value_plays');

        // RED: cache not written — this assertion fails
        expect(
          cachedJson,
          isNotNull,
          reason: "AppState.refresh() must write 'cached_value_plays' to SharedPreferences (WIRE-04)",
        );
        expect(
          cachedJson,
          contains('play-1'),
          reason: 'Cached JSON must include the play ID',
        );
      },
    );
  });
}
