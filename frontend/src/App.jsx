import { useState, useEffect } from 'react'
import { getUserId, api } from './api/client'
import BottomNav from './components/BottomNav'
import Onboarding from './pages/Onboarding'
import Dashboard from './pages/Dashboard'
import CheckIn from './pages/CheckIn'
import Coach from './pages/Coach'
import Habits from './pages/Habits'
import Settings from './pages/Settings'
import Commitments from './pages/Commitments'
import Wisdom from './pages/Wisdom'
import Progress from './pages/Progress'

// ── Web Push helpers ──────────────────────────────────────────────────────────
function urlBase64ToUint8Array(base64String) {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4)
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/')
  const raw = atob(base64)
  return Uint8Array.from([...raw].map((c) => c.charCodeAt(0)))
}

async function subscribeToPush(uid) {
  try {
    if (!('serviceWorker' in navigator) || !('PushManager' in window)) return
    const reg = await navigator.serviceWorker.ready
    const existing = await reg.pushManager.getSubscription()
    if (existing) {
      // Already subscribed — sync with backend in case it's a new session
      const k = existing.getKey('p256dh')
      const a = existing.getKey('auth')
      if (k && a) {
        await api.push.subscribe(
          uid,
          existing.endpoint,
          btoa(String.fromCharCode(...new Uint8Array(k))).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, ''),
          btoa(String.fromCharCode(...new Uint8Array(a))).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '')
        ).catch(() => { })
      }
      return existing
    }

    // Fetch VAPID key and subscribe
    const { public_key } = await api.push.getVapidKey()
    if (!public_key) return

    const sub = await reg.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: urlBase64ToUint8Array(public_key),
    })

    const k = sub.getKey('p256dh')
    const a = sub.getKey('auth')
    if (k && a) {
      await api.push.subscribe(
        uid,
        sub.endpoint,
        btoa(String.fromCharCode(...new Uint8Array(k))).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, ''),
        btoa(String.fromCharCode(...new Uint8Array(a))).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '')
      ).catch(() => { })
    }
    return sub
  } catch (e) {
    console.warn('Push subscribe failed:', e)
  }
}

// ── Notification permission banner ────────────────────────────────────────────
function NotifBanner({ uid, onDismiss }) {
  const [asking, setAsking] = useState(false)

  const enable = async () => {
    setAsking(true)
    try {
      const perm = await Notification.requestPermission()
      if (perm === 'granted') {
        await subscribeToPush(uid)
      }
    } catch (e) {
      console.warn('Notification permission error:', e)
    }
    onDismiss()
  }

  return (
    <div style={{
      position: 'fixed', bottom: 80, left: 0, right: 0, zIndex: 150,
      maxWidth: 430, margin: '0 auto', padding: '0 16px',
    }}>
      <div style={{
        background: 'rgba(11,14,24,0.97)',
        border: '1px solid var(--gold-border)',
        borderRadius: 18, padding: '18px 20px',
        boxShadow: '0 8px 40px rgba(0,0,0,0.7), 0 0 0 1px rgba(201,168,76,0.06) inset',
        backdropFilter: 'blur(20px)',
      }}>
        <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 4, color: 'var(--text1)' }}>
          🔔 Enable daily coaching nudges?
        </div>
        <div style={{ fontSize: 12, color: 'var(--text3)', marginBottom: 16, lineHeight: 1.6 }}>
          Morning brief at 8 AM · Evening reflection at 7 PM.
        </div>
        <div style={{ display: 'flex', gap: 10 }}>
          <button
            style={{ flex: 1, padding: '11px', background: 'linear-gradient(135deg, #c9a84c, #a87e2e)', color: '#07080d', border: 'none', borderRadius: 12, fontWeight: 700, fontSize: 13, cursor: 'pointer', letterSpacing: '0.02em' }}
            onClick={enable} disabled={asking}
          >
            {asking ? 'Enabling…' : 'Enable'}
          </button>
          <button
            style={{ padding: '11px 18px', background: 'var(--bg3)', color: 'var(--text3)', border: '1px solid var(--border)', borderRadius: 12, fontSize: 13, cursor: 'pointer' }}
            onClick={onDismiss}
          >
            Later
          </button>
        </div>
      </div>
    </div>
  )
}

// ── App ───────────────────────────────────────────────────────────────────────
export default function App() {
  const [uid] = useState(() => getUserId())
  const [tab, setTab] = useState('dashboard')
  const [onboarded, setOnboarded] = useState(null)
  const [loading, setLoading] = useState(true)
  const [showNotifBanner, setShowNotifBanner] = useState(false)

  useEffect(() => {
    api.onboarding.status(uid)
      .then(s => { setOnboarded(s.complete); setLoading(false) })
      .catch(() => { setOnboarded(false); setLoading(false) })
  }, [uid])

  // Show notification banner after onboarding, if not yet decided
  useEffect(() => {
    if (!onboarded) return
    if (!('Notification' in window)) return
    const dismissed = localStorage.getItem('notif_banner_dismissed')
    if (dismissed) return
    if (Notification.permission === 'granted') {
      // Already granted — silently sync subscription
      subscribeToPush(uid)
      return
    }
    if (Notification.permission === 'denied') return
    // Show banner after a short delay so the dashboard loads first
    const t = setTimeout(() => setShowNotifBanner(true), 2500)
    return () => clearTimeout(t)
  }, [onboarded, uid])

  const dismissNotifBanner = () => {
    setShowNotifBanner(false)
    localStorage.setItem('notif_banner_dismissed', '1')
  }

  if (loading) {
    return (
      <div className="app-shell">
        <div className="splash">
          <div style={{ display: 'flex', gap: 10, marginBottom: 16 }}>
            {['🪔', '🎯', '🫀', '🧬'].map((ic, i) => (
              <span key={i} style={{
                fontSize: 22, opacity: 0.6,
                animation: `pulse 1.6s ease-in-out ${i * 0.25}s infinite`,
                display: 'inline-block',
              }}>{ic}</span>
            ))}
          </div>
          <div style={{
            fontFamily: 'var(--font-serif)',
            fontSize: 30, fontWeight: 600,
            color: 'var(--gold)',
            fontStyle: 'italic',
            marginBottom: 6,
          }}>
            The Council
          </div>
          <div style={{ fontSize: 13, color: 'var(--text3)', letterSpacing: '0.12em', textTransform: 'uppercase', marginBottom: 28 }}>
            Your personal coaching OS
          </div>
          <div className="spinner" />
        </div>
        <style>{`
          @keyframes pulse {
            0%, 100% { opacity: 0.25; transform: scale(0.88); }
            50%       { opacity: 0.9;  transform: scale(1.08); }
          }
        `}</style>
      </div>
    )
  }

  if (!onboarded) {
    return (
      <div className="app-shell">
        <Onboarding uid={uid} onComplete={() => setOnboarded(true)} />
      </div>
    )
  }

  const pages = {
    dashboard: Dashboard,
    checkin: CheckIn,
    coach: Coach,
    habits: Habits,
    settings: Settings,
    commitments: Commitments,
    wisdom: Wisdom,
    progress: Progress,
  }
  const Page = pages[tab] || Dashboard

  return (
    <div className="app-shell">
      <div className="page">
        <Page uid={uid} onTabChange={setTab} />
      </div>
      <BottomNav active={tab} onChange={setTab} />
      {showNotifBanner && (
        <NotifBanner uid={uid} onDismiss={dismissNotifBanner} />
      )}
    </div>
  )
}
