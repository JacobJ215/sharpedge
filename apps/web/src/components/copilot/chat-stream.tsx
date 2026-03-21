'use client'

import React, { useState, useRef, useEffect, useCallback } from 'react'
import { supabase } from '@/lib/supabase'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'
const COPILOT_THREAD_STORAGE_KEY = 'sharpedge_copilot_thread_id'

function getOrCreateCopilotThreadId(): string {
  if (typeof window === 'undefined') return ''
  let id = localStorage.getItem(COPILOT_THREAD_STORAGE_KEY)
  if (!id) {
    id = crypto.randomUUID()
    localStorage.setItem(COPILOT_THREAD_STORAGE_KEY, id)
  }
  return id
}

function rotateCopilotThreadId(): void {
  if (typeof window === 'undefined') return
  localStorage.setItem(COPILOT_THREAD_STORAGE_KEY, crypto.randomUUID())
}

interface Message {
  role: 'user' | 'assistant'
  content: string
}

const SUGGESTION_ICONS: Record<string, React.ReactNode> = {
  'Best value bet right now?': (
    <svg width="13" height="13" viewBox="0 0 13 13" fill="none" stroke="#10b981" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <polyline points="1,10 4.5,5.5 7.5,7.5 12,2" />
      <polyline points="8.5,2 12,2 12,5.5" />
    </svg>
  ),
  'Size my bet using Kelly criterion': (
    <svg width="13" height="13" viewBox="0 0 13 13" fill="none" stroke="#10b981" strokeWidth="1.75" strokeLinecap="round" aria-hidden="true">
      <rect x="1" y="6.5" width="2.5" height="5.5" rx="0.5" />
      <rect x="5.25" y="3.5" width="2.5" height="8.5" rx="0.5" />
      <rect x="9.5" y="1" width="2.5" height="11" rx="0.5" />
    </svg>
  ),
  'Explain this line movement': (
    <svg width="13" height="13" viewBox="0 0 13 13" fill="none" stroke="#10b981" strokeWidth="1.75" strokeLinecap="round" aria-hidden="true">
      <path d="M2 10 5 6.5 8 8 11 3" />
      <circle cx="2" cy="10" r="1" fill="#10b981" stroke="none" />
      <circle cx="5" cy="6.5" r="1" fill="#10b981" stroke="none" />
      <circle cx="8" cy="8" r="1" fill="#10b981" stroke="none" />
      <circle cx="11" cy="3" r="1" fill="#10b981" stroke="none" />
    </svg>
  ),
  'Best spread across books for a game?': (
    <svg width="13" height="13" viewBox="0 0 13 13" fill="none" stroke="#10b981" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M2 10h9M2 6h6M2 2h4" />
      <path d="M11 2v8l2-2" />
    </svg>
  ),
}

const SUGGESTIONS = [
  'Best value bet right now?',
  'Size my bet using Kelly criterion',
  'Explain this line movement',
  'Best spread across books for a game?',
]

function AssistantText({ content, isStreaming }: { content: string; isStreaming: boolean }) {
  return (
    <div className="text-sm leading-relaxed text-zinc-200 [&>p]:mb-2 [&>p:last-child]:mb-0 [&>ul]:list-disc [&>ul]:pl-5 [&>ul]:mb-2 [&>ol]:list-decimal [&>ol]:pl-5 [&>ol]:mb-2 [&>li]:my-0.5 [&>h1]:text-base [&>h1]:font-semibold [&>h1]:text-white [&>h1]:mb-1 [&>h2]:text-sm [&>h2]:font-semibold [&>h2]:text-white [&>h2]:mb-1 [&>h3]:text-sm [&>h3]:font-medium [&>h3]:text-zinc-100 [&>h3]:mb-1 [&>blockquote]:border-l-2 [&>blockquote]:border-zinc-600 [&>blockquote]:pl-3 [&>blockquote]:text-zinc-400 [&>blockquote]:italic [&>table]:w-full [&>table]:text-xs [&>table]:mb-2">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          pre: ({ children }) => (
            <pre className="bg-zinc-800/80 p-3 rounded-lg overflow-x-auto mb-2 text-xs font-mono">{children}</pre>
          ),
          code: ({ className, children, ...props }) => {
            const isBlock = /language-\w+/.test(className ?? '')
            if (isBlock) {
              return <code className={`${className ?? ''} text-zinc-200`} {...props}>{children}</code>
            }
            return <code className="bg-zinc-800/80 px-1.5 py-0.5 rounded text-[#7DD3FC] text-xs font-mono" {...props}>{children}</code>
          },
          strong: ({ children }) => <strong className="font-semibold text-white">{children}</strong>,
          a: ({ children, href }) => (
            <a href={href} className="text-[#00D4AA] underline" target="_blank" rel="noopener noreferrer">{children}</a>
          ),
          th: ({ children }) => <th className="text-left py-1.5 px-2 border-b border-zinc-700 text-zinc-300 font-medium">{children}</th>,
          td: ({ children }) => <td className="py-1.5 px-2 border-b border-zinc-800">{children}</td>,
        }}
      >
        {content}
      </ReactMarkdown>
      {isStreaming && (
        <span className="inline-block ml-0.5 w-[2px] h-[1.1em] bg-[#00D4AA] align-middle animate-[blink_1s_step-end_infinite]" />
      )}
    </div>
  )
}

function EmptyState({ onSuggestion }: { onSuggestion: (text: string) => void }) {
  return (
    <div className="flex flex-col items-center justify-center h-full px-6 pb-24 select-none">
      {/* Logo mark */}
      <div className="flex items-center justify-center w-14 h-14 rounded-2xl bg-zinc-900 border border-zinc-800 mb-5 shadow-lg">
        <svg width="28" height="28" viewBox="0 0 28 28" fill="none" aria-hidden="true">
          <path
            d="M14 3L24 8.5V19.5L14 25L4 19.5V8.5L14 3Z"
            fill="none"
            stroke="#00D4AA"
            strokeWidth="1.5"
            strokeLinejoin="round"
          />
          <path
            d="M14 8L19 10.75V16.25L14 19L9 16.25V10.75L14 8Z"
            fill="#00D4AA"
            fillOpacity="0.15"
            stroke="#00D4AA"
            strokeWidth="1"
            strokeLinejoin="round"
          />
        </svg>
      </div>

      <h2 className="text-xl font-semibold text-white mb-1.5 tracking-tight">
        BettingCopilot
      </h2>
      <p className="text-sm text-zinc-500 text-center max-w-xs leading-relaxed mb-8">
        AI-powered analysis across your portfolio, value plays, and live market conditions.
      </p>

      {/* Suggestion chips — 2x2 grid */}
      <div className="grid grid-cols-2 gap-2.5 w-full max-w-md">
        {SUGGESTIONS.map((label) => (
          <button
            key={label}
            onClick={() => onSuggestion(label)}
            className="flex items-start gap-2.5 rounded-xl bg-zinc-900 border border-zinc-800 hover:border-emerald-500/20 hover:bg-zinc-800/70 px-4 py-3 text-left text-sm text-zinc-300 transition-all duration-150 cursor-pointer group"
          >
            <span className="mt-0.5 shrink-0 opacity-80 group-hover:opacity-100 transition-opacity">{SUGGESTION_ICONS[label]}</span>
            <span className="leading-snug group-hover:text-zinc-100 transition-colors">{label}</span>
          </button>
        ))}
      </div>
    </div>
  )
}

export function ChatStream() {
  const [messages, setMessages] = useState<Message[]>([])
  const [inputValue, setInputValue] = useState('')
  const [isStreaming, setIsStreaming] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const abortRef = useRef<AbortController | null>(null)

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    if (bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [messages])

  // Auto-resize textarea
  useEffect(() => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`
  }, [inputValue])

  const sendMessage = useCallback(async (text: string) => {
    const trimmed = text.trim()
    if (!trimmed || isStreaming) return

    setMessages((prev) => [...prev, { role: 'user', content: trimmed }])
    setInputValue('')
    setIsStreaming(true)

    let assistantMsg = ''
    setMessages((prev) => [...prev, { role: 'assistant', content: '' }])

    const controller = new AbortController()
    abortRef.current = controller

    try {
      const { data: { session } } = await supabase.auth.getSession()
      const authHeaders: Record<string, string> = { 'Content-Type': 'application/json' }
      if (session?.access_token) {
        authHeaders['Authorization'] = `Bearer ${session.access_token}`
      }

      const threadId = getOrCreateCopilotThreadId()
      const res = await fetch(`${API_BASE}/api/v1/copilot/chat`, {
        method: 'POST',
        headers: authHeaders,
        body: JSON.stringify({ message: trimmed, thread_id: threadId }),
        signal: controller.signal,
      })

      const reader = res.body!.getReader()
      const decoder = new TextDecoder()

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        const chunk = decoder.decode(value)
        for (const line of chunk.split('\n')) {
          if (line.startsWith('data: ') && line !== 'data: [DONE]') {
            assistantMsg += line.slice(6).replace(/\\n/g, '\n')
            setMessages((prev) => [
              ...prev.slice(0, -1),
              { role: 'assistant', content: assistantMsg },
            ])
          }
        }
      }
    } catch (err: unknown) {
      if (err instanceof Error && err.name === 'AbortError') return
      setMessages((prev) => [
        ...prev.slice(0, -1),
        { role: 'assistant', content: 'Error: could not reach copilot.' },
      ])
    } finally {
      setIsStreaming(false)
      abortRef.current = null
    }
  }, [isStreaming])

  const stopStreaming = () => {
    abortRef.current?.abort()
    setIsStreaming(false)
  }

  const clearChat = () => {
    if (isStreaming) stopStreaming()
    setMessages([])
    setInputValue('')
    rotateCopilotThreadId()
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage(inputValue)
    }
  }

  const canSend = inputValue.trim().length > 0 && !isStreaming

  return (
    <div className="flex h-full flex-col bg-[#0a0a0a]">
      {/* Top-right toolbar — only shown when there are messages */}
      {messages.length > 0 && (
        <div className="absolute top-0 right-0 p-3 z-10">
          <button
            onClick={clearChat}
            className="text-xs text-zinc-500 hover:text-zinc-300 transition-colors px-3 py-1.5 rounded-lg hover:bg-zinc-800 border border-transparent hover:border-zinc-700"
          >
            New chat
          </button>
        </div>
      )}

      {/* Message list / empty state */}
      <div className="flex-1 overflow-y-auto min-h-0 relative">
        {messages.length === 0 ? (
          <EmptyState onSuggestion={(text) => sendMessage(text)} />
        ) : (
          <div className="max-w-2xl mx-auto px-4 pt-8 pb-4 space-y-6">
            {messages.map((msg, i) => {
              const isLast = i === messages.length - 1
              if (msg.role === 'user') {
                return (
                  <div key={i} className="flex justify-end">
                    <div className="max-w-[75%] rounded-2xl rounded-tr-sm bg-zinc-800 border border-zinc-700/50 px-4 py-2.5 text-sm text-zinc-100 leading-relaxed">
                      {msg.content}
                    </div>
                  </div>
                )
              }
              return (
                <div key={i} className="flex items-start gap-3">
                  {/* Teal avatar dot */}
                  <div className="flex-shrink-0 mt-0.5 w-6 h-6 rounded-full bg-[#00D4AA]/15 border border-[#00D4AA]/30 flex items-center justify-center">
                    <span className="w-1.5 h-1.5 rounded-full bg-[#00D4AA]" />
                  </div>
                  <div className="flex-1 min-w-0 pt-0.5">
                    {msg.content === '' && isStreaming && isLast ? (
                      <span className="flex gap-1 items-center h-5 mt-0.5">
                        <span className="w-1.5 h-1.5 rounded-full bg-zinc-500 animate-[bounce_1s_ease-in-out_infinite]" style={{ animationDelay: '0ms' }} />
                        <span className="w-1.5 h-1.5 rounded-full bg-zinc-500 animate-[bounce_1s_ease-in-out_infinite]" style={{ animationDelay: '150ms' }} />
                        <span className="w-1.5 h-1.5 rounded-full bg-zinc-500 animate-[bounce_1s_ease-in-out_infinite]" style={{ animationDelay: '300ms' }} />
                      </span>
                    ) : (
                      <AssistantText
                        content={msg.content}
                        isStreaming={isStreaming && isLast}
                      />
                    )}
                  </div>
                </div>
              )
            })}
            <div ref={bottomRef} />
          </div>
        )}
      </div>

      {/* Input bar */}
      <div className="px-4 pb-5 pt-2 max-w-2xl w-full mx-auto">
        <div className="flex items-end gap-2 bg-zinc-900 border border-zinc-700/40 rounded-2xl px-4 py-3 focus-within:border-zinc-600/60 transition-colors shadow-lg">
          <textarea
            ref={textareaRef}
            rows={1}
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about your bets…"
            disabled={isStreaming}
            className="flex-1 resize-none bg-transparent text-sm text-zinc-100 placeholder-zinc-600 focus:outline-none disabled:opacity-60 leading-relaxed overflow-hidden"
            style={{ maxHeight: '160px' }}
          />
          {isStreaming ? (
            <button
              onClick={stopStreaming}
              className="flex-shrink-0 w-8 h-8 rounded-full bg-zinc-700 hover:bg-zinc-600 flex items-center justify-center transition-colors mb-0.5"
              aria-label="Stop generating"
            >
              {/* Stop square icon */}
              <span className="w-3 h-3 rounded-sm bg-zinc-200" />
            </button>
          ) : (
            <button
              onClick={() => sendMessage(inputValue)}
              disabled={!canSend}
              className="flex-shrink-0 w-8 h-8 rounded-full bg-[#00D4AA] hover:bg-[#00bfa0] disabled:bg-zinc-700 disabled:cursor-not-allowed flex items-center justify-center transition-colors mb-0.5"
              aria-label="Send message"
            >
              {/* Up-arrow icon */}
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
                <path
                  d="M7 11V3M7 3L3.5 6.5M7 3L10.5 6.5"
                  stroke={canSend ? '#0a0a0a' : '#52525b'}
                  strokeWidth="1.75"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            </button>
          )}
        </div>
        <p className="text-center text-[11px] text-zinc-600 mt-2 leading-relaxed max-w-xl mx-auto">
          18+ only. Gambling involves risk of loss. Informational only — not financial, investment, or legal
          advice. Comply with laws in your jurisdiction. Scoped to your portfolio and SharpEdge data when signed in.
        </p>
      </div>

    </div>
  )
}
