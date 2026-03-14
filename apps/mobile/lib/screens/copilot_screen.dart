import 'dart:async';
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import '../services/api_service.dart';

const _kBg = Color(0xFF0A0E1A);

class CopilotScreen extends StatefulWidget {
  const CopilotScreen({super.key});
  @override
  State<CopilotScreen> createState() => _CopilotScreenState();
}

class _CopilotScreenState extends State<CopilotScreen> {
  final List<_Message> _messages = [];
  final _inputCtrl = TextEditingController();
  final _scrollCtrl = ScrollController();
  bool _streaming = false;

  @override
  void dispose() {
    _inputCtrl.dispose();
    _scrollCtrl.dispose();
    super.dispose();
  }

  Future<void> _send(String text) async {
    if (text.trim().isEmpty || _streaming) return;
    setState(() {
      _messages.add(_Message(role: 'user', content: text.trim()));
      _messages.add(_Message(role: 'assistant', content: ''));
      _streaming = true;
    });
    _inputCtrl.clear();

    final baseUrl = ApiService.baseUrl;
    final uri = Uri.parse('$baseUrl/api/v1/copilot/chat');
    final request = http.Request('POST', uri)
      ..headers['Content-Type'] = 'application/json'
      ..body = jsonEncode({'message': text.trim()});

    try {
      final streamedResponse = await http.Client().send(request);
      await for (final chunk in streamedResponse.stream
          .transform(utf8.decoder)
          .transform(const LineSplitter())) {
        if (chunk.startsWith('data: ') && chunk != 'data: [DONE]') {
          final token = chunk.substring(6).replaceAll(r'\n', '\n');
          setState(() {
            _messages.last = _Message(
              role: 'assistant',
              content: _messages.last.content + token,
            );
          });
          if (_scrollCtrl.hasClients) {
            _scrollCtrl.jumpTo(_scrollCtrl.position.maxScrollExtent);
          }
        }
      }
    } catch (e) {
      setState(() {
        _messages.last = _Message(
          role: 'assistant',
          content: 'Error: ${e.toString()}',
        );
      });
    } finally {
      if (mounted) setState(() { _streaming = false; });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: _kBg,
      appBar: AppBar(
        backgroundColor: _kBg,
        title: const Text('BettingCopilot'),
      ),
      body: Column(
        children: [
          Expanded(
            child: _messages.isEmpty
                ? _buildEmptyState()
                : ListView.builder(
                    controller: _scrollCtrl,
                    padding: const EdgeInsets.all(12),
                    itemCount: _messages.length,
                    itemBuilder: (_, i) {
                      final msg = _messages[i];
                      final isUser = msg.role == 'user';
                      return Align(
                        alignment: isUser
                            ? Alignment.centerRight
                            : Alignment.centerLeft,
                        child: Container(
                          margin: const EdgeInsets.symmetric(vertical: 4),
                          padding: const EdgeInsets.symmetric(
                              horizontal: 12, vertical: 8),
                          constraints: BoxConstraints(
                              maxWidth:
                                  MediaQuery.of(context).size.width * 0.75),
                          decoration: BoxDecoration(
                            color: isUser
                                ? const Color(0xFF3B82F6)
                                : const Color(0xFF27272A),
                            borderRadius: BorderRadius.circular(12),
                          ),
                          child: msg.content.isEmpty && !isUser
                              ? const SizedBox(
                                  width: 20,
                                  height: 14,
                                  child: CircularProgressIndicator(
                                    strokeWidth: 2,
                                    color: Colors.white54,
                                  ),
                                )
                              : Text(
                                  msg.content,
                                  style: const TextStyle(
                                      color: Colors.white, fontSize: 14),
                                ),
                        ),
                      );
                    },
                  ),
          ),
          if (_streaming)
            const LinearProgressIndicator(minHeight: 2),
          Padding(
            padding: EdgeInsets.fromLTRB(12, 8, 12,
                8 + MediaQuery.of(context).viewInsets.bottom),
            child: Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _inputCtrl,
                    style: const TextStyle(color: Colors.white),
                    decoration: const InputDecoration(
                      hintText: 'Ask about any game or bet...',
                      border: OutlineInputBorder(),
                    ),
                    onSubmitted: _send,
                    enabled: !_streaming,
                  ),
                ),
                const SizedBox(width: 8),
                IconButton(
                  icon: const Icon(Icons.send),
                  onPressed: _streaming ? null : () => _send(_inputCtrl.text),
                  color: const Color(0xFF00D4AA),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildEmptyState() {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.chat_bubble_outline, color: Colors.grey[700], size: 40),
            const SizedBox(height: 14),
            const Text(
              'BettingCopilot',
              style: TextStyle(
                color: Colors.white70,
                fontSize: 15,
                fontWeight: FontWeight.w600,
                letterSpacing: -0.3,
              ),
            ),
            const SizedBox(height: 6),
            Text(
              'Ask about games, edges, or\nKelly stake recommendations',
              style: TextStyle(
                color: Colors.grey[600],
                fontSize: 12,
                fontWeight: FontWeight.w400,
              ),
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }
}

class _Message {
  final String role, content;
  const _Message({required this.role, required this.content});
}
