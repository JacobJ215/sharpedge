import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

const _kCard = Color(0xFF141414);
const _kTeal = Color(0xFF10B981);

// ── Data model ────────────────────────────────────────────────────────────────

class CopilotMessage {
  final String role;
  final String content;
  final DateTime timestamp;
  /// Tool trace lines for the latest assistant turn (Phase 4 SSE `event: copilot_tool`).
  final List<String> toolTraces;
  const CopilotMessage({
    required this.role,
    required this.content,
    required this.timestamp,
    this.toolTraces = const [],
  });

  CopilotMessage copyWith({String? content, List<String>? toolTraces}) => CopilotMessage(
        role: role,
        content: content ?? this.content,
        timestamp: timestamp,
        toolTraces: toolTraces ?? this.toolTraces,
      );
}

// ── Markdown-like text renderer ───────────────────────────────────────────────

/// Supports **bold**, `inline code`, and - / 1. list items.
class MarkdownText extends StatelessWidget {
  final String text;
  final double fontSize;
  final Color baseColor;
  const MarkdownText({
    super.key, required this.text,
    this.fontSize = 15, this.baseColor = Colors.white,
  });

  @override
  Widget build(BuildContext context) {
    final lines = text.split('\n');
    final children = <Widget>[];
    for (var i = 0; i < lines.length; i++) {
      final line = lines[i];
      final trimmed = line.trimLeft();
      final isBullet = trimmed.startsWith('- ') || trimmed.startsWith('* ');
      final numMatch = RegExp(r'^\d+\. ').firstMatch(trimmed);
      if (isBullet) {
        children.add(_listItem(trimmed.substring(2), '\u2022'));
      } else if (numMatch != null) {
        children.add(_listItem(trimmed.substring(numMatch.group(0)!.length),
            numMatch.group(0)!.trimRight()));
      } else {
        children.add(Text.rich(_parseInline(line),
          style: _baseStyle()));
      }
      if (i < lines.length - 1) children.add(SizedBox(height: line.trim().isEmpty ? 6 : 2));
    }
    return Column(crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min, children: children);
  }

  TextStyle _baseStyle() => TextStyle(
    color: baseColor.withValues(alpha: 0.9), fontSize: fontSize,
    height: 1.65, fontWeight: FontWeight.w400);

  Widget _listItem(String content, String bullet) => Padding(
    padding: const EdgeInsets.only(left: 8, top: 1, bottom: 1),
    child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Text('$bullet  ', style: TextStyle(color: _kTeal, fontSize: fontSize, height: 1.65, fontWeight: FontWeight.w500)),
      Expanded(child: Text.rich(_parseInline(content), style: _baseStyle())),
    ]),
  );

  TextSpan _parseInline(String line) {
    final spans = <InlineSpan>[];
    final pattern = RegExp(r'\*\*(.+?)\*\*|`([^`]+)`');
    int last = 0;
    for (final m in pattern.allMatches(line)) {
      if (m.start > last) spans.add(TextSpan(text: line.substring(last, m.start)));
      if (m.group(1) != null) {
        spans.add(TextSpan(text: m.group(1),
            style: const TextStyle(fontWeight: FontWeight.bold)));
      } else if (m.group(2) != null) {
        spans.add(WidgetSpan(
          alignment: PlaceholderAlignment.middle,
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 1),
            margin: const EdgeInsets.symmetric(horizontal: 1),
            decoration: BoxDecoration(
              color: Colors.white.withValues(alpha: 0.07),
              borderRadius: BorderRadius.circular(4),
              border: Border.all(color: Colors.white.withValues(alpha: 0.1), width: 0.5),
            ),
            child: Text(m.group(2)!,
              style: TextStyle(fontFamily: 'monospace', fontSize: fontSize - 1,
                  color: const Color(0xFF7DD3FC), height: 1.4)),
          ),
        ));
      }
      last = m.end;
    }
    if (last < line.length) spans.add(TextSpan(text: line.substring(last)));
    return TextSpan(style: _baseStyle(), children: spans);
  }
}

// ── Copilot tool trace (SSE event: copilot_tool) ──────────────────────────────

class _CopilotToolTracesList extends StatelessWidget {
  final List<String> lines;
  const _CopilotToolTracesList({required this.lines});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(top: 8),
      child: Container(
        constraints: const BoxConstraints(maxHeight: 96),
        decoration: BoxDecoration(
          color: Colors.white.withValues(alpha: 0.04),
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: Colors.white.withValues(alpha: 0.06)),
        ),
        child: ListView.separated(
          shrinkWrap: true,
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
          physics: lines.length > 4 ? const BouncingScrollPhysics() : const NeverScrollableScrollPhysics(),
          itemCount: lines.length,
          separatorBuilder: (_, __) => const SizedBox(height: 2),
          itemBuilder: (_, i) => Text(
            lines[i],
            style: TextStyle(
              fontSize: 11,
              height: 1.35,
              color: Colors.grey[500],
              fontFamily: 'monospace',
            ),
          ),
        ),
      ),
    );
  }
}

// ── User message bubble ───────────────────────────────────────────────────────

class UserMessageBubble extends StatelessWidget {
  final CopilotMessage message;
  const UserMessageBubble({super.key, required this.message});

  void _showTimestamp(BuildContext context) {
    final overlay = Overlay.of(context);
    late OverlayEntry entry;
    entry = OverlayEntry(builder: (_) => _TimestampToast(
      text: _formatTimestamp(message.timestamp), onDismiss: () => entry.remove()));
    overlay.insert(entry);
  }

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onLongPress: () => _showTimestamp(context),
      child: Padding(
        padding: const EdgeInsets.fromLTRB(64, 4, 16, 12),
        child: Align(
          alignment: Alignment.centerRight,
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
            decoration: BoxDecoration(
              color: const Color(0xFF1E1E1E),
              borderRadius: BorderRadius.circular(14),
              border: Border.all(color: Colors.white.withValues(alpha: 0.07), width: 0.5),
            ),
            child: Text(message.content,
              style: const TextStyle(color: Colors.white, fontSize: 14, height: 1.5)),
          ),
        ),
      ),
    );
  }
}

// ── Assistant message bubble ──────────────────────────────────────────────────

class AssistantMessageBubble extends StatefulWidget {
  final CopilotMessage message;
  final bool streaming;
  const AssistantMessageBubble({super.key, required this.message, required this.streaming});

  @override
  State<AssistantMessageBubble> createState() => _AssistantMessageBubbleState();
}

class _AssistantMessageBubbleState extends State<AssistantMessageBubble> {
  bool _copied = false;

  void _copy() {
    Clipboard.setData(ClipboardData(text: widget.message.content));
    setState(() => _copied = true);
    Future.delayed(const Duration(seconds: 2), () {
      if (mounted) setState(() => _copied = false);
    });
  }

  void _showCopyMenu(BuildContext context) {
    showModalBottomSheet<void>(
      context: context,
      backgroundColor: const Color(0xFF1A1A1A),
      shape: const RoundedRectangleBorder(
          borderRadius: BorderRadius.vertical(top: Radius.circular(16))),
      builder: (_) => SafeArea(
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          Container(
            width: 36, height: 4,
            margin: const EdgeInsets.symmetric(vertical: 10),
            decoration: BoxDecoration(
              color: Colors.white.withValues(alpha: 0.15),
              borderRadius: BorderRadius.circular(2)),
          ),
          ListTile(
            leading: const Icon(Icons.copy_rounded, color: _kTeal, size: 20),
            title: const Text('Copy response',
                style: TextStyle(color: Colors.white, fontSize: 14)),
            onTap: () { Navigator.pop(context); _copy(); },
          ),
          ListTile(
            leading: const Icon(Icons.access_time_rounded,
                color: Color(0xFF9CA3AF), size: 20),
            title: Text(_formatTimestamp(widget.message.timestamp),
                style: const TextStyle(color: Color(0xFF9CA3AF), fontSize: 14)),
            onTap: () => Navigator.pop(context),
          ),
          const SizedBox(height: 8),
        ]),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onLongPress: () => _showCopyMenu(context),
      child: Padding(
        padding: const EdgeInsets.fromLTRB(16, 4, 16, 16),
        child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Padding(
            padding: const EdgeInsets.only(top: 6, right: 12),
            child: Container(
              width: 6, height: 6,
              decoration: BoxDecoration(
                color: _kTeal, shape: BoxShape.circle,
                boxShadow: [BoxShadow(color: _kTeal.withValues(alpha: 0.5),
                    blurRadius: 6, spreadRadius: 1)],
              ),
            ),
          ),
          Expanded(
            child: widget.message.content.isEmpty && widget.streaming
                ? const Padding(padding: EdgeInsets.only(top: 2), child: LoadingDots())
                : Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    MarkdownText(text: widget.message.content,
                        fontSize: 15, baseColor: Colors.white),
                    if (widget.message.toolTraces.isNotEmpty)
                      _CopilotToolTracesList(lines: widget.message.toolTraces),
                    if (!widget.streaming && widget.message.content.isNotEmpty)
                      Padding(
                        padding: const EdgeInsets.only(top: 6),
                        child: GestureDetector(
                          onTap: _copy,
                          child: AnimatedSwitcher(
                            duration: const Duration(milliseconds: 200),
                            child: _copied
                                ? const Icon(Icons.check_rounded,
                                    key: ValueKey('check'), size: 14, color: _kTeal)
                                : Icon(Icons.copy_rounded,
                                    key: const ValueKey('copy'), size: 14,
                                    color: Colors.white.withValues(alpha: 0.25)),
                          ),
                        ),
                      ),
                  ]),
          ),
        ]),
      ),
    );
  }
}

// ── Suggestion chip (horizontal, matches web layout) ─────────────────────────

class SuggestionCard extends StatefulWidget {
  final String label;
  final IconData icon;
  final VoidCallback onTap;
  const SuggestionCard({super.key, required this.label, required this.icon, required this.onTap});

  @override
  State<SuggestionCard> createState() => _SuggestionCardState();
}

class _SuggestionCardState extends State<SuggestionCard>
    with SingleTickerProviderStateMixin {
  late final AnimationController _ctrl = AnimationController(
    vsync: this, duration: const Duration(milliseconds: 100));
  late final Animation<double> _scale = Tween<double>(begin: 1.0, end: 0.97)
      .animate(CurvedAnimation(parent: _ctrl, curve: Curves.easeOut));
  bool _hovered = false;

  @override
  void dispose() { _ctrl.dispose(); super.dispose(); }

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTapDown: (_) { _ctrl.forward(); setState(() => _hovered = true); },
      onTapUp: (_) { _ctrl.reverse(); setState(() => _hovered = false); widget.onTap(); },
      onTapCancel: () { _ctrl.reverse(); setState(() => _hovered = false); },
      child: AnimatedBuilder(
        animation: _scale,
        builder: (_, child) => Transform.scale(scale: _scale.value, child: child),
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 150),
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
          decoration: BoxDecoration(
            color: _kCard,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(
              color: _hovered
                  ? _kTeal.withValues(alpha: 0.2)
                  : Colors.white.withValues(alpha: 0.08),
              width: 0.5,
            ),
          ),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              Icon(widget.icon, color: _kTeal, size: 14),
              const SizedBox(width: 10),
              Expanded(
                child: Text(
                  widget.label,
                  style: TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.w500,
                    color: _hovered ? Colors.white : const Color(0xFFD1D5DB),
                    height: 1.35,
                  ),
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

// ── Loading dots ──────────────────────────────────────────────────────────────

class LoadingDots extends StatefulWidget {
  const LoadingDots({super.key});
  @override
  State<LoadingDots> createState() => _LoadingDotsState();
}

class _LoadingDotsState extends State<LoadingDots> with SingleTickerProviderStateMixin {
  late final AnimationController _ctrl = AnimationController(
    vsync: this, duration: const Duration(milliseconds: 1200))..repeat();

  @override
  void dispose() { _ctrl.dispose(); super.dispose(); }

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 18,
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: List.generate(3, (i) => AnimatedBuilder(
          animation: _ctrl,
          builder: (_, __) {
            final phase = (_ctrl.value - i * 0.18).clamp(0.0, 1.0);
            final opacity = math.sin(phase * math.pi).clamp(0.15, 1.0);
            return Container(
              width: 5, height: 5,
              margin: const EdgeInsets.symmetric(horizontal: 2),
              decoration: BoxDecoration(
                color: _kTeal.withValues(alpha: opacity),
                shape: BoxShape.circle),
            );
          },
        )),
      ),
    );
  }
}

// ── Timestamp toast overlay ───────────────────────────────────────────────────

class _TimestampToast extends StatefulWidget {
  final String text;
  final VoidCallback onDismiss;
  const _TimestampToast({required this.text, required this.onDismiss});
  @override
  State<_TimestampToast> createState() => _TimestampToastState();
}

class _TimestampToastState extends State<_TimestampToast>
    with SingleTickerProviderStateMixin {
  late final AnimationController _ctrl = AnimationController(
    vsync: this, duration: const Duration(milliseconds: 200))..forward();
  late final Animation<double> _opacity =
      CurvedAnimation(parent: _ctrl, curve: Curves.easeOut);

  @override
  void initState() {
    super.initState();
    Future.delayed(const Duration(seconds: 2), _dismiss);
  }

  Future<void> _dismiss() async {
    if (mounted) { await _ctrl.reverse(); widget.onDismiss(); }
  }

  @override
  void dispose() { _ctrl.dispose(); super.dispose(); }

  @override
  Widget build(BuildContext context) {
    return Positioned(
      bottom: 120, left: 0, right: 0,
      child: IgnorePointer(
        child: FadeTransition(
          opacity: _opacity,
          child: Center(
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 7),
              decoration: BoxDecoration(
                color: const Color(0xFF2A2A2A),
                borderRadius: BorderRadius.circular(20),
                border: Border.all(color: Colors.white.withValues(alpha: 0.1), width: 0.5),
              ),
              child: Text(widget.text,
                  style: const TextStyle(color: Color(0xFF9CA3AF), fontSize: 12)),
            ),
          ),
        ),
      ),
    );
  }
}

// ── Helpers ───────────────────────────────────────────────────────────────────

String _formatTimestamp(DateTime dt) {
  final diff = DateTime.now().difference(dt);
  if (diff.inSeconds < 60) return 'Just now';
  if (diff.inMinutes < 60) return '${diff.inMinutes}m ago';
  final h = dt.hour.toString().padLeft(2, '0');
  final m = dt.minute.toString().padLeft(2, '0');
  return diff.inHours < 24 ? 'Today at $h:$m' : '${dt.month}/${dt.day} at $h:$m';
}
