import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../models/value_play.dart';
import '../providers/app_state.dart';
import '../services/api_service.dart';

final _apiService = ApiService();

class LogBetSheet extends StatefulWidget {
  final ValuePlayV1 play;
  const LogBetSheet({super.key, required this.play});
  @override
  State<LogBetSheet> createState() => _LogBetSheetState();
}

class _LogBetSheetState extends State<LogBetSheet> {
  late TextEditingController _stakeCtrl;
  late TextEditingController _bookCtrl;
  bool _isLoading = false;

  @override
  void initState() {
    super.initState();
    // Pre-fill: Kelly suggestion = alphaScore * 2% of assumed $1000 bankroll
    final kellySuggestion = (widget.play.alphaScore * 20).toStringAsFixed(0);
    _stakeCtrl = TextEditingController(text: kellySuggestion);
    _bookCtrl = TextEditingController(text: widget.play.book);
  }

  @override
  void dispose() {
    _stakeCtrl.dispose(); _bookCtrl.dispose(); super.dispose();
  }

  Future<void> _confirmBet() async {
    final stake = double.tryParse(_stakeCtrl.text) ?? 0;
    final book = _bookCtrl.text;

    if (stake <= 0) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Enter a valid stake amount')),
      );
      return;
    }

    final appState = context.read<AppState>();
    final token = appState.authToken ?? '';

    setState(() => _isLoading = true);
    try {
      await _apiService.logBet(
        playId: widget.play.id,
        event: widget.play.event,
        market: widget.play.market,
        team: widget.play.team,
        book: book,
        stake: stake,
        token: token,
      );
      if (mounted) {
        Navigator.of(context).pop({'stake': stake, 'book': book});
      }
    } on ApiException catch (e) {
      if (mounted) {
        setState(() => _isLoading = false);
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to log bet: ${e.message}')),
        );
      }
    } catch (_) {
      if (mounted) {
        setState(() => _isLoading = false);
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Failed to log bet — please try again')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.fromLTRB(20, 20, 20,
          20 + MediaQuery.of(context).viewInsets.bottom),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(widget.play.event,
            style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
          Text('${widget.play.market} · ${widget.play.team}',
            style: const TextStyle(color: Colors.grey, fontSize: 13)),
          const SizedBox(height: 16),
          Row(children: [
            Expanded(child: _field('Stake (\$)', _stakeCtrl,
                TextInputType.number)),
            const SizedBox(width: 12),
            Expanded(child: _field('Book', _bookCtrl, TextInputType.text)),
          ]),
          const SizedBox(height: 16),
          ElevatedButton(
            onPressed: _isLoading ? null : _confirmBet,
            child: _isLoading
                ? const SizedBox(
                    height: 18,
                    width: 18,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : const Text('Confirm'),
          ),
        ],
      ),
    );
  }

  Widget _field(String label, TextEditingController ctrl,
      TextInputType type) {
    return TextField(
      controller: ctrl,
      keyboardType: type,
      decoration: InputDecoration(
        labelText: label, border: const OutlineInputBorder()),
    );
  }
}
