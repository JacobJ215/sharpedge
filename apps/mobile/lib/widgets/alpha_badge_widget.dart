import 'package:flutter/material.dart';

class AlphaBadgeWidget extends StatelessWidget {
  final String badge; // PREMIUM | HIGH | MEDIUM | SPECULATIVE
  const AlphaBadgeWidget({super.key, required this.badge});

  Color get _color => switch (badge) {
    'PREMIUM' => const Color(0xFF10B981), // emerald-500
    'HIGH'    => const Color(0xFF3B82F6), // blue-500
    'MEDIUM'  => const Color(0xFFF59E0B), // amber-500
    _         => const Color(0xFF71717A), // zinc-500
  };

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
      decoration: BoxDecoration(
        color: _color.withValues(alpha: 0.15),
        borderRadius: BorderRadius.circular(4),
        border: Border.all(color: _color.withValues(alpha: 0.4)),
      ),
      child: Text(badge,
        style: TextStyle(color: _color, fontSize: 10,
            fontWeight: FontWeight.w600)),
    );
  }
}
