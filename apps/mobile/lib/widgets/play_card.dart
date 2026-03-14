import 'package:flutter/material.dart';

class PlayCard extends StatelessWidget {
  final String title;
  final String subtitle;
  final Widget trailing;
  final Color? accentColor;
  final VoidCallback? onTap;

  const PlayCard({
    super.key,
    required this.title,
    required this.subtitle,
    required this.trailing,
    this.accentColor,
    this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final color = accentColor ?? Theme.of(context).colorScheme.primary;
    return Column(
      children: [
        Material(
          color: Colors.transparent,
          child: InkWell(
            onTap: onTap,
            splashColor: Colors.white.withValues(alpha: 0.03),
            highlightColor: Colors.white.withValues(alpha: 0.02),
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
              child: Row(
                children: [
                  // Left accent bar
                  Container(
                    width: 2,
                    height: 36,
                    decoration: BoxDecoration(
                      color: color.withValues(alpha: 0.65),
                      borderRadius: BorderRadius.circular(1),
                    ),
                  ),
                  const SizedBox(width: 14),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          title,
                          style: const TextStyle(
                            fontWeight: FontWeight.w500,
                            fontSize: 13,
                            letterSpacing: -0.1,
                            color: Colors.white,
                          ),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                        const SizedBox(height: 3),
                        Text(
                          subtitle,
                          style: const TextStyle(
                            color: Color(0xFF555555),
                            fontSize: 11,
                            fontWeight: FontWeight.w400,
                          ),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(width: 12),
                  trailing,
                ],
              ),
            ),
          ),
        ),
        Container(
          height: 0.5,
          color: Colors.white.withValues(alpha: 0.07),
          margin: const EdgeInsets.only(left: 32),
        ),
      ],
    );
  }
}
