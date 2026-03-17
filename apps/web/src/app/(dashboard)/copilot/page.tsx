'use client'

import { ChatStream } from '@/components/copilot/chat-stream'

export default function CopilotPage() {
  return (
    <div className="relative h-[calc(100vh-4rem)]">
      <ChatStream />
    </div>
  )
}
