export default function BottomNav({ active, onChange }) {
  const tabs = [
    { id: 'dashboard',   label: 'Home',     icon: HomeIcon   },
    { id: 'checkin',     label: 'Check-in', icon: HeartIcon  },
    { id: 'coach',       label: 'Council',  icon: CouncilIcon},
    { id: 'commitments', label: 'Goals',    icon: FlagIcon   },
    { id: 'wisdom',      label: 'Wisdom',   icon: LotusIcon  },
  ]
  return (
    <nav className="bottom-nav">
      {tabs.map(t => (
        <button
          key={t.id}
          className={`nav-item ${active === t.id ? 'active' : ''}`}
          onClick={() => onChange(t.id)}
        >
          <t.icon active={active === t.id} />
          <span>{t.label}</span>
        </button>
      ))}
    </nav>
  )
}

/* ── Icons — slightly bolder stroke when active ─────────────────────────── */

function HomeIcon({ active }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={active ? 2.2 : 1.8} strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>
      <polyline points="9 22 9 12 15 12 15 22"/>
    </svg>
  )
}

function HeartIcon({ active }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={active ? 2.2 : 1.8} strokeLinecap="round" strokeLinejoin="round">
      <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/>
    </svg>
  )
}

function CouncilIcon({ active }) {
  /* Four small circles arranged in a 2×2 — representing the four voices */
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={active ? 2 : 1.7} strokeLinecap="round" strokeLinejoin="round">
      <circle cx="7"  cy="7"  r="2.8"/>
      <circle cx="17" cy="7"  r="2.8"/>
      <circle cx="7"  cy="17" r="2.8"/>
      <circle cx="17" cy="17" r="2.8"/>
    </svg>
  )
}

function FlagIcon({ active }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={active ? 2.2 : 1.8} strokeLinecap="round" strokeLinejoin="round">
      <path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z"/>
      <line x1="4" y1="22" x2="4" y2="15"/>
    </svg>
  )
}

function LotusIcon({ active }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={active ? 2 : 1.7} strokeLinecap="round" strokeLinejoin="round">
      {/* Lotus flower — centre petal */}
      <path d="M12 21C12 21 7 17 7 12a5 5 0 0 1 10 0c0 5-5 9-5 9z"/>
      {/* Left petal */}
      <path d="M7 12C7 12 3 11 3 7a4 4 0 0 1 7.5-1.9"/>
      {/* Right petal */}
      <path d="M17 12C17 12 21 11 21 7a4 4 0 0 0-7.5-1.9"/>
      {/* Stem */}
      <line x1="12" y1="21" x2="12" y2="23"/>
    </svg>
  )
}
