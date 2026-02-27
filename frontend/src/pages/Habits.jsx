import { useState, useEffect } from 'react'
import { api } from '../api/client'

export default function Habits({ uid }) {
  const [habits, setHabits] = useState([])
  const [loading, setLoading] = useState(true)
  const [showAdd, setShowAdd] = useState(false)
  const [name, setName] = useState('')
  const [track, setTrack] = useState('general')
  const [saving, setSaving] = useState(false)
  const [completing, setCompleting] = useState(null)

  const load = async () => {
    try {
      const data = await api.habits.list(uid)
      setHabits(data.habits || [])
    } catch { setHabits([]) }
    finally { setLoading(false) }
  }

  useEffect(() => { load() }, [])

  const addHabit = async () => {
    if (!name.trim()) return
    setSaving(true)
    try {
      await api.habits.add(uid, name.trim(), track, 'daily')
      setName(''); setTrack('general'); setShowAdd(false)
      load()
    } catch (e) { alert(e.message) }
    finally { setSaving(false) }
  }

  const complete = async (habit_id) => {
    setCompleting(habit_id)
    try {
      await api.habits.complete(uid, habit_id, '')
      load()
    } catch (e) { alert(e.message) }
    finally { setCompleting(null) }
  }

  if (loading) return <div className="splash"><div className="spinner" /></div>

  return (
    <div className="p-5">
      <div className="section-header">
        <div style={{ fontSize: 24, fontWeight: 700 }}>Habits</div>
        <button className="btn btn-primary btn-sm" style={{ width: 'auto' }} onClick={() => setShowAdd(v => !v)}>
          {showAdd ? 'Cancel' : '+ Add'}
        </button>
      </div>

      {showAdd && (
        <div className="card mb-4">
          <div className="label">New habit</div>
          <input
            className="input mt-2"
            placeholder="e.g. 15-min deep work block"
            value={name}
            onChange={e => setName(e.target.value)}
            autoFocus
          />
          <div className="mt-3">
            <div className="label">Track</div>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 8 }}>
              {['general','leadership','relationship','wellbeing'].map(t => (
                <button
                  key={t}
                  className={`pill ${track === t ? 'pill-accent' : ''}`}
                  style={{ cursor: 'pointer', background: track === t ? undefined : 'var(--bg3)', border: 'none', color: track === t ? undefined : 'var(--text2)', padding: '6px 14px', fontSize: 13 }}
                  onClick={() => setTrack(t)}
                >{t}</button>
              ))}
            </div>
          </div>
          <button className="btn btn-primary mt-4" onClick={addHabit} disabled={saving || !name.trim()}>
            {saving ? 'Saving…' : 'Add habit'}
          </button>
        </div>
      )}

      {habits.length === 0 ? (
        <div className="card" style={{ textAlign: 'center', padding: '40px 24px' }}>
          <div style={{ fontSize: 36, marginBottom: 12 }}>🌱</div>
          <div style={{ fontWeight: 600, marginBottom: 8 }}>No habits yet</div>
          <div className="hint">Add your first keystone habit to start tracking.</div>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {habits.map(h => (
            <HabitCard key={h.id} habit={h} onComplete={() => complete(h.id)} completing={completing === h.id} />
          ))}
        </div>
      )}
    </div>
  )
}

function HabitCard({ habit, onComplete, completing }) {
  const pct = habit.completion_rate_7d ?? 0
  const completedToday = habit.completed_today

  return (
    <div className="card-sm" style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
      <button
        onClick={onComplete}
        disabled={completedToday || completing}
        style={{
          width: 40, height: 40, borderRadius: 20, flexShrink: 0,
          background: completedToday ? 'var(--success)' : 'var(--bg3)',
          border: completedToday ? 'none' : '2px solid var(--border)',
          cursor: completedToday ? 'default' : 'pointer',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 18, transition: 'all 0.15s',
        }}
      >
        {completing ? '…' : completedToday ? '✓' : ''}
      </button>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontWeight: 600, fontSize: 15, marginBottom: 4, textDecoration: completedToday ? 'line-through' : 'none', color: completedToday ? 'var(--text3)' : 'var(--text)' }}>
          {habit.name}
        </div>
        <div className="habit-bar">
          <div className="habit-bar-fill" style={{ width: `${pct}%` }} />
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 4 }}>
          <span className="hint">{habit.track}</span>
          <span className="hint">{pct}% this week</span>
        </div>
      </div>
    </div>
  )
}
