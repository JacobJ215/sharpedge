import 'package:flutter/material.dart';
import '../models/value_play.dart';

class LogBetSheet extends StatefulWidget {
  final ValuePlayV1 play;
  const LogBetSheet({super.key, required this.play});
  @override
  State<LogBetSheet> createState() => _LogBetSheetState();
}

class _LogBetSheetState extends State<LogBetSheet> {
  late TextEditingController _stakeCtrl;
  late TextEditingController _bookCtrl;

  @override
  void initState() {
    super.initState();
    // Pre-fill: Kelly suggestion = alphaScore * 2% of assumed $1000 bankroll
    // (simplified — actual bankroll from portfolio; use alpha as proxy here)
    final kellySuggestion = (widget.play.alphaScore * 20).toStringAsFixed(0);
    _stakeCtrl = TextEditingController(text: kellySuggestion);
    _bookCtrl = TextEditingController(text: widget.play.book);
  }

  @override
  void dispose() {
    _stakeCtrl.dispose(); _bookCtrl.dispose(); super.dispose();
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
            onPressed: () {
              // TODO: POST bet to API in full implementation
              Navigator.of(context).pop({
                'stake': double.tryParse(_stakeCtrl.text) ?? 0,
                'book': _bookCtrl.text,
              });
            },
            child: const Text('Confirm'),
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
