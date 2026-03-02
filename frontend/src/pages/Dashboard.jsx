import { useState, useEffect } from 'react'
import { api } from '../api/client'

export default function Dashboard({ uid, onTabChange }) {
  const [profile, setProfile] = useState(null)
  const [firstRead, setFirstRead] = useState(null)
  const [memorySummary, setMemorySummary] = useState(null)
  const [openCommitments, setOpenCommitments] = useState(null)
  const [loading, setLoading] = useState(true)
  const [showFirstRead, setShowFirstRead] = useState(false)
  const [showProfile, setShowProfile] = useState(false)

  useEffect(() => {
    Promise.allSettled([
      api.profile.get(uid),
      api.coach.firstRead(uid),
      api.coach.memorySummary(uid),
      api.commitments.open(uid),
    ]).then(([prof, fr, mem, comm]) => {
      if (prof.status === 'fulfilled') setProfile(prof.value)
      if (fr.status === 'fulfilled') setFirstRead(fr.value)
      if (mem.status === 'fulfilled') setMemorySummary(mem.value)
      if (comm.status === 'fulfilled') setOpenCommitments(comm.value)
      setLoading(false)
    })
  }, [uid])

  const markFirstReadDelivered = async () => {
    setShowFirstRead(true)
    if (firstRead && !firstRead.delivered) {
      await api.coach.markFirstReadDelivered(uid).catch(() => {})
    }
  }

  if (loading) return <div className="splash"><div className="spinner" /></div>

  const name = profile?.full_name?.split(' ')[0] || 'there'
  const richness = memorySummary?.memory_richness || 'early'
  const richnessColor = { early: 'var(--text3)', developing: 'var(--warning)', established: 'var(--accent2)', deep: 'var(--success)' }[richness] || 'var(--text3)'

  return (
    <div className="p-5">
      {/* Greeting */}
      <div style={{ marginBottom: 20 }}>
        <div style={{ fontSize: 26, fontWeight: 700, lineHeight: 1.2 }}>
          {getGreeting()}, {name}
        </div>
        <div className="hint mt-1">
          {memorySummary ? (
            <>Coach memory: <span style={{ color: richnessColor, fontWeight: 600 }}>{richness}</span></>
          ) : 'Your personal coaching OS'}
        </div>
      </div>

      {/* First Read card — the hero card */}
      {firstRead && firstRead.full_text && (
        <div
          className="card mb-4"
          style={{ background: 'linear-gradient(135deg, #1e1b4b 0%, #312e81 100%)', border: '1px solid #4f46e5', cursor: 'pointer' }}
          onClick={markFirstReadDelivered}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 10 }}>
            <div>
              <div style={{ fontSize: 11, fontWeight: 700, color: '#a5b4fc', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 4 }}>
                Your First Read
              </div>
              <div style={{ fontSize: 17, fontWeight: 700 }}>What your coach sees</div>
            </div>
            <span style={{ fontSize: 24 }}>🔮</span>
          </div>
          <div style={{ fontSize: 14, color: '#c7d2fe', lineHeight: 1.5, marginBottom: 12 }}>
            {firstRead.one_sentence || 'A deep personality synthesis based on your intake.'}
          </div>
          <div style={{ fontSize: 13, color: '#818cf8', fontWeight: 600 }}>
            Tap to read your full synthesis →
          </div>
        </div>
      )}

      {/* First Read modal */}
      {showFirstRead && firstRead && (
        <FirstReadModal text={firstRead.full_text} onClose={() => setShowFirstRead(false)} />
      )}

      {/* Memory stats */}
      {memorySummary && (
        <div className="card mb-4">
          <div className="label" style={{ marginBottom: 12 }}>What your coach knows</div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            <StatBox label="Check-ins (14d)" value={memorySummary.recent_checkins_14d} />
            <StatBox label="Active habits" value={memorySummary.active_habits} />
            <StatBox label="Open commitments" value={memorySummary.open_commitments} />
            <StatBox label="Days with coach" value={memorySummary.days_since_onboarding} />
          </div>
        </div>
      )}

      {/* Open commitments */}
      {openCommitments && (openCommitments.overdue?.length > 0 || openCommitments.due_today?.length > 0) && (
        <div className="card mb-4">
          <div className="label" style={{ marginBottom: 10 }}>Commitments</div>

          {openCommitments.overdue?.length > 0 && (
            <div style={{ marginBottom: 8 }}>
              {openCommitments.overdue.slice(0, 2).map((c, i) => (
                <div key={i} className="card-sm mb-2" style={{ borderColor: 'rgba(239,68,68,0.3)', background: 'rgba(239,68,68,0.05)' }}>
                  <div style={{ display: 'flex', gap: 8, alignItems: 'flex-start' }}>
                    <span className="pill pill-danger" style={{ flexShrink: 0 }}>Overdue</span>
                    <div style={{ fontSize: 13, lineHeight: 1.4 }}>{c.commitment_text}</div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {openCommitments.due_today?.length > 0 && openCommitments.due_today.slice(0, 2).map((c, i) => (
            <div key={i} className="card-sm mb-2" style={{ borderColor: 'rgba(245,158,11,0.3)' }}>
              <div style={{ display: 'flex', gap: 8, alignItems: 'flex-start' }}>
                <span className="pill pill-warning" style={{ flexShrink: 0 }}>Today</span>
                <div style={{ fontSize: 13, lineHeight: 1.4 }}>{c.commitment_text}</div>
              </div>
            </div>
          ))}

          {openCommitments.coach_accountability_note && (
            <div className="hint mt-2" style={{ fontStyle: 'italic' }}>
              {openCommitments.coach_accountability_note}
            </div>
          )}
        </div>
      )}

      {/* Your Profile summary card */}
      {profile && profile.profile_summary && (
        <div
          className="card mb-4"
          style={{ background: 'linear-gradient(135deg, #0f2027 0%, #203a43 60%, #2c5364 100%)', border: '1px solid rgba(255,255,255,0.1)', cursor: 'pointer' }}
          onClick={() => setShowProfile(true)}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
            <div>
              <div style={{ fontSize: 11, fontWeight: 700, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 4 }}>
                Your Profile
              </div>
              <div style={{ fontSize: 16, fontWeight: 700 }}>{profile.full_name}</div>
              <div style={{ fontSize: 13, color: '#94a3b8', marginTop: 2 }}>{profile.role}{profile.organization ? ` · ${profile.organization}` : ''}</div>
            </div>
            <span style={{ fontSize: 22 }}>🪞</span>
          </div>
          {profile.core_values?.length > 0 && (
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 10 }}>
              {profile.core_values.slice(0, 4).map((v, i) => (
                <span key={i} style={{ fontSize: 11, background: 'rgba(255,255,255,0.1)', borderRadius: 20, padding: '3px 10px', color: '#cbd5e1' }}>{v}</span>
              ))}
            </div>
          )}
          <div style={{ fontSize: 12, color: '#64748b', marginTop: 10, fontWeight: 600 }}>
            Tap to read your coaching profile →
          </div>
        </div>
      )}

      {/* Profile modal */}
      {showProfile && profile && (
        <ProfileModal profile={profile} onClose={() => setShowProfile(false)} />
      )}

      {/* Quick actions */}
      <div className="label mb-3">Quick actions</div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
        <QuickCard emoji="🧘" label="Morning brief" hint="Coach's briefing" onClick={() => onTabChange && onTabChange('coach')} />
        <QuickCard emoji="📝" label="Reflection" hint="End of week" onClick={() => onTabChange && onTabChange('checkin')} />
        <QuickCard emoji="🎯" label="Sprint board" hint="90-day goals" onClick={() => onTabChange && onTabChange('coach')} />
        <QuickCard emoji="📊" label="Energy insight" hint="Your patterns" onClick={() => onTabChange && onTabChange('checkin')} />
      </div>
    </div>
  )
}

function StatBox({ label, value }) {
  return (
    <div style={{ background: 'var(--bg3)', borderRadius: 10, padding: '12px 14px' }}>
      <div style={{ fontSize: 24, fontWeight: 700, color: 'var(--accent2)' }}>{value ?? '—'}</div>
      <div style={{ fontSize: 11, color: 'var(--text3)', marginTop: 2 }}>{label}</div>
    </div>
  )
}

function QuickCard({ emoji, label, hint, onClick }) {
  return (
    <div className="card-sm" style={{ cursor: 'pointer' }} onClick={onClick}>
      <div style={{ fontSize: 24, marginBottom: 6 }}>{emoji}</div>
      <div style={{ fontWeight: 600, fontSize: 14 }}>{label}</div>
      <div className="hint" style={{ fontSize: 11, marginTop: 2 }}>{hint}</div>
    </div>
  )
}

function ProfileModal({ profile, onClose }) {
  return (
    <div style={{
      position: 'fixed', inset: 0, zIndex: 200,
      background: 'rgba(0,0,0,0.9)', display: 'flex', flexDirection: 'column',
      maxWidth: 430, margin: '0 auto',
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '20px 20px 0', paddingTop: 'calc(var(--safe-top) + 20px)' }}>
        <div style={{ fontWeight: 700, fontSize: 18 }}>Your Coaching Profile</div>
        <button onClick={onClose} style={{ background: 'var(--bg3)', border: 'none', color: 'var(--text)', borderRadius: 20, width: 36, height: 36, cursor: 'pointer', fontSize: 18 }}>×</button>
      </div>
      <div style={{ flex: 1, overflowY: 'auto', padding: '20px', WebkitOverflowScrolling: 'touch' }}>
        {/* Summary text — the one they loved */}
        {profile.profile_summary && (
          <div style={{ fontSize: 15, lineHeight: 1.8, color: 'var(--text)', whiteSpace: 'pre-wrap', fontFamily: 'Georgia, serif', marginBottom: 24 }}>
            {profile.profile_summary}
          </div>
        )}
        {/* Goals */}
        {profile.goals_90_days?.length > 0 && (
          <div style={{ marginBottom: 20 }}>
            <div className="label" style={{ marginBottom: 10 }}>90-Day Goals</div>
            {profile.goals_90_days.map((g, i) => (
              <div key={i} style={{ background: 'var(--bg3)', borderRadius: 10, padding: '10px 14px', marginBottom: 8 }}>
                <div style={{ fontSize: 13, lineHeight: 1.5 }}>{g.goal || g}</div>
                {g.track && <div style={{ fontSize: 11, color: 'var(--accent2)', marginTop: 4, textTransform: 'uppercase', fontWeight: 600 }}>{g.track}</div>}
              </div>
            ))}
          </div>
        )}
        {/* Core values */}
        {profile.core_values?.length > 0 && (
          <div style={{ marginBottom: 20 }}>
            <div className="label" style={{ marginBottom: 10 }}>Core Values</div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
              {profile.core_values.map((v, i) => (
                <span key={i} style={{ fontSize: 13, background: 'var(--bg3)', borderRadius: 20, padding: '6px 14px', color: 'var(--text)' }}>{v}</span>
              ))}
            </div>
          </div>
        )}
        {/* Coaching style */}
        {profile.coaching_style_preference && (
          <div style={{ marginBottom: 20 }}>
            <div className="label" style={{ marginBottom: 8 }}>Coaching Style</div>
            <div style={{ background: 'var(--bg3)', borderRadius: 10, padding: '10px 14px', fontSize: 14 }}>
              {profile.coaching_style_preference.charAt(0).toUpperCase() + profile.coaching_style_preference.slice(1)}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

function FirstReadModal({ text, onClose }) {
  return (
    <div style={{
      position: 'fixed', inset: 0, zIndex: 200,
      background: 'rgba(0,0,0,0.85)', display: 'flex', flexDirection: 'column',
      maxWidth: 430, margin: '0 auto',
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '20px 20px 0', paddingTop: 'calc(var(--safe-top) + 20px)' }}>
        <div style={{ fontWeight: 700, fontSize: 18 }}>Your First Read</div>
        <button onClick={onClose} style={{ background: 'var(--bg3)', border: 'none', color: 'var(--text)', borderRadius: 20, width: 36, height: 36, cursor: 'pointer', fontSize: 18 }}>×</button>
      </div>
      <div style={{ flex: 1, overflowY: 'auto', padding: '20px', WebkitOverflowScrolling: 'touch' }}>
        <div style={{ fontSize: 15, lineHeight: 1.8, color: 'var(--text)', whiteSpace: 'pre-wrap', fontFamily: 'Georgia, serif' }}>
          {text}
        </div>
      </div>
    </div>
  )
}

function getGreeting() {
  const h = new Date().getHours()
  if (h < 12) return 'Good morning'
  if (h < 17) return 'Good afternoon'
  return 'Good evening'
}
