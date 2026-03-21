import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

/// Reusable upgrade prompt widget shown when a free-tier user
/// attempts to access a pro/sharp-gated screen.
class UpgradePromptWidget extends StatelessWidget {
  final String requiredTier;
  final String? message;

  const UpgradePromptWidget({
    super.key,
    this.requiredTier = 'pro',
    this.message,
  });

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(
              Icons.lock_outline,
              color: Color(0xFF10B981),
              size: 48,
            ),
            const SizedBox(height: 16),
            Text(
              message ?? 'This feature requires a ${requiredTier.toUpperCase()} subscription',
              textAlign: TextAlign.center,
              style: const TextStyle(
                color: Color(0xFFA1A1AA),
                fontSize: 14,
              ),
            ),
            const SizedBox(height: 8),
            const Text(
              'Upgrade on the web to unlock full access.',
              textAlign: TextAlign.center,
              style: TextStyle(
                color: Color(0xFF71717A),
                fontSize: 12,
              ),
            ),
            const SizedBox(height: 24),
            ElevatedButton(
              onPressed: () async {
                final uri = Uri.parse('https://whop.com/sharpedge/');
                if (await canLaunchUrl(uri)) {
                  await launchUrl(uri, mode: LaunchMode.externalApplication);
                }
              },
              style: ElevatedButton.styleFrom(
                backgroundColor: const Color(0xFF10B981),
                foregroundColor: Colors.white,
                padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 12),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(8),
                ),
              ),
              child: const Text(
                'Upgrade on Whop',
                style: TextStyle(fontWeight: FontWeight.w600),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
