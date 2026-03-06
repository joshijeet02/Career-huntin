import { useState, useEffect } from 'react'
import { api } from '../api/client'
import GoalWizard from '../components/GoalWizard'

const STATUS_OPTIONS = [
    { value: 'kept', label: '✅ Kept', color: 'var(--success)' },
    { value: 'partial', label: '🟡 Partial', color: 'var(--warning)' },
    { value: 'missed', label: '❌ Missed', color: '#ef4444' },
    { value: 'deferred', label: '⏩ Deferred', color: 'var(--text3)' },
]

const CATEGORY_ICONS = {
    growth: '🌱',
    leadership: '👔',
    business: '📈',
    energy: '⚡'
}

export default function Goals({ uid }) {
    const [goals, setGoals] = useState([])
    const [loading, setLoading] = useState(true)
    const [showWizard, setShowWizard] = useState(false)
    const [selectedGoal, setSelectedGoal] = useState(null)
    const [goalDetails, setGoalDetails] = useState(null)

    const loadGoals = async () => {
        setLoading(true)
        try {
            const data = await api.goals.list(uid)
            setGoals(data)
        } catch (e) { console.error(e) }
        finally { setLoading(false) }
    }

    const loadGoalDetails = async (goalId) => {
        try {
            const details = await api.goals.details(uid, goalId)
            setGoalDetails(details)
            setSelectedGoal(goals.find(g => g.id === goalId))
        } catch (e) { console.error(e) }
    }

    useEffect(() => { loadGoals() }, [uid])

    if (loading) return <div className="splash"><div className="spinner" /></div>

    return (
        <div className="p-5">
            <div className="section-header">
                <div>
                    <div style={{ fontSize: 24, fontWeight: 700 }}>Missions</div>
                    <div className="hint">{goals.length} active goals</div>
                </div>
                <button className="btn btn-primary btn-sm" style={{ width: 'auto' }} onClick={() => setShowWizard(true)}>
                    + New Goal
                </button>
            </div>

            {goals.length === 0 && !showWizard && (
                <div className="card mt-4" style={{ textAlign: 'center', padding: '60px 24px' }}>
                    <div style={{ fontSize: 48, marginBottom: 16 }}>🎯</div>
                    <div style={{ fontWeight: 700, fontSize: 18, marginBottom: 8 }}>Set your first big goal</div>
                    <div className="hint" style={{ maxWidth: 280, margin: '0 auto' }}>
                        A goal without a plan is just a wish. Let the Council help you map out your next 90 days.
                    </div>
                    <button className="btn btn-primary mt-6" onClick={() => setShowWizard(true)}>
                        Start SMART Goal Wizard
                    </button>
                </div>
            )}

            <div className="mt-4" style={{ display: 'grid', gap: 16 }}>
                {goals.map(goal => (
                    <GoalCard
                        key={goal.id}
                        goal={goal}
                        onClick={() => loadGoalDetails(goal.id)}
                        isSelected={selectedGoal?.id === goal.id}
                    />
                ))}
            </div>

            {selectedGoal && goalDetails && (
                <GoalDetailsPane
                    uid={uid}
                    goal={selectedGoal}
                    details={goalDetails}
                    onUpdate={() => { loadGoalDetails(selectedGoal.id); loadGoals(); }}
                    onClose={() => { setSelectedGoal(null); setGoalDetails(null); }}
                />
            )}

            {showWizard && (
                <GoalWizard
                    uid={uid}
                    onClose={() => setShowWizard(false)}
                    onComplete={loadGoals}
                />
            )}
        </div>
    )
}

function GoalCard({ goal, onClick, isSelected }) {
    return (
        <div
            className={`card ${isSelected ? 'selected' : ''}`}
            onClick={onClick}
            style={{
                cursor: 'pointer',
                borderLeft: `4px solid ${isSelected ? 'var(--primary)' : 'var(--border)'}`,
                transition: 'all 0.2s ease'
            }}
        >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 }}>
                <div>
                    <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--text3)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                        {CATEGORY_ICONS[goal.category] || '🎯'} {goal.category}
                    </div>
                    <div style={{ fontSize: 18, fontWeight: 700, marginTop: 4 }}>{goal.title}</div>
                </div>
                <div style={{
                    background: 'var(--bg3)', padding: '4px 8px', borderRadius: 6,
                    fontSize: 12, fontWeight: 700, color: goal.progress_pct > 0 ? 'var(--primary)' : 'var(--text3)'
                }}>
                    {goal.progress_pct}%
                </div>
            </div>

            <div style={{ height: 6, background: 'var(--bg3)', borderRadius: 3, overflow: 'hidden' }}>
                <div style={{ height: '100%', width: `${goal.progress_pct}%`, background: 'var(--primary)', transition: 'width 0.4s ease' }} />
            </div>

            {goal.vision_statement && (
                <div style={{ marginTop: 12, fontSize: 12, color: 'var(--text3)', fontStyle: 'italic', lineHeight: 1.4 }}>
                    "{(goal.vision_statement.length > 80 ? goal.vision_statement.slice(0, 80) + '...' : goal.vision_statement)}"
                </div>
            )}
        </div>
    )
}

function GoalDetailsPane({ uid, goal, details, onUpdate, onClose }) {
    const [showAddCommitment, setShowAddCommitment] = useState(false)
    const [newCText, setNewCText] = useState('')
    const [checkingIn, setCheckingIn] = useState(null)

    const addCommitment = async () => {
        if (!newCText.trim()) return
        try {
            await api.commitments.create(uid, newCText.trim(), null, goal.id)
            setNewCText('')
            setShowAddCommitment(false)
            onUpdate()
        } catch (e) { alert(e.message) }
    }

    return (
        <div style={{
            position: 'fixed', inset: 0, zIndex: 500, background: 'rgba(0,0,0,0.85)',
            display: 'flex', alignItems: 'flex-end', maxWidth: 430, margin: '0 auto',
        }}>
            <div style={{
                background: 'var(--bg1)', borderRadius: '24px 24px 0 0', width: '100%',
                height: '90vh', overflowY: 'auto', padding: '24px 20px',
                paddingBottom: 'calc(24px + env(safe-area-inset-bottom))'
            }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 20 }}>
                    <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--primary)', textTransform: 'uppercase' }}>Goal Intelligence</div>
                    <button onClick={onClose} style={{ background: 'none', border: 'none', color: 'var(--text3)', fontSize: 20, cursor: 'pointer' }}>✕</button>
                </div>

                <div style={{ fontSize: 24, fontWeight: 800, marginBottom: 8 }}>{goal.title}</div>
                <div className="card-sm" style={{ background: 'var(--bg3)', padding: 16, marginBottom: 24 }}>
                    <div style={{ fontSize: 13, lineHeight: 1.6, color: 'var(--text2)' }}>{goal.vision_statement || goal.description}</div>
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                    <div style={{ fontSize: 14, fontWeight: 700 }}>Commitments</div>
                    <button className="btn btn-secondary btn-sm" style={{ width: 'auto' }} onClick={() => setShowAddCommitment(true)}>+ Add</button>
                </div>

                {showAddCommitment && (
                    <div className="card-sm mb-4" style={{ background: 'var(--bg2)' }}>
                        <textarea
                            className="input"
                            placeholder="Next tactical step..."
                            value={newCText}
                            onChange={e => setNewCText(e.target.value)}
                            autoFocus
                        />
                        <div style={{ display: 'flex', gap: 8, marginTop: 12 }}>
                            <button className="btn btn-primary btn-sm" onClick={addCommitment}>Save</button>
                            <button className="btn btn-secondary btn-sm" onClick={() => setShowAddCommitment(false)}>Cancel</button>
                        </div>
                    </div>
                )}

                <div style={{ display: 'grid', gap: 12 }}>
                    {details.commitments.map(c => (
                        <div key={c.id} className="card-sm" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', opacity: c.status !== 'open' ? 0.6 : 1 }}>
                            <div>
                                <div style={{ fontSize: 14, fontWeight: 500, textDecoration: c.status === 'kept' ? 'line-through' : 'none' }}>{c.commitment_text}</div>
                                <div style={{ fontSize: 11, color: 'var(--text3)' }}>{c.status} • {c.due_date}</div>
                            </div>
                            {c.status === 'open' && (
                                <button
                                    onClick={() => setCheckingIn(c)}
                                    style={{ background: 'var(--bg3)', border: '1px solid var(--border)', borderRadius: 6, padding: '4px 8px', fontSize: 11, fontWeight: 700 }}
                                >
                                    Update
                                </button>
                            )}
                        </div>
                    ))}
                    {details.commitments.length === 0 && (
                        <div className="hint" style={{ textAlign: 'center', padding: '20px 0' }}>No specific commitments yet. Add one to start moving the needle.</div>
                    )}
                </div>

                {checkingIn && (
                    <div style={{ position: 'fixed', inset: 0, zIndex: 600, background: 'rgba(0,0,0,0.92)', display: 'flex', alignItems: 'center', padding: 20 }}>
                        <div className="card" style={{ width: '100%' }}>
                            <div style={{ fontWeight: 700, marginBottom: 16 }}>Update Progress</div>
                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                                {STATUS_OPTIONS.map(opt => (
                                    <button
                                        key={opt.value}
                                        onClick={async () => {
                                            await api.commitments.checkin(uid, checkingIn.id, opt.value, '')
                                            setCheckingIn(null)
                                            onUpdate()
                                        }}
                                        style={{ padding: 12, borderRadius: 12, border: '1px solid var(--border)', background: 'var(--bg3)', fontWeight: 600 }}
                                    >
                                        {opt.label}
                                    </button>
                                ))}
                            </div>
                            <button className="btn btn-secondary mt-4" onClick={() => setCheckingIn(null)} style={{ width: '100%' }}>Cancel</button>
                        </div>
                    </div>
                )}
            </div>
        </div>
    )
}
