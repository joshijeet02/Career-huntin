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
        ).catch(() => {})
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
      ).catch(() => {})
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
        background: '#1e293b', border: '1px solid #334155',
        borderRadius: 16, padding: '16px 18px',
        boxShadow: '0 8px 32px rgba(0,0,0,0.5)',
      }}>
        <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 4 }}>
          🔔 Enable coaching nudges?
        </div>
        <div style={{ fontSize: 12, color: '#94a3b8', marginBottom: 14, lineHeight: 1.5 }}>
          Get a morning brief at 8 AM and an evening reflection reminder at 7 PM.
        </div>
        <div style={{ display: 'flex', gap: 10 }}>
          <button
            style={{ flex: 1, padding: '10px', background: '#6366f1', color: '#fff', border: 'none', borderRadius: 10, fontWeight: 700, fontSize: 13, cursor: 'pointer' }}
            onClick={enable} disabled={asking}
          >
            {asking ? 'Enabling…' : 'Enable'}
          </button>
          <button
            style={{ padding: '10px 16px', background: '#334155', color: '#94a3b8', border: 'none', borderRadius: 10, fontSize: 13, cursor: 'pointer' }}
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
          <div style={{ fontSize: 48, marginBottom: 8 }}>🧭</div>
          <div style={{ fontSize: 22, fontWeight: 700 }}>Coach</div>
          <div className="spinner" style={{ marginTop: 24 }} />
        </div>
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
