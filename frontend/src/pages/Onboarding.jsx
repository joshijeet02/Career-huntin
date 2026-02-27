import { useState, useEffect } from 'react'
import { api } from '../api/client'

const TOTAL_ESTIMATE = 12

export default function Onboarding({ uid, onComplete }) {
  const [question, setQuestion] = useState(null)
  const [answer, setAnswer] = useState('')
  const [step, setStep] = useState(0)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const fetchNext = async () => {
    setLoading(true)
    setAnswer('')
    setError('')
    try {
      const q = await api.onboarding.question(uid)
      if (q.complete) { onComplete(); return }
      setQuestion(q)
      setStep(s => s + 1)
    } catch (e) {
      setError('Could not load question. Check your connection.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchNext() }, [])

  const submit = async () => {
    if (!answer.trim()) return
    setSaving(true)
    setError('')
    try {
      await api.onboarding.answer(uid, question.question_key, answer.trim())
      fetchNext()
    } catch (e) {
      setError(e.message || 'Failed to save. Try again.')
    } finally {
      setSaving(false)
    }
  }

  const pct = Math.min((step / TOTAL_ESTIMATE) * 100, 90)

  return (
    <div className="page-no-nav" style={{ display: 'flex', flexDirection: 'column' }}>
      {/* Header */}
      <div style={{ padding: '20px 24px 16px', paddingTop: 'calc(var(--safe-top) + 20px)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 20 }}>
          <span style={{ fontSize: 28 }}>🧭</span>
          <div>
            <div style={{ fontSize: 20, fontWeight: 700 }}>Coach</div>
            <div className="hint">Let's build your profile</div>
          </div>
        </div>
        <div className="progress-bar">
          <div className="progress-fill" style={{ width: `${pct}%` }} />
        </div>
        <div className="hint mt-2">Step {step} of ~{TOTAL_ESTIMATE}</div>
      </div>

      {/* Question */}
      <div style={{ flex: 1, padding: '0 24px 32px', display: 'flex', flexDirection: 'column' }}>
        {loading ? (
          <div className="splash"><div className="spinner" /></div>
        ) : question ? (
          <>
            <div style={{ marginBottom: 24 }}>
              <div style={{ fontSize: 22, fontWeight: 700, lineHeight: 1.3, marginBottom: 8 }}>
                {question.question_text}
              </div>
              {question.hint && <div className="hint">{question.hint}</div>}
            </div>

            {/* Multi-choice or free text */}
            {question.options && question.options.length > 0 ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10, flex: 1 }}>
                {question.options.map(opt => (
                  <button
                    key={opt}
                    className={`btn ${answer === opt ? 'btn-primary' : 'btn-ghost'}`}
                    style={{ justifyContent: 'flex-start', padding: '14px 18px' }}
                    onClick={() => setAnswer(opt)}
                  >
                    {opt}
                  </button>
                ))}
              </div>
            ) : question.input_type === 'multiline' ? (
              <textarea
                className="input"
                style={{ flex: 1, minHeight: 120 }}
                placeholder={question.placeholder || 'Type your answer…'}
                value={answer}
                onChange={e => setAnswer(e.target.value)}
              />
            ) : (
              <input
                className="input"
                type="text"
                placeholder={question.placeholder || 'Type your answer…'}
                value={answer}
                onChange={e => setAnswer(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && submit()}
                autoFocus
              />
            )}

            {error && <div className="error mt-3">{error}</div>}

            <button
              className="btn btn-primary mt-5"
              onClick={submit}
              disabled={saving || !answer.trim()}
            >
              {saving ? <div className="spinner" style={{ width: 18, height: 18, borderWidth: 2 }} /> : 'Continue →'}
            </button>
          </>
        ) : (
          <div className="splash">
            <div style={{ fontSize: 40 }}>✅</div>
            <div style={{ fontSize: 18, fontWeight: 600 }}>All done!</div>
          </div>
        )}
      </div>
    </div>
  )
}
