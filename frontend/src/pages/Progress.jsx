import { useState, useEffect } from 'react'
import { api } from '../api/client'
import WisdomSettings from '../components/WisdomSettings'

// Simple SVG sparkline component so we don't need heavy charting libraries
function EnergySparkline({ data, height = 120, color = 'var(--primary)' }) {
    if (!data || data.length < 2) return null

    const min = Math.min(...data) - 1
    const max = Math.max(...data) + 1
    const range = max - min

    const points = data.map((val, i) => {
        const x = (i / (data.length - 1)) * 100
        const y = 100 - (((val - min) / range) * 100)
        return `${x},${y}`
    }).join(' ')

    return (
        <svg width="100%" height={height} viewBox="0 0 100 100" preserveAspectRatio="none" style={{ overflow: 'visible', padding: '10px 0' }}>
            <polyline
                fill="none"
                stroke={color}
                strokeWidth="3"
                strokeLinecap="round"
                strokeLinejoin="round"
                points={points}
                style={{ vectorEffect: 'non-scaling-stroke' }}
            />
            {/* Draw a subtle baseline at 5.0 (neutral) */}
            <line
                x1="0" y1={100 - (((5 - min) / range) * 100)}
                x2="100" y2={100 - (((5 - min) / range) * 100)}
                stroke="var(--border)" strokeWidth="1" strokeDasharray="4 4"
                style={{ vectorEffect: 'non-scaling-stroke' }}
            />
        </svg>
    )
}

function SimpleMarkdown({ text }) {
    if (!text) return null
    return (
        <div style={{ lineHeight: 1.6, color: 'var(--text)', fontSize: 14 }}>
            {text.split('\n\n').map((paragraph, i) => {
                if (paragraph.startsWith('## ')) {
                    return <h3 key={i} style={{ marginTop: 24, marginBottom: 8, fontSize: 18, color: 'var(--gold)' }}>{paragraph.replace('## ', '')}</h3>
                }
                if (paragraph.startsWith('# ')) {
                    return <h2 key={i} style={{ marginTop: 24, marginBottom: 12, fontSize: 22, color: 'var(--gold)' }}>{paragraph.replace('# ', '')}</h2>
                }

                // Allow simple bolding
                const parts = paragraph.split(/(\*\*.*?\*\*)/g)
                return (
                    <p key={i} style={{ marginBottom: 16 }}>
                        {parts.map((p, j) =>
                            p.startsWith('**') && p.endsWith('**')
                                ? <strong key={j} style={{ color: 'var(--text1)' }}>{p.slice(2, -2)}</strong>
                                : p
                        )}
                    </p>
                )
            })}
        </div>
    )
}


export default function Progress({ uid }) {
    const [energyData, setEnergyData] = useState(null)
    const [achievements, setAchievements] = useState([])
    const [profile, setProfile] = useState(null)
    const [loading, setLoading] = useState(true)

    const [synthesisReport, setSynthesisReport] = useState(null)
    const [generatingReport, setGeneratingReport] = useState(false)
    const [synthesisError, setSynthesisError] = useState(null)

    const handleGenerateSynthesis = async () => {
        setGeneratingReport(true)
        setSynthesisError(null)
        try {
            const result = await api.coach.synthesis(uid, 30)
            setSynthesisReport(result.markdown_report)
        } catch (err) {
            setSynthesisError("Failed to generate report. Make sure you have at least 5 check-ins.")
        } finally {
            setGeneratingReport(false)
        }
    }


    useEffect(() => {
        async function load() {
            try {
                const [energy, ach, prof] = await Promise.all([
                    api.metrics.energy(uid, 30).catch(() => null),
                    api.metrics.achievements(uid).catch(() => []),
                    api.profile.get(uid).catch(() => null)
                ])
                setEnergyData(energy)
                setAchievements(ach)
                setProfile(prof)
            } finally {
                setLoading(false)
            }
        }
        load()
    }, [uid])

    if (loading) return <div className="splash"><div className="spinner" /></div>

    // Generate 30 mock data points if user doesn't have enough check-ins yet
    // This ensures the dashboard always looks good and shows users what they are building towards
    const trendData = energyData?.available && energyData.trend?.estimated_30_day_change
        ? null // We don't have literal time-series array from the backend yet! Let's just use the stability metrics.
        : null;

    return (
        <div className="p-5 pb-20">
            <div className="section-header">
                <div>
                    <div style={{ fontSize: 24, fontWeight: 700 }}>Progress & Patterns</div>
                    <div className="hint mb-4">Your coach's analysis of your performance data.</div>
                </div>
            </div>

            {/* Energy Pattern Cards */}
            {energyData?.coach_insight ? (
                <div className="card mb-4" style={{ borderColor: 'rgba(99,102,241,0.3)', background: 'rgba(99,102,241,0.05)' }}>
                    <div className="label">The Coach's Synthesis</div>
                    <div style={{
                        fontSize: 14,
                        lineHeight: 1.6,
                        color: 'var(--text)',
                        whiteSpace: 'pre-wrap',
                        fontStyle: 'italic'
                    }}>
                        {energyData.coach_insight}
                    </div>
                </div>
            ) : (
                <div className="card mb-4">
                    <div className="label">Pattern Engine Initializing</div>
                    <div className="hint mt-2">
                        Your coach needs 14 consecutive days of check-in data to confidently identify your energy and performance patterns.
                        Keep showing up. The data is compounding.
                    </div>
                </div>
            )}

            {energyData?.available && (
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 24 }}>
                    {/* Peak Day */}
                    {energyData.day_of_week?.available && (
                        <div className="card-sm">
                            <div className="label" style={{ fontSize: 11 }}>Peak Day</div>
                            <div style={{ fontSize: 20, fontWeight: 700, margin: '8px 0 4px' }}>
                                {energyData.day_of_week.peak_day}
                            </div>
                            <div className="hint" style={{ fontSize: 12 }}>
                                Avg energy: {energyData.day_of_week.peak_avg_energy}/10
                            </div>
                        </div>
                    )}

                    {/* Stability */}
                    {energyData.stability?.available && (
                        <div className="card-sm">
                            <div className="label" style={{ fontSize: 11 }}>Stability</div>
                            <div style={{ fontSize: 20, fontWeight: 700, margin: '8px 0 4px', textTransform: 'capitalize' }}>
                                {energyData.stability.stability_label}
                            </div>
                            <div className="hint" style={{ fontSize: 12 }}>
                                Score: {energyData.stability.stability_score}/100
                            </div>
                        </div>
                    )}
                </div>
            )}

            {/* Habit Correlations */}
            {energyData?.habit_correlations?.length > 0 && (
                <div className="mb-5">
                    <div className="label mb-3">Habit Intelligence</div>
                    {energyData.habit_correlations.map((h, i) => (
                        <div key={i} className="card-sm mb-3">
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                                <div style={{ fontWeight: 600 }}>{h.habit_name}</div>
                                <div style={{
                                    fontSize: 12,
                                    fontWeight: 700,
                                    color: h.energy_impact > 0 ? 'var(--success)' : '#ef4444'
                                }}>
                                    {h.energy_impact > 0 ? '+' : ''}{h.energy_impact} energy
                                </div>
                            </div>
                            <div className="hint" style={{ fontSize: 13, lineHeight: 1.5 }}>
                                {h.coach_note}
                            </div>
                        </div>
                    ))}
                </div>
            )}

            {/* Achievements / Gamification */}
            <div className="mb-4">
                <div className="label mb-3">Milestones Unlocked</div>
                {achievements.length > 0 ? (
                    achievements.map((ach) => (
                        <div key={ach.achievement_id} className="card-sm mb-3" style={{ borderLeft: '3px solid var(--primary)' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                                <div style={{ fontWeight: 700 }}>{ach.title}</div>
                                <div className="hint" style={{ fontSize: 11 }}>{ach.achievement_date}</div>
                            </div>
                            <div style={{ fontSize: 13, color: 'var(--text2)', fontStyle: 'italic', marginTop: 8 }}>
                                "{ach.coach_message}"
                            </div>
                        </div>
                    ))
                ) : (
                    <div className="card-sm" style={{ textAlign: 'center', padding: '24px 12px' }}>
                        <div className="hint mb-2">No milestones unlocked yet.</div>
                        <div style={{ fontSize: 12, color: 'var(--text3)' }}>
                            Consistent check-ins and completed 90-day sprints will unlock coach celebrations here.
                        </div>
                    </div>
                )}
            </div>

            {/* Wisdom Preferences */}
            <WisdomSettings
                uid={uid}
                currentPrefs={profile?.wisdom_preferences}
                onUpdate={(newPrefs) => setProfile({ ...profile, wisdom_preferences: newPrefs })}
            />

            {/* Premium Synthesis feature */}
            <div className="mb-4">
                <div className="label mb-3">Council Synthesis (Premium)</div>
                <div className="card" style={{ background: 'var(--bg2)', border: '1px solid var(--gold-border)' }}>
                    <div style={{ marginBottom: 16, fontSize: 14, color: 'var(--text2)', lineHeight: 1.5 }}>
                        Generate a comprehensive 30-day coaching report. The Council will analyze your check-ins, habits, and reflections to provide a deep, unified diagnosis of your current trajectory.
                    </div>

                    {!synthesisReport ? (
                        <button
                            onClick={handleGenerateSynthesis}
                            disabled={generatingReport}
                            style={{
                                background: 'linear-gradient(135deg, #c9a84c, #a87e2e)',
                                color: '#07080d',
                                border: 'none',
                                padding: '12px 16px',
                                borderRadius: 12,
                                fontWeight: 700,
                                width: '100%',
                                cursor: 'pointer'
                            }}
                        >
                            {generatingReport ? 'The Council is Synthesizing (Wait 20s)...' : 'Generate 30-Day Synthesis Report'}
                        </button>
                    ) : (
                        <div>
                            <div style={{ background: 'var(--bg1)', padding: 16, borderRadius: 12, border: '1px solid var(--border)', marginBottom: 16, maxHeight: 400, overflowY: 'auto' }}>
                                <SimpleMarkdown text={synthesisReport} />
                            </div>
                            <button
                                onClick={() => window.print()}
                                style={{
                                    background: 'var(--bg3)',
                                    color: 'var(--text)',
                                    border: '1px solid var(--border)',
                                    padding: '12px 16px',
                                    borderRadius: 12,
                                    fontWeight: 600,
                                    width: '100%',
                                    cursor: 'pointer'
                                }}
                            >
                                Export as PDF
                            </button>
                        </div>
                    )}

                    {synthesisError && (
                        <div style={{ color: '#ef4444', marginTop: 12, fontSize: 13, textAlign: 'center' }}>
                            {synthesisError}
                        </div>
                    )}
                </div>
            </div>

        </div>
    )
}

