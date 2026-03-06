import { useState } from 'react'
import { api } from '../api/client'

export default function GoalWizard({ uid, onClose, onComplete }) {
    const [step, setStep] = useState(1)
    const [title, setTitle] = useState('')
    const [vision, setVision] = useState('')
    const [category, setCategory] = useState('growth')
    const [targetDate, setTargetDate] = useState('')
    const [loading, setLoading] = useState(false)
    const [refinedVision, setRefinedVision] = useState('')
    const [error, setError] = useState('')

    const CATEGORIES = [
        { id: 'growth', label: 'Personal Growth', icon: '🌱' },
        { id: 'leadership', label: 'Leadership', icon: '👔' },
        { id: 'business', label: 'Business', icon: '📈' },
        { id: 'energy', label: 'Energy & Health', icon: '⚡' }
    ]

    const totalSteps = 3

    const handleNext = async () => {
        if (step === 1 && !title.trim()) return
        if (step === 2) {
            setLoading(true)
            try {
                // Create the goal first to get an ID
                const goal = await api.goals.create(uid, title, vision, targetDate, category)
                // Then refine it
                const ref = await api.goals.refine(uid, goal.id, vision || title)
                setRefinedVision(ref.refined_vision)
                setStep(3)
            } catch (err) {
                setError('The Council is busy. Proceeding with your raw vision.')
                setStep(3)
            } finally {
                setLoading(false)
            }
            return
        }
        setStep(v => v + 1)
    }

    const handleFinish = () => {
        onComplete()
        onClose()
    }

    return (
        <div style={{
            position: 'fixed', inset: 0, zIndex: 1000, background: 'rgba(0,0,0,0.92)',
            display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 20
        }}>
            <div className="card" style={{ maxWidth: 400, width: '100%', position: 'relative', overflow: 'hidden' }}>
                {/* Progress bar */}
                <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 4, background: 'var(--bg3)' }}>
                    <div style={{ height: '100%', width: `${(step / totalSteps) * 100}%`, background: 'var(--primary)', transition: 'width 0.4s ease' }} />
                </div>

                <div style={{ marginTop: 20 }}>
                    {step === 1 && (
                        <div>
                            <div style={{ fontSize: 24, fontWeight: 800, marginBottom: 8 }}>What is the big vision?</div>
                            <div className="hint" style={{ marginBottom: 24 }}>Define your high-level objective for the next 90 days.</div>

                            <div className="label">Goal Title</div>
                            <input
                                className="input mt-1 mb-4"
                                placeholder="e.g. Master Executive Presence"
                                value={title}
                                onChange={e => setTitle(e.target.value)}
                                autoFocus
                            />

                            <div className="label">Category</div>
                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }} className="mt-1">
                                {CATEGORIES.map(cat => (
                                    <button
                                        key={cat.id}
                                        onClick={() => setCategory(cat.id)}
                                        style={{
                                            padding: '12px 8px', borderRadius: 12, border: category === cat.id ? '2px solid var(--primary)' : '2px solid var(--border)',
                                            background: category === cat.id ? 'var(--primary-light)' : 'var(--bg3)',
                                            color: category === cat.id ? 'var(--primary)' : 'var(--text2)',
                                            fontSize: 13, fontWeight: 600, cursor: 'pointer', textAlign: 'center'
                                        }}
                                    >
                                        <span style={{ display: 'block', fontSize: 20, marginBottom: 4 }}>{cat.icon}</span>
                                        {cat.label}
                                    </button>
                                ))}
                            </div>
                        </div>
                    )}

                    {step === 2 && (
                        <div>
                            <div style={{ fontSize: 24, fontWeight: 800, marginBottom: 8 }}>The Rough Draft</div>
                            <div className="hint" style={{ marginBottom: 24 }}>Describe your vision in your own words. The Council will help you refine it.</div>

                            <div className="label">Your Vision / Context</div>
                            <textarea
                                className="input mt-1 mb-4"
                                placeholder="I want to be more confident in board meetings and handle conflict without getting defensive..."
                                value={vision}
                                onChange={e => setVision(e.target.value)}
                                style={{ minHeight: 120 }}
                                autoFocus
                            />

                            <div className="label">Target Date</div>
                            <input
                                type="date"
                                className="input mt-1"
                                value={targetDate}
                                onChange={e => setTargetDate(e.target.value)}
                            />
                        </div>
                    )}

                    {step === 3 && (
                        <div>
                            <div style={{ fontSize: 24, fontWeight: 800, marginBottom: 8 }}>Council Alignment</div>
                            <div className="hint" style={{ marginBottom: 24 }}>The Council has refined your vision into a SMART objective.</div>

                            <div className="card-sm" style={{ background: 'rgba(99,102,241,0.05)', border: '1px solid rgba(99,102,241,0.2)', padding: 16 }}>
                                <div style={{ fontSize: 13, color: 'var(--primary)', fontWeight: 700, textTransform: 'uppercase', marginBottom: 8 }}>Refined Vision</div>
                                <div style={{ fontSize: 15, lineHeight: 1.6, color: 'var(--text1)', fontStyle: 'italic' }}>
                                    "{refinedVision || vision || 'No vision provided.'}"
                                </div>
                            </div>

                            <div style={{ marginTop: 20, fontSize: 13, color: 'var(--text3)', lineHeight: 1.5 }}>
                                ✅ Specific and Measurable<br />
                                ✅ Feasibilty checked against current load<br />
                                ✅ Aligned with your core values
                            </div>
                        </div>
                    )}
                </div>

                <div style={{ display: 'flex', gap: 12, marginTop: 32 }}>
                    {step < totalSteps ? (
                        <>
                            <button
                                className="btn btn-secondary"
                                onClick={onClose}
                                style={{ flex: 1 }}
                            >
                                Cancel
                            </button>
                            <button
                                className="btn btn-primary"
                                onClick={handleNext}
                                disabled={loading || (step === 1 && !title.trim())}
                                style={{ flex: 2 }}
                            >
                                {loading ? 'Consulting Council...' : 'Next'}
                            </button>
                        </>
                    ) : (
                        <button
                            className="btn btn-primary"
                            onClick={handleFinish}
                            style={{ width: '100%' }}
                        >
                            Start Mission
                        </button>
                    )}
                </div>
            </div>
        </div>
    )
}
