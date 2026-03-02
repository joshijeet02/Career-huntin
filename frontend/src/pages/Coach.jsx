import { useState, useRef, useEffect } from 'react'
import { api } from '../api/client'

// ── Voice metadata (mirrors backend COUNCIL dict) ─────────────────────────
const VOICES = {
  sage:       { label: 'The Sage',       domain: 'Spiritual & Inner Truth',  icon: '🪔', color: '#f59e0b', bg: 'rgba(245,158,11,0.07)',   border: 'rgba(245,158,11,0.28)'   },
  strategist: { label: 'The Strategist', domain: 'Executive Leadership',      icon: '🎯', color: '#3b82f6', bg: 'rgba(59,130,246,0.07)',   border: 'rgba(59,130,246,0.28)'   },
  heart:      { label: 'The Heart',      domain: 'Relationships & Emotion',   icon: '🫀', color: '#f43f5e', bg: 'rgba(244,63,94,0.07)',    border: 'rgba(244,63,94,0.28)'    },
  scientist:  { label: 'The Scientist',  domain: 'Behaviour & Psychology',    icon: '🧬', color: '#10b981', bg: 'rgba(16,185,129,0.07)',   border: 'rgba(16,185,129,0.28)'   },
}

// ── Sub-components ────────────────────────────────────────────────────────

function VoiceCard({ voice }) {
  const meta = VOICES[voice.id] || {}
  const color  = voice.color  || meta.color  || '#6366f1'
  const bg     = voice.bg     || meta.bg     || 'rgba(99,102,241,0.07)'
  const border = voice.border || meta.border || 'rgba(99,102,241,0.28)'

  return (
    <div style={{
      background: bg,
      border: `1px solid ${border}`,
      borderRadius: 14,
      padding: '14px 16px',
      marginBottom: 10,
    }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
        <span style={{ fontSize: 18 }}>{voice.icon || meta.icon}</span>
        <div>
          <div style={{ fontSize: 13, fontWeight: 700, color }}>{voice.name || meta.label}</div>
          <div style={{ fontSize: 11, color: 'var(--text3)', marginTop: 1 }}>{voice.domain || meta.domain}</div>
        </div>
      </div>
      {/* Response */}
      <p style={{
        fontSize: 14,
        lineHeight: 1.65,
        color: 'var(--text1)',
        margin: 0,
        fontStyle: voice.id === 'sage' ? 'italic' : 'normal',
      }}>
        {voice.response}
      </p>
      {/* Master citation */}
      {voice.master && (
        <div style={{
          marginTop: 10,
          display: 'inline-block',
          fontSize: 11,
          color,
          background: bg,
          border: `1px solid ${border}`,
          borderRadius: 20,
          padding: '3px 10px',
          fontWeight: 600,
        }}>
          — {voice.master}
        </div>
      )}
    </div>
  )
}

function SynthesisCard({ text }) {
  return (
    <div style={{
      background: 'rgba(99,102,241,0.06)',
      border: '1px solid rgba(99,102,241,0.22)',
      borderRadius: 14,
      padding: '14px 16px',
      marginTop: 4,
    }}>
      <div style={{ fontSize: 11, fontWeight: 700, color: '#818cf8', marginBottom: 6, letterSpacing: '0.08em', textTransform: 'uppercase' }}>
        The Council agrees
      </div>
      <p style={{
        fontSize: 14,
        lineHeight: 1.65,
        color: 'var(--text1)',
        margin: 0,
        fontStyle: 'italic',
      }}>
        "{text}"
      </p>
    </div>
  )
}

function ConveningAnimation() {
  const icons = ['🪔', '🎯', '🫀', '🧬']
  return (
    <div style={{ padding: '16px 0', display: 'flex', flexDirection: 'column', alignItems: 'flex-start', gap: 10 }}>
      <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
        {icons.map((icon, i) => (
          <span
            key={i}
            style={{
              fontSize: 22,
              animation: `pulse 1.4s ease-in-out ${i * 0.2}s infinite`,
              display: 'inline-block',
            }}
          >
            {icon}
          </span>
        ))}
      </div>
      <div style={{ fontSize: 12, color: 'var(--text3)', fontStyle: 'italic' }}>
        The Council is convening…
      </div>
    </div>
  )
}

// ── Main component ────────────────────────────────────────────────────────

export default function Coach({ uid }) {
  const [messages, setMessages] = useState([
    {
      role: 'council-intro',
      text: 'Your personal board of directors is assembled. Four voices — spiritual, strategic, relational, psychological — will respond together to whatever you bring. Nothing is too small or too large.',
    },
  ])
  const [input, setInput]     = useState('')
  const [loading, setLoading] = useState(false)
  const bottomRef             = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  const send = async () => {
    const msg = input.trim()
    if (!msg || loading) return
    setInput('')

    // Append user message
    const userMsg = { role: 'user', text: msg }
    setMessages(m => [...m, userMsg])
    setLoading(true)

    // Build history for context (last 6 entries, skip intro)
    const history = [...messages, userMsg]
      .filter(m => m.role === 'user' || m.role === 'council')
      .map(m =>
        m.role === 'user'
          ? { role: 'user', text: m.text }
          : { role: 'council', synthesis: m.synthesis || '' }
      )
      .slice(-6)

    try {
      const res = await api.council.ask(uid, msg, history)
      setMessages(m => [...m, { role: 'council', voices: res.voices || [], synthesis: res.synthesis || '' }])
    } catch {
      setMessages(m => [...m, {
        role: 'council',
        voices: [],
        synthesis: 'The Council was unable to convene right now. Please try again in a moment.',
      }])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>

      {/* Header */}
      <div style={{
        padding: '16px 18px 12px',
        borderBottom: '1px solid var(--border)',
        flexShrink: 0,
        background: 'var(--bg1)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{ fontSize: 22 }}>⚖️</div>
          <div>
            <div style={{ fontSize: 16, fontWeight: 700 }}>The Council</div>
            <div style={{ fontSize: 11, color: 'var(--text3)', marginTop: 1 }}>
              {Object.values(VOICES).map(v => v.icon).join('  ')}  &nbsp;Four voices, one truth
            </div>
          </div>
        </div>
      </div>

      {/* Messages */}
      <div style={{
        flex: 1,
        overflowY: 'auto',
        padding: '16px',
        display: 'flex',
        flexDirection: 'column',
        gap: 16,
        WebkitOverflowScrolling: 'touch',
      }}>
        {messages.map((m, i) => {

          // ── Council intro card ──
          if (m.role === 'council-intro') {
            return (
              <div key={i} style={{
                background: 'linear-gradient(135deg, rgba(99,102,241,0.1), rgba(139,92,246,0.08))',
                border: '1px solid rgba(99,102,241,0.2)',
                borderRadius: 16,
                padding: '16px 18px',
              }}>
                <div style={{ display: 'flex', gap: 8, marginBottom: 10 }}>
                  {Object.values(VOICES).map(v => (
                    <span key={v.icon} style={{ fontSize: 20 }}>{v.icon}</span>
                  ))}
                </div>
                <p style={{ fontSize: 14, lineHeight: 1.65, color: 'var(--text2)', margin: 0 }}>
                  {m.text}
                </p>
                <div style={{ marginTop: 12, display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                  {Object.values(VOICES).map(v => (
                    <span key={v.label} style={{
                      fontSize: 11, fontWeight: 600,
                      color: v.color,
                      background: v.bg,
                      border: `1px solid ${v.border}`,
                      borderRadius: 20, padding: '3px 10px',
                    }}>
                      {v.icon} {v.label}
                    </span>
                  ))}
                </div>
              </div>
            )
          }

          // ── User message ──
          if (m.role === 'user') {
            return (
              <div key={i} style={{ display: 'flex', justifyContent: 'flex-end' }}>
                <div className="bubble-user" style={{ maxWidth: '80%' }}>
                  {m.text}
                </div>
              </div>
            )
          }

          // ── Council response ──
          if (m.role === 'council') {
            return (
              <div key={i}>
                {m.voices && m.voices.length > 0
                  ? m.voices.map(v => <VoiceCard key={v.id} voice={v} />)
                  : null
                }
                {m.synthesis ? <SynthesisCard text={m.synthesis} /> : null}
              </div>
            )
          }

          return null
        })}

        {/* Loading state */}
        {loading && <ConveningAnimation />}

        <div ref={bottomRef} />
      </div>

      {/* Input bar */}
      <div style={{
        padding: '10px 12px',
        paddingBottom: 'calc(10px + var(--safe-bot))',
        background: 'var(--bg2)',
        borderTop: '1px solid var(--border)',
        display: 'flex',
        gap: 10,
        flexShrink: 0,
      }}>
        <textarea
          className="input"
          rows={1}
          style={{
            flex: 1,
            borderRadius: 20,
            padding: '12px 18px',
            resize: 'none',
            lineHeight: 1.5,
            fontFamily: 'inherit',
            fontSize: 14,
            overflowY: 'hidden',
          }}
          placeholder="Bring anything to the Council…"
          value={input}
          onChange={e => {
            setInput(e.target.value)
            e.target.style.height = 'auto'
            e.target.style.height = Math.min(e.target.scrollHeight, 120) + 'px'
          }}
          onKeyDown={e => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault()
              send()
            }
          }}
        />
        <button
          className="btn btn-primary"
          style={{ width: 46, height: 46, padding: 0, borderRadius: 23, flexShrink: 0, alignSelf: 'flex-end' }}
          onClick={send}
          disabled={loading || !input.trim()}
        >
          ↑
        </button>
      </div>

      {/* Pulse animation keyframes */}
      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 0.3; transform: scale(0.85); }
          50%       { opacity: 1;   transform: scale(1.1);  }
        }
      `}</style>
    </div>
  )
}
