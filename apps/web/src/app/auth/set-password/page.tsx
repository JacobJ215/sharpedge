'use client'

import { useEffect, useState } from 'react'
import { supabase } from '@/lib/supabase'

export default function SetPasswordPage() {
  const [password, setPassword] = useState('')
  const [status, setStatus] = useState<'idle' | 'loading' | 'done' | 'error'>('idle')
  const [message, setMessage] = useState('')
  const [sessionReady, setSessionReady] = useState(false)

  useEffect(() => {
    const hash = window.location.hash
    const params = new URLSearchParams(hash.replace('#', ''))
    const accessToken = params.get('access_token')
    const refreshToken = params.get('refresh_token') ?? ''

    if (accessToken) {
      supabase.auth.setSession({ access_token: accessToken, refresh_token: refreshToken }).then(
        ({ error }) => {
          if (error) setMessage('Session error: ' + error.message)
          else setSessionReady(true)
        }
      )
    } else {
      setMessage('No access token found. Navigate here directly from the invite link.')
    }
  }, [])

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setStatus('loading')
    const { error } = await supabase.auth.updateUser({ password })
    if (error) {
      setStatus('error')
      setMessage(error.message)
    } else {
      setStatus('done')
      setMessage('Password set! You can now sign in to the Flutter app.')
    }
  }

  return (
    <main style={{ padding: 40, fontFamily: 'sans-serif', maxWidth: 400 }}>
      <h1>Set Password</h1>
      {!sessionReady && <p style={{ color: message ? 'red' : '#888' }}>{message || 'Loading session…'}</p>}
      {sessionReady && status !== 'done' && (
        <form onSubmit={handleSubmit}>
          <input
            type="password"
            placeholder="New password (min 6 chars)"
            value={password}
            onChange={e => setPassword(e.target.value)}
            minLength={6}
            required
            style={{ display: 'block', width: '100%', padding: 8, marginBottom: 12, fontSize: 16 }}
          />
          <button type="submit" disabled={status === 'loading'} style={{ padding: '8px 24px', fontSize: 16 }}>
            {status === 'loading' ? 'Setting…' : 'Set Password'}
          </button>
          {status === 'error' && <p style={{ color: 'red', marginTop: 8 }}>{message}</p>}
        </form>
      )}
      {status === 'done' && <p style={{ color: 'green' }}>{message}</p>}
    </main>
  )
}
