import { useState, useEffect } from 'react'
import { api } from '../api/client'

export default function Dashboard({ uid, onTabChange }) {
  const [profile, setProfile]                   = useState(null)
  const [firstRead, setFirstRead]               = useState(null)
  const [memorySummary, setMemorySummary]       = useState(null)
  const [openCommitments, setOpenCommitments]   = useState(null)
  const [dailyWisdom, setDailyWisdom]           = useState(null)
  const [loading, setLoading]                   = useState(true)
  const [showFirstRead, setShowFirstRead]       = useState(false)
  const [showProfile, setShowProfile]           = useState(false)
  const [morningBrief, setMorningBrief]         = useState(null)
  const [morningBriefLoading, setMBLoading]     = useState(false)
  const [showMorningBrief, setShowMorningBrief] = useState(false)

  useEffect(() => {
    Promise.allSettled([
      api.profile.get(uid),
      api.coach.firstRead(uid),
      api.coach.memorySummary(uid),
      api.commitments.open(uid),
      api.wisdom.daily(uid),
    ]).then(([prof, fr, mem, comm, wis]) => {
      if (prof.status === 'fulfilled') setProfile(prof.value)
      if (fr.status   === 'fulfilled') setFirstRead(fr.value)
      if (mem.status  === 'fulfilled') setMemorySummary(mem.value)
      if (comm.status === 'fulfilled') setOpenCommitments(comm.value)
      if (wis.status  === 'fulfilled') setDailyWisdom(wis.value?.wisdom || null)
      setLoading(false)
    })
  }, [uid])

  const markFirstReadDelivered = async () => {
    setShowFirstRead(true)
    if (firstRead && !firstRead.delivered) {
      await api.coach.markFirstReadDelivered(uid).catch(() => {})
    }
  }

  const openMorningBrief = async () => {
    setShowMorningBrief(true)
    if (morningBrief) return
    setMBLoading(true)
    try {
      const data = await api.coach.respond(uid, 'morning_brief', '', 'general')
      setMorningBrief(data?.response || data?.message || 'Your coach is preparing your brief…')
    } catch {
      setMorningBrief('Could not load morning brief. Try opening the Coach tab.')
    } finally {
      setMBLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="splash">
        <div style={{ fontFamily: 'var(--font-serif)', fontSize: 28, color: 'var(--gold)', fontStyle: 'italic', marginBottom: 8 }}>
          Your Council awaits
        </div>
        <div className="spinner" />
      </div>
    )
  }

  const name    = profile?.full_name?.split(' ')[0] || 'there'
  const richness = memorySummary?.memory_richness || 'early'
  const richnessColor = {
    early: 'var(--text3)', developing: 'var(--warning)',
    established: 'var(--gold2)', deep: 'var(--success)',
  }[richness] || 'var(--text3)'

  return (
    <div style={{ padding: '4px 20px 20px' }}>

      {/* ── Greeting ─────────────────────────────────────────────────────── */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 28, paddingTop: 8 }}>
        <div>
          <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--gold)', textTransform: 'uppercase', letterSpacing: '0.12em', marginBottom: 4 }}>
            {getGreeting()}
          </div>
          <div style={{
            fontFamily: 'var(--font-serif)', fontSize: 34, fontWeight: 600,
            lineHeight: 1.1, color: 'var(--text1)', letterSpacing: '-0.01em',
          }}>
            {name}
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 6 }}>
            <div className="gold-line" />
            <div style={{ fontSize: 12, color: 'var(--text3)' }}>
              {memorySummary
                ? <>Memory depth: <span style={{ color: richnessColor, fontWeight: 600 }}>{richness}</span></>
                : 'Your personal coaching council'}
            </div>
          </div>
        </div>
        <button
          onClick={() => onTabChange && onTabChange('settings')}
          style={{
            background: 'rgba(201,168,76,0.08)',
            border: '1px solid var(--gold-border)',
            color: 'var(--text3)',
            borderRadius: '50%',
            width: 38, height: 38,
            cursor: 'pointer',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            flexShrink: 0, marginTop: 6, fontSize: 16,
            transition: 'all 0.2s',
          }}
        >
          ⚙️
        </button>
      </div>

      {/* ── First Read — hero card ────────────────────────────────────────── */}
      {firstRead && firstRead.full_text && (
        <div
          onClick={markFirstReadDelivered}
          style={{
            background: 'linear-gradient(145deg, rgba(201,168,76,0.12) 0%, rgba(168,126,46,0.06) 100%)',
            border: '1px solid rgba(201,168,76,0.28)',
            borderRadius: 20,
            padding: '22px',
            marginBottom: 16,
            cursor: 'pointer',
            boxShadow: '0 0 40px rgba(201,168,76,0.06) inset, 0 12px 40px rgba(0,0,0,0.4)',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 }}>
            <div>
              <div style={{ fontSize: 10, fontWeight: 700, color: 'var(--gold)', textTransform: 'uppercase', letterSpacing: '0.14em', marginBottom: 6 }}>
                Your First Read
              </div>
              <div style={{ fontFamily: 'var(--font-serif)', fontSize: 22, fontWeight: 600, lineHeight: 1.2 }}>
                What your coach sees
              </div>
            </div>
            <div style={{ fontSize: 28, opacity: 0.8 }}>🔮</div>
          </div>
          <div style={{ fontSize: 14, color: 'var(--text2)', lineHeight: 1.65, marginBottom: 14, fontStyle: 'italic', fontFamily: 'var(--font-serif)' }}>
            {firstRead.one_sentence || 'A deep personality synthesis based on your intake.'}
          </div>
          <div style={{ fontSize: 12, color: 'var(--gold)', fontWeight: 600, letterSpacing: '0.04em' }}>
            Read your full synthesis →
          </div>
        </div>
      )}

      {showFirstRead && firstRead && (
        <FirstReadModal text={firstRead.full_text} onClose={() => setShowFirstRead(false)} />
      )}

      {/* ── Memory stats ─────────────────────────────────────────────────── */}
      {memorySummary && (
        <div className="card" style={{ marginBottom: 16 }}>
          <div className="section-title" style={{ marginBottom: 14 }}>What your Council knows</div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
            <StatBox label="Check-ins (14d)"    value={memorySummary.recent_checkins_14d} />
            <StatBox label="Active habits"       value={memorySummary.active_habits} />
            <StatBox label="Open commitments"    value={memorySummary.open_commitments} />
            <StatBox label="Days with coach"     value={memorySummary.days_since_onboarding} />
          </div>
        </div>
      )}

      {/* ── Open commitments ─────────────────────────────────────────────── */}
      {openCommitments && (openCommitments.overdue?.length > 0 || openCommitments.due_today?.length > 0) && (
        <div className="card" style={{ marginBottom: 16 }}>
          <div className="section-title" style={{ marginBottom: 12 }}>Commitments</div>

          {openCommitments.overdue?.slice(0, 2).map((c, i) => (
            <div key={i} className="card-sm" style={{ marginBottom: 8, borderColor: 'rgba(248,113,113,0.25)', background: 'rgba(248,113,113,0.04)' }}>
              <div style={{ display: 'flex', gap: 8, alignItems: 'flex-start' }}>
                <span className="pill pill-danger" style={{ flexShrink: 0 }}>Overdue</span>
                <div style={{ fontSize: 13, lineHeight: 1.5, color: 'var(--text2)' }}>{c.commitment_text}</div>
              </div>
            </div>
          ))}

          {openCommitments.due_today?.slice(0, 2).map((c, i) => (
            <div key={i} className="card-sm" style={{ marginBottom: 8, borderColor: 'rgba(251,191,36,0.2)' }}>
              <div style={{ display: 'flex', gap: 8, alignItems: 'flex-start' }}>
                <span className="pill pill-warning" style={{ flexShrink: 0 }}>Today</span>
                <div style={{ fontSize: 13, lineHeight: 1.5, color: 'var(--text2)' }}>{c.commitment_text}</div>
              </div>
            </div>
          ))}

          {openCommitments.coach_accountability_note && (
            <div className="hint" style={{ fontStyle: 'italic', marginTop: 8, paddingTop: 8, borderTop: '1px solid var(--border2)' }}>
              {openCommitments.coach_accountability_note}
            </div>
          )}
        </div>
      )}

      {/* ── Profile card ─────────────────────────────────────────────────── */}
      {profile && profile.profile_summary && (
        <div
          onClick={() => setShowProfile(true)}
          style={{
            background: 'linear-gradient(145deg, #0d1520 0%, #111f2e 100%)',
            border: '1px solid rgba(255,255,255,0.07)',
            borderRadius: 20,
            padding: '20px 22px',
            marginBottom: 16,
            cursor: 'pointer',
            boxShadow: '0 12px 40px rgba(0,0,0,0.5)',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 10 }}>
            <div>
              <div style={{ fontSize: 10, fontWeight: 700, color: 'var(--text3)', textTransform: 'uppercase', letterSpacing: '0.12em', marginBottom: 6 }}>
                Your Profile
              </div>
              <div style={{ fontFamily: 'var(--font-serif)', fontSize: 20, fontWeight: 600 }}>{profile.full_name}</div>
              <div style={{ fontSize: 12, color: 'var(--text3)', marginTop: 2 }}>
                {profile.role}{profile.organization ? ` · ${profile.organization}` : ''}
              </div>
            </div>
            <div style={{ fontSize: 22, opacity: 0.7 }}>🪞</div>
          </div>
          {profile.core_values?.length > 0 && (
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 12 }}>
              {profile.core_values.slice(0, 4).map((v, i) => (
                <span key={i} style={{
                  fontSize: 11, background: 'rgba(255,255,255,0.06)',
                  borderRadius: 20, padding: '3px 10px', color: 'var(--text3)',
                  border: '1px solid rgba(255,255,255,0.08)',
                }}>{v}</span>
              ))}
            </div>
          )}
          <div style={{ fontSize: 11, color: 'var(--text3)', marginTop: 12, fontWeight: 600, letterSpacing: '0.04em' }}>
            View coaching profile →
          </div>
        </div>
      )}

      {showProfile && profile && (
        <ProfileModal profile={profile} onClose={() => setShowProfile(false)} />
      )}

      {/* ── Quick actions ─────────────────────────────────────────────────── */}
      <div className="section-title" style={{ marginBottom: 12 }}>Your practice</div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginBottom: 16 }}>
        <QuickCard icon="☀️" label="Morning brief"  hint="Coach's note for today" onClick={openMorningBrief} />
        <QuickCard icon="📋" label="Check-in"       hint="Log your day"           onClick={() => onTabChange && onTabChange('checkin')} />
        <QuickCard icon="🤝" label="Commitments"    hint="Track your word"        onClick={() => onTabChange && onTabChange('commitments')} />
        <QuickCard icon="⚖️" label="The Council"    hint="All four voices"        onClick={() => onTabChange && onTabChange('coach')} />
      </div>

      {/* ── Today's Wisdom ───────────────────────────────────────────────── */}
      {dailyWisdom && (
        <div
          onClick={() => onTabChange && onTabChange('wisdom')}
          style={{
            background: 'linear-gradient(145deg, rgba(88,28,135,0.25) 0%, rgba(49,10,80,0.2) 100%)',
            border: '1px solid rgba(167,139,250,0.18)',
            borderRadius: 20,
            padding: '20px 22px',
            marginBottom: 16,
            cursor: 'pointer',
            boxShadow: '0 0 40px rgba(124,58,237,0.04) inset',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 10 }}>
            <div>
              <div style={{ fontSize: 10, fontWeight: 700, color: '#a78bfa', textTransform: 'uppercase', letterSpacing: '0.14em', marginBottom: 6 }}>
                Today's Wisdom
              </div>
              <div style={{ fontFamily: 'var(--font-serif)', fontSize: 18, fontWeight: 600, lineHeight: 1.2 }}>
                {dailyWisdom.master}
              </div>
              <div style={{ fontSize: 11, color: '#7c3aed', marginTop: 2 }}>{dailyWisdom.tradition}</div>
            </div>
            <div style={{ fontSize: 24, opacity: 0.8 }}>📿</div>
          </div>
          <div style={{
            fontSize: 14, color: '#c4b5fd', lineHeight: 1.7,
            fontStyle: 'italic', fontFamily: 'var(--font-serif)',
            marginBottom: 12, borderLeft: '2px solid rgba(167,139,250,0.3)',
            paddingLeft: 12,
          }}>
            "{dailyWisdom.quote.length > 120 ? dailyWisdom.quote.slice(0, 120) + '…' : dailyWisdom.quote}"
          </div>
          <div style={{ fontSize: 11, color: '#7c3aed', fontWeight: 600, letterSpacing: '0.04em' }}>
            Explore the masters →
          </div>
        </div>
      )}

      {/* ── Morning Brief modal ───────────────────────────────────────────── */}
      {showMorningBrief && (
        <MorningBriefModal
          loading={morningBriefLoading}
          text={morningBrief}
          onClose={() => setShowMorningBrief(false)}
        />
      )}
    </div>
  )
}

// ── Sub-components ────────────────────────────────────────────────────────────

function StatBox({ label, value }) {
  return (
    <div style={{
      background: 'var(--bg3)',
      border: '1px solid var(--border2)',
      borderRadius: 12,
      padding: '14px 16px',
    }}>
      <div style={{
        fontFamily: 'var(--font-serif)',
        fontSize: 32, fontWeight: 600,
        color: 'var(--gold2)',
        lineHeight: 1,
        marginBottom: 4,
      }}>
        {value ?? '—'}
      </div>
      <div style={{ fontSize: 11, color: 'var(--text3)', letterSpacing: '0.04em' }}>{label}</div>
    </div>
  )
}

function QuickCard({ icon, label, hint, onClick }) {
  return (
    <div
      onClick={onClick}
      style={{
        background: 'linear-gradient(145deg, var(--bg2), var(--bg1))',
        border: '1px solid var(--border)',
        borderRadius: 16,
        padding: '16px',
        cursor: 'pointer',
        transition: 'border-color 0.2s, transform 0.15s',
        boxShadow: '0 4px 16px rgba(0,0,0,0.25)',
      }}
      onTouchStart={e => e.currentTarget.style.transform = 'scale(0.97)'}
      onTouchEnd={e => e.currentTarget.style.transform = 'scale(1)'}
    >
      <div style={{ fontSize: 22, marginBottom: 8 }}>{icon}</div>
      <div style={{ fontWeight: 600, fontSize: 14, color: 'var(--text1)', marginBottom: 3 }}>{label}</div>
      <div style={{ fontSize: 11, color: 'var(--text3)' }}>{hint}</div>
    </div>
  )
}

function ModalShell({ title, subtitle, onClose, children, footer }) {
  return (
    <div style={{
      position: 'fixed', inset: 0, zIndex: 200,
      background: 'rgba(4,5,10,0.96)',
      display: 'flex', flexDirection: 'column',
      maxWidth: 430, margin: '0 auto',
      backdropFilter: 'blur(12px)',
    }}>
      <div style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start',
        padding: '20px 22px 0',
        paddingTop: 'calc(var(--safe-top) + 20px)',
        borderBottom: '1px solid var(--border)',
        paddingBottom: 16,
      }}>
        <div>
          <div style={{ fontFamily: 'var(--font-serif)', fontSize: 24, fontWeight: 600, lineHeight: 1.2 }}>{title}</div>
          {subtitle && <div style={{ fontSize: 12, color: 'var(--text3)', marginTop: 4 }}>{subtitle}</div>}
        </div>
        <button onClick={onClose} style={{
          background: 'var(--bg3)', border: '1px solid var(--border2)',
          color: 'var(--text2)', borderRadius: '50%',
          width: 36, height: 36, cursor: 'pointer', fontSize: 18,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          flexShrink: 0,
        }}>×</button>
      </div>
      <div style={{ flex: 1, overflowY: 'auto', padding: '24px 22px', WebkitOverflowScrolling: 'touch' }}>
        {children}
      </div>
      {footer && (
        <div style={{ padding: '16px 22px', paddingBottom: 'calc(16px + env(safe-area-inset-bottom))', borderTop: '1px solid var(--border)' }}>
          {footer}
        </div>
      )}
    </div>
  )
}

function ProfileModal({ profile, onClose }) {
  return (
    <ModalShell title={profile.full_name} subtitle="Coaching profile" onClose={onClose} footer={<button className="btn btn-ghost btn-sm" onClick={onClose}>Close</button>}>
      {profile.profile_summary && (
        <>
          <div className="gold-line" style={{ marginBottom: 16 }} />
          <div style={{ fontSize: 15, lineHeight: 1.9, color: 'var(--text2)', fontFamily: 'var(--font-serif)', marginBottom: 28, fontStyle: 'italic' }}>
            {profile.profile_summary}
          </div>
        </>
      )}
      {profile.goals_90_days?.length > 0 && (
        <div style={{ marginBottom: 24 }}>
          <div className="section-title" style={{ marginBottom: 12 }}>90-Day Goals</div>
          {profile.goals_90_days.map((g, i) => (
            <div key={i} style={{ background: 'var(--bg3)', border: '1px solid var(--border2)', borderRadius: 12, padding: '12px 16px', marginBottom: 8 }}>
              <div style={{ fontSize: 14, lineHeight: 1.55, color: 'var(--text)' }}>{g.goal || g}</div>
              {g.track && <div style={{ fontSize: 11, color: 'var(--gold)', marginTop: 6, textTransform: 'uppercase', fontWeight: 600, letterSpacing: '0.08em' }}>{g.track}</div>}
            </div>
          ))}
        </div>
      )}
      {profile.core_values?.length > 0 && (
        <div style={{ marginBottom: 24 }}>
          <div className="section-title" style={{ marginBottom: 12 }}>Core Values</div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
            {profile.core_values.map((v, i) => (
              <span key={i} style={{
                fontSize: 13, background: 'rgba(201,168,76,0.08)',
                border: '1px solid rgba(201,168,76,0.18)',
                borderRadius: 20, padding: '6px 14px', color: 'var(--gold2)',
              }}>{v}</span>
            ))}
          </div>
        </div>
      )}
      {profile.coaching_style_preference && (
        <div>
          <div className="section-title" style={{ marginBottom: 10 }}>Coaching Style</div>
          <div style={{ background: 'var(--bg3)', borderRadius: 12, padding: '12px 16px', fontSize: 14, color: 'var(--text2)' }}>
            {profile.coaching_style_preference.charAt(0).toUpperCase() + profile.coaching_style_preference.slice(1)}
          </div>
        </div>
      )}
    </ModalShell>
  )
}

function FirstReadModal({ text, onClose }) {
  return (
    <ModalShell title="Your First Read" subtitle="What your coach sees in you" onClose={onClose} footer={<button className="btn btn-primary" onClick={onClose}>Close</button>}>
      <div className="gold-line" style={{ marginBottom: 20 }} />
      <div style={{
        fontSize: 15, lineHeight: 1.9, color: 'var(--text2)',
        whiteSpace: 'pre-wrap', fontFamily: 'var(--font-serif)',
      }}>
        {text}
      </div>
    </ModalShell>
  )
}

function MorningBriefModal({ loading, text, onClose }) {
  return (
    <ModalShell title="Morning Brief" subtitle="Your coach's note for today" onClose={onClose} footer={<button className="btn btn-primary" onClick={onClose}>Close</button>}>
      {loading ? (
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', paddingTop: 60, gap: 16 }}>
          <div className="spinner" />
          <div style={{ fontSize: 13, color: 'var(--text3)', fontStyle: 'italic' }}>Preparing your brief…</div>
        </div>
      ) : (
        <>
          <div className="gold-line" style={{ marginBottom: 20 }} />
          <div style={{
            fontSize: 15, lineHeight: 1.9, color: 'var(--text2)',
            whiteSpace: 'pre-wrap', fontFamily: 'var(--font-serif)',
          }}>
            {text}
          </div>
        </>
      )}
    </ModalShell>
  )
}

function getGreeting() {
  const h = new Date().getHours()
  if (h < 12) return 'Good morning'
  if (h < 17) return 'Good afternoon'
  return 'Good evening'
}
