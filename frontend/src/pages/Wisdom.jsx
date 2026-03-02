import { useState, useEffect, useRef } from 'react'
import { api } from '../api/client'

// Tradition → color mapping
const TRADITION_COLORS = {
  'Hindu':           { bg: '#1a0a2e', accent: '#a78bfa', pill: 'rgba(167,139,250,0.15)', text: '#c4b5fd' },
  'Vedanta':         { bg: '#1a0a2e', accent: '#a78bfa', pill: 'rgba(167,139,250,0.15)', text: '#c4b5fd' },
  'Advaita Vedanta': { bg: '#1a0a2e', accent: '#a78bfa', pill: 'rgba(167,139,250,0.15)', text: '#c4b5fd' },
  'Buddhist':        { bg: '#0a1628', accent: '#60a5fa', pill: 'rgba(96,165,250,0.15)',  text: '#93c5fd' },
  'Sufi':            { bg: '#1a1000', accent: '#fbbf24', pill: 'rgba(251,191,36,0.15)',  text: '#fcd34d' },
  'Sufi / Islamic':  { bg: '#1a1000', accent: '#fbbf24', pill: 'rgba(251,191,36,0.15)',  text: '#fcd34d' },
  'Sufi / Persian':  { bg: '#1a1000', accent: '#fbbf24', pill: 'rgba(251,191,36,0.15)',  text: '#fcd34d' },
  'Islamic':         { bg: '#001a0a', accent: '#34d399', pill: 'rgba(52,211,153,0.15)',  text: '#6ee7b7' },
  'Taoist':          { bg: '#001212', accent: '#2dd4bf', pill: 'rgba(45,212,191,0.15)',  text: '#5eead4' },
  'Stoic':           { bg: '#160a00', accent: '#fb923c', pill: 'rgba(251,146,60,0.15)',  text: '#fdba74' },
  'Christian':       { bg: '#0a0f1e', accent: '#818cf8', pill: 'rgba(129,140,248,0.15)', text: '#a5b4fc' },
  'Jain':            { bg: '#0f1a00', accent: '#a3e635', pill: 'rgba(163,230,53,0.15)',  text: '#bef264' },
  'Tamil / Universal': { bg: '#1a0a00', accent: '#f97316', pill: 'rgba(249,115,22,0.15)', text: '#fb923c' },
  'Bhakti / Sufi':   { bg: '#1a0010', accent: '#f472b6', pill: 'rgba(244,114,182,0.15)', text: '#f9a8d4' },
  'Hindu / Universal': { bg: '#1a0a2e', accent: '#a78bfa', pill: 'rgba(167,139,250,0.15)', text: '#c4b5fd' },
  'Kriya Yoga':      { bg: '#1a0a2e', accent: '#a78bfa', pill: 'rgba(167,139,250,0.15)', text: '#c4b5fd' },
  'Universal / Mystical': { bg: '#100a1a', accent: '#e879f9', pill: 'rgba(232,121,249,0.15)', text: '#f0abfc' },
}

function getColors(tradition) {
  return TRADITION_COLORS[tradition] || { bg: '#0f172a', accent: '#64748b', pill: 'rgba(100,116,139,0.15)', text: '#94a3b8' }
}

// Tradition → emoji
const TRADITION_ICON = {
  'Hindu': '🪷', 'Vedanta': '🪷', 'Advaita Vedanta': '🪷', 'Kriya Yoga': '🧘',
  'Buddhist': '☸️', 'Sufi': '🌙', 'Sufi / Islamic': '🌙', 'Sufi / Persian': '🌙',
  'Islamic': '☪️', 'Taoist': '☯️', 'Stoic': '⚡', 'Christian': '✝️',
  'Jain': '🕊️', 'Tamil / Universal': '📜', 'Bhakti / Sufi': '🎶',
  'Hindu / Universal': '🔱', 'Universal / Mystical': '✨',
}
function getIcon(tradition) { return TRADITION_ICON[tradition] || '📿' }

// ── Main component ─────────────────────────────────────────────────────────────
export default function Wisdom({ uid }) {
  const [daily, setDaily] = useState(null)
  const [corpus, setCorpus] = useState(null)
  const [loading, setLoading] = useState(true)
  const [question, setQuestion] = useState('')
  const [asking, setAsking] = useState(false)
  const [answer, setAnswer] = useState(null)
  const [showCorpus, setShowCorpus] = useState(false)
  const answerRef = useRef(null)

  useEffect(() => {
    Promise.allSettled([
      api.wisdom.daily(uid),
      api.wisdom.corpus(),
    ]).then(([d, c]) => {
      if (d.status === 'fulfilled') setDaily(d.value?.wisdom || null)
      if (c.status === 'fulfilled') setCorpus(c.value || null)
      setLoading(false)
    })
  }, [uid])

  const handleAsk = async () => {
    if (!question.trim() || asking) return
    setAsking(true)
    setAnswer(null)
    try {
      const result = await api.wisdom.ask(uid, question.trim())
      setAnswer(result)
      setTimeout(() => answerRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 100)
    } catch (e) {
      setAnswer({ synthesis: 'The masters are reflecting. Please try again in a moment.', citations: [], theme: '' })
    } finally {
      setAsking(false)
    }
  }

  if (loading) return <div className="splash"><div className="spinner" /></div>

  return (
    <div style={{ paddingBottom: 'calc(80px + env(safe-area-inset-bottom))' }}>
      {/* Header */}
      <div style={{
        padding: '20px 20px 16px',
        background: 'linear-gradient(160deg, #0f0c29 0%, #302b63 50%, #24243e 100%)',
        borderBottom: '1px solid rgba(255,255,255,0.06)',
      }}>
        <div style={{ fontSize: 11, fontWeight: 700, color: '#a78bfa', letterSpacing: '0.15em', textTransform: 'uppercase', marginBottom: 4 }}>
          Spiritual Intelligence
        </div>
        <div style={{ fontSize: 24, fontWeight: 800, lineHeight: 1.2, marginBottom: 6 }}>
          Ask the Masters
        </div>
        <div style={{ fontSize: 13, color: '#94a3b8', lineHeight: 1.5 }}>
          2,500 years of wisdom — personalised to your life
        </div>
      </div>

      <div className="p-5">
        {/* Today's Wisdom */}
        {daily && <DailyWisdomCard wisdom={daily} />}

        {/* Ask the Masters input */}
        <div style={{ marginBottom: 28 }}>
          <div className="label mb-3">Ask anything</div>
          <textarea
            value={question}
            onChange={e => setQuestion(e.target.value)}
            placeholder="What should I do when my ego gets in the way of good leadership? How do I find peace in uncertainty? What does wisdom say about letting go?"
            style={{
              width: '100%', background: 'var(--bg2)', border: '1px solid var(--border)',
              borderRadius: 14, padding: '14px 16px', color: 'var(--text)', fontSize: 14,
              lineHeight: 1.6, resize: 'none', minHeight: 100, boxSizing: 'border-box',
              fontFamily: 'inherit', outline: 'none',
            }}
            rows={4}
            onKeyDown={e => { if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) handleAsk() }}
          />
          <button
            onClick={handleAsk}
            disabled={!question.trim() || asking}
            style={{
              marginTop: 10, width: '100%', padding: '13px',
              background: question.trim() && !asking
                ? 'linear-gradient(135deg, #4f46e5, #7c3aed)'
                : 'var(--bg3)',
              color: question.trim() && !asking ? '#fff' : 'var(--text3)',
              border: 'none', borderRadius: 12, fontWeight: 700, fontSize: 14,
              cursor: question.trim() && !asking ? 'pointer' : 'default',
              transition: 'all 0.2s',
            }}
          >
            {asking ? '🌀 Consulting the masters…' : '🔮 Seek wisdom'}
          </button>
        </div>

        {/* Answer from the Masters */}
        {asking && (
          <div style={{ textAlign: 'center', padding: '40px 0', color: '#a78bfa' }}>
            <div style={{ fontSize: 32, marginBottom: 12 }}>🌀</div>
            <div style={{ fontSize: 14, color: '#94a3b8' }}>The masters are speaking across centuries…</div>
          </div>
        )}

        {answer && !asking && (
          <div ref={answerRef}>
            <MastersAnswer answer={answer} question={question} />
          </div>
        )}

        {/* Corpus — who's in the library */}
        {corpus && (
          <div>
            <div
              style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12, cursor: 'pointer' }}
              onClick={() => setShowCorpus(!showCorpus)}
            >
              <div className="label">The Library ({corpus.total_teachings} teachings)</div>
              <span style={{ color: '#64748b', fontSize: 12 }}>{showCorpus ? '▲ Hide' : '▼ Show'}</span>
            </div>

            {showCorpus && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {/* Scriptures first */}
                {corpus.masters.filter(m => m.is_scripture).map((m, i) => (
                  <MasterChip key={i} master={m} />
                ))}
                {/* Then masters */}
                {corpus.masters.filter(m => !m.is_scripture).map((m, i) => (
                  <MasterChip key={i + 100} master={m} />
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

// ── Daily Wisdom Card ──────────────────────────────────────────────────────────
function DailyWisdomCard({ wisdom }) {
  const [expanded, setExpanded] = useState(false)
  const colors = getColors(wisdom.tradition)
  const icon = getIcon(wisdom.tradition)

  return (
    <div
      className="mb-5"
      style={{
        background: `linear-gradient(145deg, ${colors.bg} 0%, #0f172a 100%)`,
        border: `1px solid ${colors.accent}30`,
        borderRadius: 18, padding: '18px 18px 16px', cursor: 'pointer',
      }}
      onClick={() => setExpanded(!expanded)}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 }}>
        <div>
          <div style={{ fontSize: 10, fontWeight: 700, color: colors.accent, letterSpacing: '0.12em', textTransform: 'uppercase', marginBottom: 4 }}>
            Today's Wisdom
          </div>
          <div style={{ fontSize: 15, fontWeight: 700, color: '#f1f5f9' }}>{wisdom.master}</div>
          <div style={{ fontSize: 11, color: colors.text, marginTop: 2 }}>{wisdom.tradition} · {wisdom.era}</div>
        </div>
        <span style={{ fontSize: 28 }}>{icon}</span>
      </div>

      <div style={{
        fontSize: 14, lineHeight: 1.7, color: '#e2e8f0',
        fontFamily: 'Georgia, serif', fontStyle: 'italic',
        borderLeft: `3px solid ${colors.accent}60`, paddingLeft: 14,
        marginBottom: 12,
      }}>
        "{wisdom.quote}"
      </div>

      {wisdom.source && (
        <div style={{ fontSize: 11, color: colors.text, marginBottom: expanded ? 12 : 0 }}>
          — {wisdom.source}
        </div>
      )}

      {expanded && wisdom.reflection && (
        <div style={{
          marginTop: 12, paddingTop: 12, borderTop: `1px solid ${colors.accent}20`,
          fontSize: 13, color: '#94a3b8', lineHeight: 1.6,
        }}>
          <span style={{ fontWeight: 700, color: colors.accent }}>What this means for you: </span>
          {wisdom.reflection}
        </div>
      )}

      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 12 }}>
        {wisdom.themes?.slice(0, 3).map((t, i) => (
          <span key={i} style={{
            fontSize: 10, padding: '3px 10px', borderRadius: 20, fontWeight: 600,
            background: colors.pill, color: colors.text, textTransform: 'capitalize',
          }}>{t}</span>
        ))}
        <span style={{ fontSize: 10, color: '#475569', marginLeft: 'auto', alignSelf: 'center' }}>
          {expanded ? 'Tap to collapse' : 'Tap for reflection'}
        </span>
      </div>
    </div>
  )
}

// ── Masters Answer ─────────────────────────────────────────────────────────────
function MastersAnswer({ answer, question }) {
  return (
    <div className="mb-6">
      <div style={{
        background: 'linear-gradient(145deg, #0f0c29, #1e1b4b)',
        border: '1px solid #4f46e540', borderRadius: 18, overflow: 'hidden',
      }}>
        {/* Header */}
        <div style={{ padding: '16px 18px 0', borderBottom: '1px solid #4f46e520', paddingBottom: 14 }}>
          <div style={{ fontSize: 10, fontWeight: 700, color: '#a78bfa', letterSpacing: '0.12em', textTransform: 'uppercase', marginBottom: 6 }}>
            The Masters respond
          </div>
          <div style={{ fontSize: 13, color: '#64748b', fontStyle: 'italic', lineHeight: 1.4 }}>
            "{question.length > 80 ? question.slice(0, 80) + '…' : question}"
          </div>
        </div>

        {/* Synthesis */}
        <div style={{ padding: '18px 18px 14px' }}>
          <div style={{
            fontSize: 15, lineHeight: 1.8, color: '#e2e8f0',
            fontFamily: 'Georgia, serif', whiteSpace: 'pre-wrap',
          }}>
            {answer.synthesis}
          </div>
        </div>

        {/* Citations */}
        {answer.citations?.length > 0 && (
          <div style={{ padding: '0 18px 18px' }}>
            <div style={{ borderTop: '1px solid #4f46e520', paddingTop: 14, marginBottom: 12 }}>
              <div style={{ fontSize: 10, fontWeight: 700, color: '#64748b', letterSpacing: '0.1em', textTransform: 'uppercase', marginBottom: 10 }}>
                Drawn from
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                {answer.citations.map((c, i) => {
                  const colors = getColors(c.tradition || '')
                  const icon = getIcon(c.tradition || '')
                  return (
                    <div key={i} style={{
                      background: `${colors.bg}80`,
                      border: `1px solid ${colors.accent}25`,
                      borderRadius: 12, padding: '12px 14px',
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                        <span style={{ fontSize: 16 }}>{icon}</span>
                        <div>
                          <span style={{ fontSize: 13, fontWeight: 700, color: '#f1f5f9' }}>{c.master}</span>
                          {c.source && (
                            <span style={{ fontSize: 11, color: colors.text, marginLeft: 6 }}>· {c.source}</span>
                          )}
                        </div>
                      </div>
                      {c.quote && (
                        <div style={{ fontSize: 12, color: '#94a3b8', fontStyle: 'italic', lineHeight: 1.5 }}>
                          "{c.quote.length > 120 ? c.quote.slice(0, 120) + '…' : c.quote}"
                        </div>
                      )}
                    </div>
                  )
                })}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

// ── Master Chip ────────────────────────────────────────────────────────────────
function MasterChip({ master }) {
  const colors = getColors(master.tradition)
  const icon = getIcon(master.tradition)
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 12,
      background: `${colors.bg}80`, border: `1px solid ${colors.accent}20`,
      borderRadius: 12, padding: '10px 14px',
    }}>
      <span style={{ fontSize: 20, flexShrink: 0 }}>{icon}</span>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: 13, fontWeight: 700, color: '#e2e8f0' }}>{master.master}</div>
        <div style={{ fontSize: 11, color: colors.text }}>
          {master.tradition}{master.era ? ` · ${master.era}` : ''}
        </div>
      </div>
      <div style={{
        fontSize: 10, fontWeight: 700, color: colors.accent,
        background: colors.pill, borderRadius: 20, padding: '3px 10px', flexShrink: 0,
      }}>
        {master.count} teachings
      </div>
    </div>
  )
}
