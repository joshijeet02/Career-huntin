import { useState, useEffect } from 'react'
import { getUserId, api } from './api/client'
import BottomNav from './components/BottomNav'
import Onboarding from './pages/Onboarding'
import Dashboard from './pages/Dashboard'
import CheckIn from './pages/CheckIn'
import Coach from './pages/Coach'
import Habits from './pages/Habits'

export default function App() {
  const [uid] = useState(() => getUserId())
  const [tab, setTab] = useState('dashboard')
  const [onboarded, setOnboarded] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.onboarding.status(uid)
      .then(s => { setOnboarded(s.complete); setLoading(false) })
      .catch(() => { setOnboarded(false); setLoading(false) })
  }, [uid])

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

  const pages = { dashboard: Dashboard, checkin: CheckIn, coach: Coach, habits: Habits }
  const Page = pages[tab] || Dashboard

  return (
    <div className="app-shell">
      <div className="page">
        <Page uid={uid} onTabChange={setTab} />
      </div>
      <BottomNav active={tab} onChange={setTab} />
    </div>
  )
}
