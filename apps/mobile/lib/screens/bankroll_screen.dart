import 'package:flutter/material.dart';
import '../services/api_service.dart';

const _kTeal   = Color(0xFF10B981);
const _kAmber  = Color(0xFFF59E0B);
const _kRed    = Color(0xFFEF4444);
const _kBlue   = Color(0xFF3B82F6);
const _kBg     = Color(0xFF0A0A0A);
const _kCard   = Color(0xFF141414);
const _kBorder = Color(0xFF1F1F1F);

final _apiService = ApiService();

class BankrollScreen extends StatefulWidget {
  const BankrollScreen({super.key});

  @override
  State<BankrollScreen> createState() => _BankrollScreenState();
}

class _BankrollScreenState extends State<BankrollScreen> {
  // Kelly inputs
  final _kellyBankrollCtrl = TextEditingController(text: '1000');
  final _kellyWinProbCtrl  = TextEditingController(text: '0.55');
  final _kellyDecimalCtrl  = TextEditingController(text: '1.91');
  _KellyResult? _kellyResult;

  // Monte Carlo inputs
  final _mcBankrollCtrl = TextEditingController(text: '1000');
  final _mcBetSizeCtrl  = TextEditingController(text: '20');
  final _mcNumBetsCtrl  = TextEditingController(text: '100');
  final _mcWinRateCtrl  = TextEditingController(text: '0.55');
  Map<String, dynamic>? _mcResult;
  bool _mcLoading = false;
  String? _mcError;

  @override
  void dispose() {
    _kellyBankrollCtrl.dispose();
    _kellyWinProbCtrl.dispose();
    _kellyDecimalCtrl.dispose();
    _mcBankrollCtrl.dispose();
    _mcBetSizeCtrl.dispose();
    _mcNumBetsCtrl.dispose();
    _mcWinRateCtrl.dispose();
    super.dispose();
  }

  void _calcKelly() {
    final bankroll    = double.tryParse(_kellyBankrollCtrl.text) ?? 0;
    final winProb     = double.tryParse(_kellyWinProbCtrl.text) ?? 0;
    final decimalOdds = double.tryParse(_kellyDecimalCtrl.text) ?? 0;
    if (bankroll <= 0 || winProb <= 0 || winProb >= 1 || decimalOdds <= 1) {
      setState(() { _kellyResult = null; });
      return;
    }
    final b = decimalOdds - 1;
    final q = 1 - winProb;
    final fraction = ((winProb * b) - q) / b;
    setState(() {
      _kellyResult = _KellyResult(
        fraction: fraction,
        fullKelly: fraction * bankroll,
        halfKelly: fraction * bankroll * 0.5,
        quarterKelly: fraction * bankroll * 0.25,
      );
    });
  }

  Future<void> _runSimulation() async {
    final bankroll = double.tryParse(_mcBankrollCtrl.text) ?? 1000;
    final betSize  = double.tryParse(_mcBetSizeCtrl.text) ?? 20;
    final numBets  = int.tryParse(_mcNumBetsCtrl.text) ?? 100;
    final winRate  = double.tryParse(_mcWinRateCtrl.text) ?? 0.55;
    setState(() { _mcLoading = true; _mcError = null; });
    try {
      final result = await _apiService.simulateBankroll(
        bankroll: bankroll,
        betSize: betSize,
        numBets: numBets,
        winRate: winRate,
      );
      setState(() { _mcResult = result; });
    } catch (e) {
      setState(() { _mcError = e.toString(); });
    } finally {
      setState(() { _mcLoading = false; });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: _kBg,
      appBar: AppBar(
        backgroundColor: _kBg,
        toolbarHeight: 56,
        title: const Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Bankroll',
              style: TextStyle(
                fontSize: 17,
                fontWeight: FontWeight.w700,
                letterSpacing: -0.5,
              ),
            ),
            Text(
              'Kelly sizing & simulation',
              style: TextStyle(
                fontSize: 11,
                color: Color(0xFF6B7280),
                letterSpacing: 0.1,
                fontWeight: FontWeight.w500,
              ),
            ),
          ],
        ),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _buildKellySection(),
            const SizedBox(height: 20),
            _buildMonteCarloSection(),
            const SizedBox(height: 20),
            _buildExposureReminder(),
            const SizedBox(height: 32),
          ],
        ),
      ),
    );
  }

  // ── Kelly Calculator ────────────────────────────────────────────────────────

  Widget _buildKellySection() {
    return _Card(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const _SectionHeader(label: 'KELLY CALCULATOR'),
          const SizedBox(height: 14),
          _Input(label: 'Bankroll (\$)', ctrl: _kellyBankrollCtrl, hint: '1000'),
          const SizedBox(height: 10),
          _Input(label: 'Win Probability (0–1)', ctrl: _kellyWinProbCtrl, hint: '0.55'),
          const SizedBox(height: 10),
          _Input(label: 'Decimal Odds', ctrl: _kellyDecimalCtrl, hint: '1.91'),
          const SizedBox(height: 14),
          _ActionButton(label: 'Calculate', onTap: _calcKelly),
          if (_kellyResult != null) ...[
            const SizedBox(height: 14),
            _buildKellyResult(_kellyResult!),
          ],
        ],
      ),
    );
  }

  Widget _buildKellyResult(_KellyResult r) {
    final isEdge     = r.fraction > 0;
    final fColor     = isEdge ? _kTeal : _kRed;
    return Padding(
      padding: const EdgeInsets.only(top: 14),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Text(
                '${(r.fraction * 100).toStringAsFixed(2)}%',
                style: TextStyle(
                  fontSize: 28,
                  fontWeight: FontWeight.w700,
                  color: fColor,
                  letterSpacing: -1,
                ),
              ),
              const SizedBox(width: 8),
              const Padding(
                padding: EdgeInsets.only(bottom: 4),
                child: Text(
                  'Kelly fraction',
                  style: TextStyle(color: Color(0xFF6B7280), fontSize: 12),
                ),
              ),
            ],
          ),
          if (isEdge) ...[
            const SizedBox(height: 12),
            Row(
              children: [
                _KellyBadge(label: 'Full Kelly', value: '\$${r.fullKelly.toStringAsFixed(2)}', color: _kAmber),
                const SizedBox(width: 8),
                _KellyBadge(label: '½ Kelly', value: '\$${r.halfKelly.toStringAsFixed(2)}', color: _kTeal),
                const SizedBox(width: 8),
                _KellyBadge(label: '¼ Kelly', value: '\$${r.quarterKelly.toStringAsFixed(2)}', color: _kBlue),
              ],
            ),
          ] else
            const Padding(
              padding: EdgeInsets.only(top: 4),
              child: Text(
                'No edge — do not bet.',
                style: TextStyle(color: Color(0xFF9CA3AF), fontSize: 12),
              ),
            ),
        ],
      ),
    );
  }

  // ── Monte Carlo Simulation ──────────────────────────────────────────────────

  Widget _buildMonteCarloSection() {
    return _Card(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const _SectionHeader(label: 'MONTE CARLO SIMULATION'),
          const SizedBox(height: 14),
          Row(
            children: [
              Expanded(child: _Input(label: 'Bankroll (\$)', ctrl: _mcBankrollCtrl, hint: '1000')),
              const SizedBox(width: 10),
              Expanded(child: _Input(label: 'Bet Size (\$)', ctrl: _mcBetSizeCtrl, hint: '20')),
            ],
          ),
          const SizedBox(height: 10),
          Row(
            children: [
              Expanded(child: _Input(label: 'Number of Bets', ctrl: _mcNumBetsCtrl, hint: '100', isInt: true)),
              const SizedBox(width: 10),
              Expanded(child: _Input(label: 'Win Rate (0–1)', ctrl: _mcWinRateCtrl, hint: '0.55')),
            ],
          ),
          const SizedBox(height: 14),
          _ActionButton(
            label: _mcLoading ? 'Simulating…' : 'Run Simulation',
            onTap: _mcLoading ? null : _runSimulation,
          ),
          if (_mcError != null) ...[
            const SizedBox(height: 10),
            Text(_mcError!, style: const TextStyle(color: _kRed, fontSize: 12)),
          ],
          if (_mcResult != null) ...[
            const SizedBox(height: 14),
            _buildMcResult(_mcResult!),
          ],
        ],
      ),
    );
  }

  Widget _buildMcResult(Map<String, dynamic> r) {
    final ruinProb    = (r['ruin_probability'] as num?)?.toDouble() ?? 0.0;
    final p5          = (r['p5_final'] as num?)?.toDouble();
    final p50         = (r['p50_final'] as num?)?.toDouble();
    final p95         = (r['p95_final'] as num?)?.toDouble();
    final maxDrawdown = (r['max_drawdown_pct'] as num?)?.toDouble();
    final ruinColor   = ruinProb > 0.2 ? _kRed : (ruinProb > 0.1 ? _kAmber : _kTeal);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'RUIN PROBABILITY',
              style: TextStyle(
                color: Color(0xFF6B7280),
                fontSize: 10,
                fontWeight: FontWeight.w600,
                letterSpacing: 1.2,
              ),
            ),
            const SizedBox(height: 4),
            Text(
              '${(ruinProb * 100).toStringAsFixed(1)}%',
              style: TextStyle(
                fontSize: 32,
                fontWeight: FontWeight.w700,
                color: ruinColor,
                letterSpacing: -1,
              ),
            ),
          ],
        ),
        if (p5 != null && p50 != null && p95 != null) ...[
          const SizedBox(height: 10),
          Row(
            children: [
              Expanded(child: _StatTile(label: 'P5 (worst)', value: '\$${p5.toStringAsFixed(0)}', color: _kRed)),
              const SizedBox(width: 8),
              Expanded(child: _StatTile(label: 'P50 (median)', value: '\$${p50.toStringAsFixed(0)}', color: _kTeal)),
              const SizedBox(width: 8),
              Expanded(child: _StatTile(label: 'P95 (best)', value: '\$${p95.toStringAsFixed(0)}', color: _kBlue)),
            ],
          ),
        ],
        if (maxDrawdown != null) ...[
          const SizedBox(height: 8),
          _StatTile(
            label: 'Max Drawdown',
            value: '-${maxDrawdown.toStringAsFixed(1)}%',
            color: _kAmber,
          ),
        ],
      ],
    );
  }

  // ── Exposure Limits reminder ────────────────────────────────────────────────

  Widget _buildExposureReminder() {
    return const Padding(
      padding: EdgeInsets.only(top: 8),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.warning_amber_rounded, color: _kAmber, size: 14),
              SizedBox(width: 6),
              Text(
                'Exposure Limits',
                style: TextStyle(
                  color: _kAmber,
                  fontSize: 13,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ],
          ),
          SizedBox(height: 8),
          Text(
            'Never bet more than 2% Kelly per wager. Full Kelly is theoretically optimal but produces variance that exceeds most bettors\' risk tolerance. Half or quarter Kelly is recommended for sustained compounding.',
            style: TextStyle(
              color: Color(0xFF9CA3AF),
              fontSize: 12,
              height: 1.5,
            ),
          ),
        ],
      ),
    );
  }
}

// ── Data classes ──────────────────────────────────────────────────────────────

class _KellyResult {
  final double fraction;
  final double fullKelly;
  final double halfKelly;
  final double quarterKelly;
  const _KellyResult({
    required this.fraction,
    required this.fullKelly,
    required this.halfKelly,
    required this.quarterKelly,
  });
}

// ── Shared UI components ──────────────────────────────────────────────────────

class _Card extends StatelessWidget {
  final Widget child;
  const _Card({required this.child});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: child,
    );
  }
}

class _SectionHeader extends StatelessWidget {
  final String label;
  const _SectionHeader({required this.label});

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Container(
          width: 2,
          height: 14,
          decoration: BoxDecoration(
            color: _kTeal,
            borderRadius: BorderRadius.circular(1),
          ),
        ),
        const SizedBox(width: 8),
        Text(
          label,
          style: const TextStyle(
            fontSize: 10,
            fontWeight: FontWeight.w700,
            color: Color(0xFF6B7280),
            letterSpacing: 1.4,
          ),
        ),
      ],
    );
  }
}

class _Input extends StatelessWidget {
  final String label;
  final TextEditingController ctrl;
  final String hint;
  final bool isInt;

  const _Input({
    required this.label,
    required this.ctrl,
    required this.hint,
    this.isInt = false,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: const TextStyle(
            color: Color(0xFF6B7280),
            fontSize: 11,
            fontWeight: FontWeight.w500,
          ),
        ),
        const SizedBox(height: 5),
        TextField(
          controller: ctrl,
          keyboardType: isInt
              ? TextInputType.number
              : const TextInputType.numberWithOptions(decimal: true),
          style: const TextStyle(
            color: Colors.white,
            fontSize: 14,
            fontFamily: 'monospace',
          ),
          decoration: InputDecoration(
            hintText: hint,
            hintStyle: const TextStyle(color: Color(0xFF52525B), fontSize: 13),
            filled: true,
            fillColor: const Color(0xFF18181B),
            contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
            border: OutlineInputBorder(
              borderRadius: BorderRadius.circular(6),
              borderSide: const BorderSide(color: Color(0xFF3F3F46), width: 1),
            ),
            enabledBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(6),
              borderSide: const BorderSide(color: Color(0xFF3F3F46), width: 1),
            ),
            focusedBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(6),
              borderSide: const BorderSide(color: Color(0xFF71717A), width: 1),
            ),
          ),
        ),
      ],
    );
  }
}

class _ActionButton extends StatelessWidget {
  final String label;
  final VoidCallback? onTap;
  const _ActionButton({required this.label, this.onTap});

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: double.infinity,
      child: TextButton(
        onPressed: onTap,
        style: TextButton.styleFrom(
          backgroundColor: onTap != null ? _kTeal : _kTeal.withValues(alpha: 0.4),
          padding: const EdgeInsets.symmetric(vertical: 12),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
        ),
        child: Text(
          label,
          style: const TextStyle(
            color: Colors.white,
            fontSize: 14,
            fontWeight: FontWeight.w600,
          ),
        ),
      ),
    );
  }
}

class _KellyBadge extends StatelessWidget {
  final String label;
  final String value;
  final Color color;
  const _KellyBadge({required this.label, required this.value, required this.color});

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            label,
            style: TextStyle(
              color: color.withValues(alpha: 0.6),
              fontSize: 9,
              fontWeight: FontWeight.w600,
              letterSpacing: 0.5,
            ),
          ),
          const SizedBox(height: 2),
          Text(
            value,
            style: TextStyle(
              color: color,
              fontSize: 13,
              fontWeight: FontWeight.w700,
              letterSpacing: -0.3,
            ),
          ),
        ],
      ),
    );
  }
}

class _StatTile extends StatelessWidget {
  final String label;
  final String value;
  final Color color;
  const _StatTile({required this.label, required this.value, required this.color});

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: const TextStyle(
            color: Color(0xFF6B7280),
            fontSize: 9,
            fontWeight: FontWeight.w600,
            letterSpacing: 0.8,
          ),
        ),
        const SizedBox(height: 3),
        Text(
          value,
          style: TextStyle(
            color: color,
            fontSize: 15,
            fontWeight: FontWeight.w700,
            letterSpacing: -0.4,
          ),
        ),
      ],
    );
  }
}
