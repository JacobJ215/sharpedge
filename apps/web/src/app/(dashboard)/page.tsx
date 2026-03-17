'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'

export default function DashboardIndexPage() {
  const router = useRouter()
  useEffect(() => {
    router.replace('/portfolio')
  }, [router])
  return <div className="min-h-screen bg-zinc-950" />
}
