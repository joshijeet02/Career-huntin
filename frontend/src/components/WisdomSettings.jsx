import { useState } from 'react'
import { api } from '../api/client'

const TRADITIONS = [
    "Stoic",
    "Modern Strategy",
    "Buddhist",
    "Hindu",
    "Islamic",
    "Christian",
    "Sufi",
    "Taoist",
    "Jain",
    "Universal / Mystical"
]

export default function WisdomSettings({ uid, currentPrefs, onUpdate }) {
    const [selected, setSelected] = useState(currentPrefs || [])
    const [loading, setLoading] = useState(false)

    const toggleTradition = (t) => {
        if (selected.includes(t)) {
            setSelected(selected.filter(item => item !== t))
        } else {
            setSelected([...selected, t])
        }
    }

    const handleSave = async () => {
        setLoading(true)
        try {
            const updated = await api.profile.updateWisdom(uid, selected)
            onUpdate(updated.wisdom_preferences)
        } catch (err) {
            console.error(err)
        } finally {
            setLoading(false)
        }
    }

    return (
        <div className="card mb-4" style={{ background: 'var(--bg2)', border: '1px solid var(--border)' }}>
            <div className="label mb-3">Wisdom Personalization</div>
            <div className="hint mb-4">Select the traditions the Council should prioritize for your daily coaching.</div>

            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 20 }}>
                {TRADITIONS.map(t => (
                    <button
                        key={t}
                        onClick={() => toggleTradition(t)}
                        style={{
                            padding: '8px 12px',
                            borderRadius: 20,
                            border: '1px solid',
                            borderColor: selected.includes(t) ? 'var(--gold)' : 'var(--border)',
                            background: selected.includes(t) ? 'rgba(201, 168, 76, 0.2)' : 'var(--bg1)',
                            color: selected.includes(t) ? 'var(--gold)' : 'var(--text2)',
                            fontSize: 12,
                            fontWeight: 600,
                            cursor: 'pointer',
                            transition: 'all 0.2s'
                        }}
                    >
                        {t}
                    </button>
                ))}
            </div>

            <button
                onClick={handleSave}
                disabled={loading}
                style={{
                    width: '100%',
                    padding: '12px',
                    borderRadius: 12,
                    border: 'none',
                    background: 'var(--primary)',
                    color: '#fff',
                    fontWeight: 700,
                    cursor: 'pointer',
                    opacity: loading ? 0.7 : 1
                }}
            >
                {loading ? 'Saving...' : 'Save Preferences'}
            </button>
        </div>
    )
}
