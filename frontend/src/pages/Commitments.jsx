import { useState, useEffect } from 'react'
import { api } from '../api/client'

const STATUS_OPTIONS = [
  { value: 'kept', label: '✅ Kept', color: 'var(--success)' },
  { value: 'partial', label: '🟡 Partial', color: 'var(--warning)' },
  { value: 'missed', label: '❌ Missed', color: '#ef4444' },
  { value: 'deferred', label: '⏩ Deferred', color: 'var(--text3)' },
]

export default function Commitments({ uid }) {
  const [open, setOpen] = useState(null)
  const [loading, setLoading] = useState(true)
  const [showAdd, setShowAdd] = useState(false)
  const [checkingIn, setCheckingIn] = useState(null)  // commitment being checked in
  const [text, setText] = useState('')
  const [dueDate, setDueDate] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const load = async () => {
    setLoading(true)
    try {
      const data = await api.commitments.open(uid)
      setOpen(data)
    } catch { setOpen(null) }
    finally { setLoading(false) }
  }

  useEffect(() => { load() }, [uid])

  const addCommitment = async () => {
    if (!text.trim()) return
    setSaving(true)
    setError('')
    try {
      await api.commitments.create(uid, text.trim(), dueDate || null)
      setText(''); setDueDate(''); setShowAdd(false)
      load()
    } catch (e) {
      setError(e.message || 'Could not save commitment.')
    } finally { setSaving(false) }
  }

  const doCheckIn = async (commitmentId, status, note = '') => {
    try {
      await api.commitments.checkin(uid, commitmentId, status, note)
      setCheckingIn(null)
      load()
    } catch (e) {
      alert(e.message || 'Could not update commitment.')
    }
  }

  if (loading) return <div className="splash"><div className="spinner" /></div>

  const overdueItems = open?.overdue || []
  const todayItems = open?.due_today || []
  const upcomingItems = open?.upcoming_7_days || []
  const total = overdueItems.length + todayItems.length + upcomingItems.length

  return (
    <div className="p-5">
      <div className="section-header">
        <div>
          <div style={{ fontSize: 24, fontWeight: 700 }}>Commitments</div>
          <div className="hint">{total} open</div>
        </div>
        <button className="btn btn-primary btn-sm" style={{ width: 'auto' }} onClick={() => setShowAdd(v => !v)}>
          {showAdd ? 'Cancel' : '+ Add'}
        </button>
      </div>

      {/* Add form */}
      {showAdd && (
        <div className="card mb-4">
          <div className="label" style={{ marginBottom: 8 }}>New commitment</div>
          <textarea
            className="input"
            placeholder="What are you committing to? Be specific."
            value={text}
            onChange={e => setText(e.target.value)}
            style={{ minHeight: 80 }}
            autoFocus
          />
          <div className="mt-3">
            <label className="label">Due date (optional)</label>
            <input
              className="input mt-1"
              type="date"
              value={dueDate}
              onChange={e => setDueDate(e.target.value)}
            />
          </div>
          {error && <div className="error mt-2">{error}</div>}
          <button className="btn btn-primary mt-4" onClick={addCommitment} disabled={saving || !text.trim()}>
            {saving ? 'Saving…' : 'Add commitment'}
          </button>
        </div>
      )}

      {/* Coach note */}
      {open?.coach_accountability_note && (
        <div className="card mb-4" style={{ borderColor: 'rgba(99,102,241,0.3)', background: 'rgba(99,102,241,0.05)' }}>
          <div style={{ fontSize: 13, color: '#a5b4fc', lineHeight: 1.6, fontStyle: 'italic' }}>
            🧠 {open.coach_accountability_note}
          </div>
        </div>
      )}

      {/* Overdue */}
      {overdueItems.length > 0 && (
        <Section title="Overdue" color="#ef4444" items={overdueItems} onCheckIn={setCheckingIn} />
      )}

      {/* Due today */}
      {todayItems.length > 0 && (
        <Section title="Due today" color="var(--warning)" items={todayItems} onCheckIn={setCheckingIn} />
      )}

      {/* Upcoming */}
      {upcomingItems.length > 0 && (
        <Section title="Upcoming" color="var(--text3)" items={upcomingItems} onCheckIn={setCheckingIn} />
      )}

      {total === 0 && !showAdd && (
        <div className="card" style={{ textAlign: 'center', padding: '40px 24px' }}>
          <div style={{ fontSize: 36, marginBottom: 12 }}>🤝</div>
          <div style={{ fontWeight: 600, marginBottom: 8 }}>No open commitments</div>
          <div className="hint">Add something you're committing to and hold yourself accountable.</div>
        </div>
      )}

      {/* Check-in modal */}
      {checkingIn && (
        <CheckInModal
          commitment={checkingIn}
          onSubmit={(status, note) => doCheckIn(checkingIn.id, status, note)}
          onClose={() => setCheckingIn(null)}
        />
      )}
    </div>
  )
}

function Section({ title, color, items, onCheckIn }) {
  return (
    <div style={{ marginBottom: 20 }}>
      <div style={{ fontSize: 11, fontWeight: 700, color, textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 10 }}>
        {title}
      </div>
      {items.map((c, i) => (
        <CommitmentCard key={c.id || i} commitment={c} onCheckIn={() => onCheckIn(c)} />
      ))}
    </div>
  )
}

function CommitmentCard({ commitment: c, onCheckIn }) {
  return (
    <div className="card-sm mb-3" style={{ display: 'flex', gap: 12, alignItems: 'flex-start' }}>
      <div style={{ flex: 1 }}>
        <div style={{ fontSize: 14, lineHeight: 1.5, fontWeight: 500, marginBottom: 4 }}>
          {c.commitment_text}
        </div>
        {c.due_date && (
          <div className="hint" style={{ fontSize: 11 }}>Due: {c.due_date}</div>
        )}
      </div>
      <button
        onClick={onCheckIn}
        style={{
          flexShrink: 0, fontSize: 12, fontWeight: 600, padding: '6px 12px',
          background: 'var(--bg3)', border: '1px solid var(--border)',
          borderRadius: 8, color: 'var(--text2)', cursor: 'pointer',
        }}
      >
        Update
      </button>
    </div>
  )
}

function CheckInModal({ commitment, onSubmit, onClose }) {
  const [status, setStatus] = useState('')
  const [note, setNote] = useState('')
  const [saving, setSaving] = useState(false)

  const submit = async () => {
    if (!status) return
    setSaving(true)
    await onSubmit(status, note)
    setSaving(false)
  }

  return (
    <div style={{
      position: 'fixed', inset: 0, zIndex: 200, background: 'rgba(0,0,0,0.85)',
      display: 'flex', alignItems: 'flex-end', maxWidth: 430, margin: '0 auto',
    }}>
      <div style={{ background: 'var(--bg2)', borderRadius: '20px 20px 0 0', padding: '24px 20px', width: '100%', paddingBottom: 'calc(24px + env(safe-area-inset-bottom))' }}>
        <div style={{ fontWeight: 700, fontSize: 16, marginBottom: 6 }}>Check in on commitment</div>
        <div style={{ fontSize: 13, color: 'var(--text3)', marginBottom: 20, lineHeight: 1.5 }}>
          {commitment.commitment_text}
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginBottom: 16 }}>
          {STATUS_OPTIONS.map(opt => (
            <button
              key={opt.value}
              onClick={() => setStatus(opt.value)}
              style={{
                padding: '12px 8px', borderRadius: 12, fontWeight: 600, fontSize: 13, cursor: 'pointer',
                border: status === opt.value ? `2px solid ${opt.color}` : '2px solid var(--border)',
                background: status === opt.value ? `${opt.color}20` : 'var(--bg3)',
                color: status === opt.value ? opt.color : 'var(--text2)',
              }}
            >
              {opt.label}
            </button>
          ))}
        </div>

        <textarea
          className="input"
          placeholder="Add a note (optional)…"
          value={note}
          onChange={e => setNote(e.target.value)}
          style={{ minHeight: 64, marginBottom: 16 }}
        />

        <div style={{ display: 'flex', gap: 10 }}>
          <button className="btn btn-primary" onClick={submit} disabled={saving || !status} style={{ flex: 1 }}>
            {saving ? 'Saving…' : 'Submit'}
          </button>
          <button className="btn btn-secondary" onClick={onClose} style={{ width: 'auto', padding: '0 20px' }}>
            Cancel
          </button>
        </div>
      </div>
    </div>
  )
}
