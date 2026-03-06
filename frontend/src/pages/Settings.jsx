import { useState, useEffect } from 'react'
import { api, getUserId, setUserId } from '../api/client'

function urlBase64ToUint8Array(base64String) {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4)
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/')
  const raw = atob(base64)
  return Uint8Array.from([...raw].map((c) => c.charCodeAt(0)))
}

async function getCurrentPushState() {
  if (!('Notification' in window)) return 'unsupported'
  if (!('serviceWorker' in navigator)) return 'unsupported'
  const perm = Notification.permission
  if (perm === 'denied') return 'denied'
  if (perm === 'default') return 'not-asked'
  // granted — check if actually subscribed
  try {
    const reg = await navigator.serviceWorker.ready
    const sub = await reg.pushManager.getSubscription()
    return sub ? 'subscribed' : 'granted-not-subscribed'
  } catch { return 'error' }
}

export default function Settings({ uid }) {
  const [pushState, setPushState] = useState(null)
  const [profile, setProfile] = useState(null)
  const [working, setWorking] = useState(false)
  const [msg, setMsg] = useState('')

  useEffect(() => {
    getCurrentPushState().then(setPushState)
    api.profile.get(uid).then(setProfile).catch(() => { })
  }, [uid])

  const enableNotifications = async () => {
    setWorking(true)
    setMsg('')
    try {
      const perm = await Notification.requestPermission()
      if (perm !== 'granted') {
        setMsg("Permission denied. Enable in your phone's Settings → Notifications.")
        setPushState('denied')
        return
      }
      const reg = await navigator.serviceWorker.ready
      const { public_key } = await api.push.getVapidKey()
      const sub = await reg.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(public_key),
      })
      const k = sub.getKey('p256dh')
      const a = sub.getKey('auth')
      await api.push.subscribe(
        uid,
        sub.endpoint,
        btoa(String.fromCharCode(...new Uint8Array(k))).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, ''),
        btoa(String.fromCharCode(...new Uint8Array(a))).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '')
      )
      setPushState('subscribed')
      localStorage.setItem('notif_banner_dismissed', '1')
      setMsg("✅ Notifications enabled! You'll get a nudge at 8 AM and 7 PM.")
    } catch (e) {
      setMsg('Something went wrong. Try again.')
      console.error(e)
    } finally {
      setWorking(false)
    }
  }

  const disableNotifications = async () => {
    setWorking(true)
    setMsg('')
    try {
      const reg = await navigator.serviceWorker.ready
      const sub = await reg.pushManager.getSubscription()
      if (sub) {
        await api.push.unsubscribe(sub.endpoint).catch(() => { })
        await sub.unsubscribe()
      }
      setPushState('not-asked')
      setMsg('Notifications disabled.')
    } catch (e) {
      setMsg('Could not disable. Try again.')
    } finally {
      setWorking(false)
    }
  }

  const pushLabel = {
    'unsupported': '❌ Not supported on this browser',
    'denied': '🚫 Blocked — enable in phone Settings',
    'not-asked': '🔔 Not enabled yet',
    'granted-not-subscribed': '⚠️ Permission granted but not subscribed',
    'subscribed': '✅ Active',
    'error': '⚠️ Error checking status',
  }[pushState] || '…'

  const name = profile?.full_name?.split(' ')[0] || 'there'

  return (
    <div className="p-5">
      <div style={{ fontSize: 24, fontWeight: 700, marginBottom: 4 }}>Settings</div>
      <div className="hint mb-5">Manage your coaching experience</div>

      {/* Profile card */}
      {profile && (
        <div className="card mb-4">
          <div className="label" style={{ marginBottom: 12 }}>Your profile</div>
          <div style={{ display: 'flex', gap: 14, alignItems: 'center' }}>
            <div style={{ width: 48, height: 48, borderRadius: 24, background: 'linear-gradient(135deg, #6366f1, #8b5cf6)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 20, fontWeight: 700, flexShrink: 0 }}>
              {(profile.full_name || 'U')[0].toUpperCase()}
            </div>
            <div>
              <div style={{ fontWeight: 700, fontSize: 16 }}>{profile.full_name}</div>
              <div style={{ fontSize: 13, color: 'var(--text3)', marginTop: 2 }}>{profile.role}{profile.organization ? ` · ${profile.organization}` : ''}</div>
            </div>
          </div>
          {profile.core_values?.length > 0 && (
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 14 }}>
              {profile.core_values.map((v, i) => (
                <span key={i} style={{ fontSize: 11, background: 'var(--bg3)', borderRadius: 20, padding: '4px 10px', color: 'var(--text2)' }}>{v}</span>
              ))}
            </div>
          )}
          {profile.coaching_style_preference && (
            <div className="hint mt-3">
              Coaching style: <span style={{ color: 'var(--text2)', fontWeight: 600 }}>{profile.coaching_style_preference}</span>
            </div>
          )}
        </div>
      )}

      {/* Notifications */}
      <div className="card mb-4">
        <div className="label" style={{ marginBottom: 4 }}>Push notifications</div>
        <div className="hint mb-4" style={{ lineHeight: 1.5 }}>
          Daily nudges: 8 AM morning brief + 7 PM reflection reminder.
        </div>

        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <div style={{ fontSize: 13, color: 'var(--text2)' }}>Status</div>
          <div style={{ fontSize: 13, fontWeight: 600 }}>{pushState === null ? '…' : pushLabel}</div>
        </div>

        {pushState === 'subscribed' ? (
          <button
            className="btn btn-secondary"
            onClick={disableNotifications}
            disabled={working}
          >
            {working ? 'Working…' : 'Disable notifications'}
          </button>
        ) : pushState === 'denied' ? (
          <div style={{ fontSize: 12, color: 'var(--text3)', lineHeight: 1.6 }}>
            You've blocked notifications. On iPhone: Settings → {name}'s Phone → Coach → Notifications → Allow.
          </div>
        ) : pushState === 'unsupported' ? (
          <div style={{ fontSize: 12, color: 'var(--text3)', lineHeight: 1.6 }}>
            Push notifications require iOS 16.4+ with the app added to your home screen.
          </div>
        ) : (
          <button
            className="btn btn-primary"
            onClick={enableNotifications}
            disabled={working || pushState === null}
          >
            {working ? 'Enabling…' : 'Enable notifications'}
          </button>
        )}

        {msg && (
          <div style={{ marginTop: 12, fontSize: 13, color: msg.startsWith('✅') ? 'var(--success)' : 'var(--text3)', lineHeight: 1.5 }}>
            {msg}
          </div>
        )}
      </div>

      {/* Profile Recovery */}
      <div className="card mb-4">
        <div className="label" style={{ marginBottom: 4 }}>Profile Recovery</div>
        <div className="hint mb-4" style={{ lineHeight: 1.5 }}>
          Your profile is linked to this unique ID. Save it to restore your account on another device.
        </div>

        <div style={{
          background: 'var(--bg1)',
          padding: '12px',
          borderRadius: 10,
          fontSize: 13,
          fontFamily: 'monospace',
          marginBottom: 16,
          border: '1px solid var(--border)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center'
        }}>
          <span style={{ color: 'var(--gold)' }}>{uid}</span>
          <button
            style={{ background: 'none', border: 'none', color: 'var(--text3)', cursor: 'pointer', fontSize: 12 }}
            onClick={() => {
              navigator.clipboard.writeText(uid)
              alert('Copied to clipboard!')
            }}
          >
            Copy
          </button>
        </div>

        <div style={{ display: 'flex', gap: 10 }}>
          <input
            className="input"
            style={{ flex: 1, height: 44, margin: 0, fontSize: 13 }}
            placeholder="Enter Profile ID..."
            id="recovery-id"
          />
          <button
            className="btn btn-secondary"
            style={{ width: 'auto', padding: '0 16px', height: 44 }}
            onClick={() => {
              const val = document.getElementById('recovery-id').value.trim()
              if (val.startsWith('user_')) {
                setUserId(val)
              } else {
                alert('Invalid Profile ID. Must start with "user_"')
              }
            }}
          >
            Recover
          </button>
        </div>
      </div>

      {/* About */}
      <div className="card mb-4">
        <div className="label" style={{ marginBottom: 10 }}>About</div>
        <div style={{ fontSize: 13, color: 'var(--text3)', lineHeight: 1.8 }}>
          <div>Version: 6.0 (PWA)</div>
          <div>Backend: career-huntin.onrender.com</div>
          <div style={{ marginTop: 8, color: 'var(--text3)', fontSize: 12 }}>
            Calendar integration requires the iOS native app (Google Calendar OAuth coming soon).
          </div>
        </div>
      </div>

      {/* Reset onboarding */}
      <div className="card">
        <div className="label" style={{ marginBottom: 8 }}>Danger zone</div>
        <div className="hint mb-3">Clear local data. Your cloud profile stays intact.</div>
        <button
          className="btn btn-secondary"
          style={{ color: '#ef4444', borderColor: 'rgba(239,68,68,0.3)' }}
          onClick={() => {
            if (window.confirm('This clears your local user ID. You will start fresh. Continue?')) {
              localStorage.clear()
              window.location.reload()
            }
          }}
        >
          Reset local data
        </button>
      </div>
    </div>
  )
}
