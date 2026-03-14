'use client'

import { ChatStream } from '@/components/copilot/chat-stream'

export default function CopilotPage() {
  return (
    <div className="flex h-[calc(100vh-4rem)] flex-col">
      <div className="border-b border-zinc-800 px-6 py-4">
        <h1 className="text-xl font-semibold text-white">BettingCopilot</h1>
        <p className="mt-0.5 text-xs text-zinc-500">
          AI-powered betting analysis — ask about value plays, bankroll sizing, regime conditions, or
          market edges. Scope: your portfolio and active SharpEdge data only.
        </p>
      </div>
      <div className="flex-1 min-h-0">
        <ChatStream />
      </div>
    </div>
  )
}
