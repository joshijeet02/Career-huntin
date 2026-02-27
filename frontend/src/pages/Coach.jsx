import { useState, useRef, useEffect } from 'react'
import { api } from '../api/client'

const SESSION_ID = 'session_' + Math.random().toString(36).slice(2, 8)

export default function Coach({ uid }) {
  const [messages, setMessages] = useState([
    { role: 'coach', text: "What's on your mind? I'm listening." }
  ])
  const [input, setInput] = useState('')
  const [thinking, setThinking] = useState(false)
  const [track, setTrack] = useState('general')
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, thinking])

  const send = async () => {
    const msg = input.trim()
    if (!msg || thinking) return
    setInput('')
    setMessages(m => [...m, { role: 'user', text: msg }])
    setThinking(true)
    try {
      const res = await api.coach.message(uid, msg, SESSION_ID, '', track)
      setMessages(m => [...m, { role: 'coach', text: res.message }])
    } catch (e) {
      setMessages(m => [...m, { role: 'coach', text: "I'm having trouble connecting right now. Try again in a moment." }])
    } finally {
      setThinking(false)
    }
  }

  const tracks = [
    { id: 'general', label: 'General' },
    { id: 'leadership', label: 'Leadership' },
    { id: 'relationship', label: 'Relationships' },
    { id: 'wellbeing', label: 'Wellbeing' },
  ]

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      {/* Track selector */}
      <div style={{ padding: '12px 16px 0', flexShrink: 0 }}>
        <div style={{ display: 'flex', gap: 8, overflowX: 'auto', paddingBottom: 8 }}>
          {tracks.map(t => (
            <button
              key={t.id}
              className={`pill ${track === t.id ? 'pill-accent' : ''}`}
              style={{ flexShrink: 0, cursor: 'pointer', background: track === t.id ? undefined : 'var(--bg3)', border: 'none', color: track === t.id ? undefined : 'var(--text2)', padding: '6px 14px', fontSize: 13 }}
              onClick={() => setTrack(t.id)}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>

      {/* Messages */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '12px 16px', display: 'flex', flexDirection: 'column', gap: 12, WebkitOverflowScrolling: 'touch' }}>
        {messages.map((m, i) => (
          <div key={i} className={m.role === 'user' ? 'bubble-user' : 'bubble-coach'}>
            {m.text}
          </div>
        ))}
        {thinking && (
          <div className="bubble-coach" style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
            <span style={{ animation: 'spin 0.8s linear infinite', display: 'inline-block' }}>💭</span>
            <span className="hint">Thinking…</span>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input bar */}
      <div style={{ padding: '10px 12px', paddingBottom: 'calc(10px + var(--safe-bot))', background: 'var(--bg2)', borderTop: '1px solid var(--border)', display: 'flex', gap: 10, flexShrink: 0 }}>
        <input
          className="input"
          style={{ flex: 1, borderRadius: 24, padding: '12px 18px' }}
          placeholder="Message your coach…"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && !e.shiftKey && send()}
        />
        <button
          className="btn btn-primary"
          style={{ width: 46, height: 46, padding: 0, borderRadius: 23, flexShrink: 0 }}
          onClick={send}
          disabled={thinking || !input.trim()}
        >
          ↑
        </button>
      </div>
    </div>
  )
}
