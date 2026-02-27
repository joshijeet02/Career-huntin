import { useState } from 'react'
import { api } from '../api/client'

const EMOJIS = ['😴','😔','😐','🙂','😊','😄','🚀','⚡','🔥','💎']

export default function CheckIn({ uid }) {
  const [energy, setEnergy] = useState(6)
  const [mood, setMood] = useState('')
  const [sleep, setSleep] = useState('')
  const [wins, setWins] = useState('')
  const [blockers, setBlockers] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [done, setDone] = useState(null)
  const [error, setError] = useState('')

  const submit = async () => {
    setSubmitting(true)
    setError('')
    try {
      const result = await api.checkin.submit(
        uid, energy, mood, sleep ? parseFloat(sleep) : null,
        wins ? [wins] : [], blockers ? [blockers] : []
      )
      setDone(result)
    } catch (e) {
      setError(e.message || 'Could not save check-in.')
    } finally {
      setSubmitting(false)
    }
  }

  if (done) {
    return (
      <div className="p-5">
        <div style={{ textAlign: 'center', paddingTop: 40 }}>
          <div style={{ fontSize: 56, marginBottom: 16 }}>{EMOJIS[energy - 1]}</div>
          <div style={{ fontSize: 22, fontWeight: 700, marginBottom: 8 }}>Checked in</div>
          <div className="hint">Energy: {energy}/10</div>
        </div>
        {done.coach_message && (
          <div className="card mt-5">
            <div className="label">Your coach</div>
            <div style={{ fontSize: 15, lineHeight: 1.6, marginTop: 8, whiteSpace: 'pre-wrap' }}>
              {done.coach_message}
            </div>
          </div>
        )}
        <button className="btn btn-secondary mt-5" onClick={() => setDone(null)}>
          Check in again
        </button>
      </div>
    )
  }

  return (
    <div className="p-5">
      <div style={{ fontSize: 24, fontWeight: 700, marginBottom: 4 }}>Daily Check-in</div>
      <div className="hint mb-4">How are you showing up today?</div>

      {/* Energy slider */}
      <div className="card mb-4">
        <div className="label">Energy level</div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 8 }}>
          <span style={{ fontSize: 32 }}>{EMOJIS[energy - 1]}</span>
          <div style={{ flex: 1 }}>
            <input
              type="range" min="1" max="10" value={energy}
              onChange={e => setEnergy(Number(e.target.value))}
            />
          </div>
          <span style={{ fontSize: 22, fontWeight: 700, minWidth: 28, textAlign: 'right' }}>{energy}</span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <span className="hint">Drained</span>
          <span className="hint">On fire</span>
        </div>
      </div>

      {/* Mood note */}
      <div className="mb-4">
        <label className="label">What's on your mind?</label>
        <textarea
          className="input"
          placeholder="A one-liner about how you're feeling or what's occupying your head…"
          value={mood}
          onChange={e => setMood(e.target.value)}
          style={{ minHeight: 72 }}
        />
      </div>

      {/* Sleep */}
      <div className="mb-4">
        <label className="label">Sleep last night (hours)</label>
        <input
          className="input"
          type="number" min="0" max="24" step="0.5"
          placeholder="7.5"
          value={sleep}
          onChange={e => setSleep(e.target.value)}
        />
      </div>

      {/* Wins */}
      <div className="mb-4">
        <label className="label">One win from yesterday</label>
        <input
          className="input"
          type="text"
          placeholder="Even small counts…"
          value={wins}
          onChange={e => setWins(e.target.value)}
        />
      </div>

      {/* Blockers */}
      <div className="mb-4">
        <label className="label">What might slow you down today?</label>
        <input
          className="input"
          type="text"
          placeholder="Optional — name the friction"
          value={blockers}
          onChange={e => setBlockers(e.target.value)}
        />
      </div>

      {error && <div className="error mb-3">{error}</div>}

      <button className="btn btn-primary" onClick={submit} disabled={submitting}>
        {submitting ? <div className="spinner" style={{ width: 18, height: 18, borderWidth: 2 }} /> : 'Submit check-in'}
      </button>
    </div>
  )
}
