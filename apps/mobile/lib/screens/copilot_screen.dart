import 'dart:async';
import 'dart:convert';
import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:http/http.dart' as http;
import 'package:provider/provider.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../providers/app_state.dart';
import '../services/api_service.dart';
import '../widgets/copilot_widgets.dart';

const _kCopilotThreadKey = 'sharpedge_copilot_thread_id';

const _kBg   = Color(0xFF0A0A0A);
const _kCard  = Color(0xFF141414);
const _kTeal  = Color(0xFF10B981);


class CopilotScreen extends StatefulWidget {
  const CopilotScreen({super.key});
  @override
  State<CopilotScreen> createState() => _CopilotScreenState();
}

class _CopilotScreenState extends State<CopilotScreen> {
  final List<CopilotMessage> _messages = [];
  final _inputCtrl  = TextEditingController();
  final _scrollCtrl = ScrollController();
  bool _streaming = false;
  bool _firstTokenFired = false;

  // Cancellation support
  http.Client? _activeClient;

  @override
  void dispose() {
    _inputCtrl.dispose();
    _scrollCtrl.dispose();
    _activeClient?.close();
    super.dispose();
  }

  String _newCopilotThreadId() {
    final r = math.Random.secure();
    final bytes = List<int>.generate(16, (_) => r.nextInt(256));
    bytes[6] = (bytes[6] & 0x0f) | 0x40;
    bytes[8] = (bytes[8] & 0x3f) | 0x80;
    final h = bytes.map((b) => b.toRadixString(16).padLeft(2, '0')).join();
    return '${h.substring(0, 8)}-${h.substring(8, 12)}-${h.substring(12, 16)}-${h.substring(16, 20)}-${h.substring(20)}';
  }

  Future<String> _threadIdForRequest() async {
    final p = await SharedPreferences.getInstance();
    var id = p.getString(_kCopilotThreadKey);
    if (id == null || id.isEmpty) {
      id = _newCopilotThreadId();
      await p.setString(_kCopilotThreadKey, id);
    }
    return id;
  }

  // ── Streaming send ──────────────────────────────────────────────────────────

  Future<void> _send(String text) async {
    if (text.trim().isEmpty || _streaming) return;
    HapticFeedback.mediumImpact();
    _firstTokenFired = false;
    final now = DateTime.now();
    setState(() {
      _messages.add(CopilotMessage(
          role: 'user', content: text.trim(), timestamp: now));
      _messages.add(CopilotMessage(
          role: 'assistant', content: '', timestamp: DateTime.now()));
      _streaming = true;
    });
    _inputCtrl.clear();
    _scrollToBottom();

    final authToken = Provider.of<AppState>(context, listen: false).authToken;
    final threadId = await _threadIdForRequest();

    final uri = Uri.parse('${ApiService.baseUrl}/api/v1/copilot/chat');
    final client = http.Client();
    _activeClient = client;

    final request = http.Request('POST', uri)
      ..headers['Content-Type'] = 'application/json'
      ..body = jsonEncode({'message': text.trim(), 'thread_id': threadId});
    if (authToken != null && authToken.isNotEmpty) {
      request.headers['Authorization'] = 'Bearer $authToken';
    }

    try {
      final streamedResponse = await client.send(request);
      await for (final chunk in streamedResponse.stream
          .transform(utf8.decoder)
          .transform(const LineSplitter())) {
        if (chunk.startsWith('data: ') && chunk != 'data: [DONE]') {
          final token = chunk.substring(6).replaceAll(r'\n', '\n');
          if (!_firstTokenFired) {
            _firstTokenFired = true;
            HapticFeedback.lightImpact();
          }
          setState(() {
            _messages.last = _messages.last.copyWith(
              content: _messages.last.content + token,
            );
          });
          _scrollToBottom();
        }
      }
    } catch (e) {
      // Ignore cancellation errors (client closed intentionally)
      if (_activeClient != null) {
        setState(() {
          _messages.last = _messages.last.copyWith(
            content: 'Error: ${e.toString()}',
          );
        });
      }
    } finally {
      _activeClient = null;
      if (mounted) setState(() => _streaming = false);
    }
  }

  void _stopStreaming() {
    _activeClient?.close();
    _activeClient = null;
    if (mounted) setState(() => _streaming = false);
  }

  // ── New chat ────────────────────────────────────────────────────────────────

  Future<void> _confirmNewChat() async {
    if (_messages.isEmpty) return;
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        backgroundColor: _kCard,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
        title: const Text('New chat',
            style: TextStyle(color: Colors.white, fontSize: 16)),
        content: Text(
          'Clear ${_messages.length ~/ 2 + _messages.length % 2} message(s) and start over?',
          style: TextStyle(color: Colors.grey[400], fontSize: 14),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: Text('Cancel',
                style: TextStyle(color: Colors.grey[500], fontSize: 14)),
          ),
          TextButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Clear',
                style: TextStyle(color: _kTeal, fontSize: 14)),
          ),
        ],
      ),
    );
    if (confirmed == true) {
      final p = await SharedPreferences.getInstance();
      await p.setString(_kCopilotThreadKey, _newCopilotThreadId());
      setState(() => _messages.clear());
    }
  }

  // ── Scroll helpers ──────────────────────────────────────────────────────────

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollCtrl.hasClients) {
        _scrollCtrl.animateTo(
          _scrollCtrl.position.maxScrollExtent,
          duration: const Duration(milliseconds: 180),
          curve: Curves.easeOut,
        );
      }
    });
  }

  // ── Build ───────────────────────────────────────────────────────────────────

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: _kBg,
      appBar: _buildAppBar(),
      body: Column(
        children: [
          Expanded(
            child: Stack(
              children: [
                _messages.isEmpty ? _buildEmptyState() : _buildMessageList(),
                // Gradient fade at top
                Positioned(
                  top: 0,
                  left: 0,
                  right: 0,
                  child: IgnorePointer(
                    child: Container(
                      height: 32,
                      decoration: BoxDecoration(
                        gradient: LinearGradient(
                          begin: Alignment.topCenter,
                          end: Alignment.bottomCenter,
                          colors: [
                            _kBg,
                            _kBg.withValues(alpha: 0.0),
                          ],
                        ),
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ),
          // Stop button while streaming
          if (_streaming)
            Padding(
              padding: const EdgeInsets.fromLTRB(12, 0, 12, 4),
              child: Center(
                child: GestureDetector(
                  onTap: _stopStreaming,
                  child: Container(
                    padding: const EdgeInsets.symmetric(
                        horizontal: 16, vertical: 8),
                    decoration: BoxDecoration(
                      color: _kCard,
                      borderRadius: BorderRadius.circular(20),
                      border: Border.all(
                        color: Colors.white.withValues(alpha: 0.1),
                        width: 0.5,
                      ),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Container(
                          width: 10,
                          height: 10,
                          decoration: BoxDecoration(
                            color: Colors.white.withValues(alpha: 0.75),
                            borderRadius: BorderRadius.circular(2),
                          ),
                        ),
                        const SizedBox(width: 8),
                        Text(
                          'Stop generating',
                          style: TextStyle(
                            color: Colors.white.withValues(alpha: 0.65),
                            fontSize: 12,
                            fontWeight: FontWeight.w500,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ),
          _buildInputBar(context),
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 4, 16, 10),
            child: Text(
              '18+ only. Gambling involves risk. Informational only — not financial or legal advice.',
              textAlign: TextAlign.center,
              style: TextStyle(
                fontSize: 10,
                height: 1.35,
                color: Colors.grey[700],
              ),
            ),
          ),
        ],
      ),
    );
  }

  // ── AppBar ──────────────────────────────────────────────────────────────────

  PreferredSizeWidget _buildAppBar() {
    final msgCount = _messages.length;
    return AppBar(
      backgroundColor: _kBg,
      elevation: 0,
      title: Row(
        children: [
          Container(
            width: 28,
            height: 28,
            decoration: BoxDecoration(
              color: _kCard,
              borderRadius: BorderRadius.circular(8),
              border: Border.all(
                color: Colors.white.withValues(alpha: 0.1),
                width: 1,
              ),
            ),
            child: const Center(
              child: CustomPaint(
                size: Size(16, 16),
                painter: _HexagonPainter(color: _kTeal),
              ),
            ),
          ),
          const SizedBox(width: 10),
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              const Text(
                'BettingCopilot',
                style: TextStyle(
                  fontSize: 15,
                  fontWeight: FontWeight.w600,
                  color: Colors.white,
                  letterSpacing: -0.3,
                ),
              ),
              if (msgCount > 0)
                Text(
                  '$msgCount message${msgCount == 1 ? '' : 's'}',
                  style: TextStyle(
                    fontSize: 10,
                    color: Colors.grey[600],
                    fontWeight: FontWeight.w400,
                  ),
                ),
            ],
          ),
        ],
      ),
      actions: [
        if (_messages.isNotEmpty)
          IconButton(
            icon: Icon(Icons.add_comment_outlined,
                color: Colors.white.withValues(alpha: 0.45), size: 20),
            tooltip: 'New chat',
            onPressed: _confirmNewChat,
          ),
      ],
      bottom: PreferredSize(
        preferredSize: const Size.fromHeight(1),
        child: Container(
          height: 1,
          color: Colors.white.withValues(alpha: 0.06),
        ),
      ),
    );
  }

  // ── Message list ────────────────────────────────────────────────────────────

  Widget _buildMessageList() {
    return ListView.builder(
      controller: _scrollCtrl,
      padding: const EdgeInsets.symmetric(vertical: 16),
      itemCount: _messages.length,
      itemBuilder: (_, i) {
        final msg = _messages[i];
        return msg.role == 'user'
            ? UserMessageBubble(message: msg)
            : AssistantMessageBubble(
                message: msg,
                streaming: _streaming && i == _messages.length - 1,
              );
      },
    );
  }

  // ── Empty / suggestion state ────────────────────────────────────────────────

  Widget _buildEmptyState() {
    return SingleChildScrollView(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(24, 56, 24, 24),
        child: Column(
          children: [
            Container(
              width: 56,
              height: 56,
              decoration: BoxDecoration(
                color: _kCard,
                borderRadius: BorderRadius.circular(16),
                border: Border.all(
                  color: Colors.white.withValues(alpha: 0.08),
                  width: 1,
                ),
              ),
              child: const Center(
                child: CustomPaint(
                  size: Size(28, 28),
                  painter: _HexagonPainter(color: _kTeal),
                ),
              ),
            ),
            const SizedBox(height: 20),
            const Text(
              'BettingCopilot',
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.w600,
                color: Colors.white,
                letterSpacing: -0.5,
              ),
            ),
            const SizedBox(height: 6),
            Text(
              'Ask about value, Kelly stakes, or any game.',
              style: TextStyle(
                fontSize: 13,
                color: Colors.grey[600],
                height: 1.4,
              ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 32),
            // 2-column grid — context-aware suggestions from live AppState
            Consumer<AppState>(
              builder: (context, state, _) {
                final suggestions = _buildDynamicSuggestions(state);
                return Column(
                  children: [
                    Row(children: [
                      Expanded(child: SuggestionCard(label: suggestions[0].label, icon: suggestions[0].icon, onTap: () => _send(suggestions[0].label))),
                      const SizedBox(width: 10),
                      Expanded(child: SuggestionCard(label: suggestions[1].label, icon: suggestions[1].icon, onTap: () => _send(suggestions[1].label))),
                    ]),
                    const SizedBox(height: 10),
                    Row(children: [
                      Expanded(child: SuggestionCard(label: suggestions[2].label, icon: suggestions[2].icon, onTap: () => _send(suggestions[2].label))),
                      const SizedBox(width: 10),
                      Expanded(child: SuggestionCard(label: suggestions[3].label, icon: suggestions[3].icon, onTap: () => _send(suggestions[3].label))),
                    ]),
                  ],
                );
              },
            ),
          ],
        ),
      ),
    );
  }

  // ── Dynamic suggestions based on live AppState ──────────────────────────────

  List<({String label, IconData icon})> _buildDynamicSuggestions(AppState state) {
    final list = <({String label, IconData icon})>[];

    if (state.valuePlays.isNotEmpty) {
      final top = state.valuePlays.first;
      final ev = (top.expectedValue * 100).toStringAsFixed(1);
      list.add((
        label: 'Analyze ${top.event} (+$ev% EV on ${top.book})',
        icon: Icons.trending_up_rounded,
      ));
    } else {
      list.add((
        label: 'Best value bet right now?',
        icon: Icons.trending_up_rounded,
      ));
    }

    if (state.lineMovements.isNotEmpty) {
      final lm = state.lineMovements.first;
      list.add((
        label: 'What\'s moving: ${lm.event} (${lm.direction})',
        icon: Icons.show_chart_rounded,
      ));
    } else {
      list.add((
        label: 'Explain this line movement',
        icon: Icons.show_chart_rounded,
      ));
    }

    if (state.arbitrage.isNotEmpty) {
      final arb = state.arbitrage.first;
      final pct = arb.profitPercent.toStringAsFixed(1);
      list.add((
        label: 'Explain $pct% arb on ${arb.event}',
        icon: Icons.bolt_rounded,
      ));
    } else {
      list.add((
        label: 'Best spread across books for a game?',
        icon: Icons.compare_arrows_rounded,
      ));
    }

    if (state.pmPlays.isNotEmpty) {
      final topPm = state.pmPlays.reduce((a, b) => a.expectedValue > b.expectedValue ? a : b);
      final pmEv = (topPm.expectedValue * 100).toStringAsFixed(1);
      list.add((
        label: 'Analyze PM edge: ${topPm.market} (+$pmEv%)',
        icon: Icons.candlestick_chart_rounded,
      ));
    } else {
      list.add((
        label: 'Any prediction market edges right now?',
        icon: Icons.candlestick_chart_rounded,
      ));
    }

    list.add((
      label: 'Kelly stake for +150, 55% edge',
      icon: Icons.calculate_rounded,
    ));

    return list.take(4).toList();
  }

  // ── Input bar ───────────────────────────────────────────────────────────────

  Widget _buildInputBar(BuildContext context) {
    final bottom = MediaQuery.of(context).viewInsets.bottom;
    return Container(
      color: _kBg,
      padding: EdgeInsets.fromLTRB(12, 8, 12, 8 + bottom),
      child: Container(
        decoration: BoxDecoration(
          color: _kCard,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(
            color: Colors.white.withValues(alpha: 0.08),
            width: 0.5,
          ),
        ),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.end,
          children: [
            Expanded(
              child: TextField(
                controller: _inputCtrl,
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 14,
                  height: 1.4,
                ),
                decoration: InputDecoration(
                  hintText: 'Ask about any game or bet...',
                  hintStyle: TextStyle(
                    color: Colors.grey[700],
                    fontSize: 14,
                  ),
                  border: InputBorder.none,
                  contentPadding: const EdgeInsets.symmetric(
                    horizontal: 14,
                    vertical: 12,
                  ),
                ),
                onSubmitted: _send,
                enabled: !_streaming,
                maxLines: 5,
                minLines: 1,
              ),
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(0, 0, 8, 8),
              child: _streaming
                  ? const LoadingDots()
                  : GestureDetector(
                      onTap: () => _send(_inputCtrl.text),
                      child: Container(
                        width: 32,
                        height: 32,
                        decoration: BoxDecoration(
                          color: _kTeal,
                          borderRadius: BorderRadius.circular(9),
                          boxShadow: [
                            BoxShadow(
                              color: _kTeal.withValues(alpha: 0.3),
                              blurRadius: 8,
                              offset: const Offset(0, 2),
                            ),
                          ],
                        ),
                        child: const Icon(
                          Icons.arrow_upward_rounded,
                          color: Colors.black,
                          size: 16,
                        ),
                      ),
                    ),
            ),
          ],
        ),
      ),
    );
  }
}

// ── Hexagon painter (matches web SVG icon) ────────────────────────────────────

class _HexagonPainter extends CustomPainter {
  final Color color;
  const _HexagonPainter({required this.color});

  List<Offset> _hexPoints(Offset center, double r) {
    return List.generate(6, (i) {
      final angle = (i * 60 - 90) * math.pi / 180;
      return Offset(center.dx + r * math.cos(angle),
          center.dy + r * math.sin(angle));
    });
  }

  Path _hexPath(List<Offset> pts) {
    final p = Path()..moveTo(pts[0].dx, pts[0].dy);
    for (var i = 1; i < pts.length; i++) {
      p.lineTo(pts[i].dx, pts[i].dy);
    }
    return p..close();
  }

  @override
  void paint(Canvas canvas, Size size) {
    final c = Offset(size.width / 2, size.height / 2);
    final outerR = size.width * 0.46;
    final innerR = size.width * 0.26;

    // outer hex stroke
    canvas.drawPath(
      _hexPath(_hexPoints(c, outerR)),
      Paint()
        ..style = PaintingStyle.stroke
        ..color = color
        ..strokeWidth = 1.5
        ..strokeJoin = StrokeJoin.round,
    );
    // inner hex fill + stroke
    final innerPts = _hexPoints(c, innerR);
    canvas.drawPath(
      _hexPath(innerPts),
      Paint()
        ..style = PaintingStyle.fill
        ..color = color.withValues(alpha: 0.15),
    );
    canvas.drawPath(
      _hexPath(innerPts),
      Paint()
        ..style = PaintingStyle.stroke
        ..color = color
        ..strokeWidth = 1.0
        ..strokeJoin = StrokeJoin.round,
    );
  }

  @override
  bool shouldRepaint(_HexagonPainter old) => old.color != color;
}
