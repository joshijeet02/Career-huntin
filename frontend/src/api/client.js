/**
 * API client — points to the FastAPI backend.
 *
 * In development: Vite proxies /api → localhost:8000
 * In production:  Set VITE_API_URL to your Render backend URL
 *                 e.g. https://career-huntin.onrender.com
 */

const BASE = import.meta.env.VITE_API_URL || ''

// User ID is stored in localStorage so both Jeet and Papa each have their own
export function getUserId() {
  let uid = localStorage.getItem('coach_user_id')
  if (!uid) {
    uid = 'user_' + Math.random().toString(36).slice(2, 10)
    localStorage.setItem('coach_user_id', uid)
  }
  return uid
}

async function req(method, path, body = null) {
  const url = `${BASE}${path}`
  const opts = {
    method,
    headers: { 'Content-Type': 'application/json' },
  }
  if (body) opts.body = JSON.stringify(body)
  const res = await fetch(url, opts)
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    // FastAPI validation errors return detail as an array of {loc, msg, type} objects
    const detail = err.detail
    if (Array.isArray(detail)) {
      const msgs = detail.map(d => d.msg || JSON.stringify(d)).join('; ')
      throw new Error(msgs || 'Validation error')
    }
    throw new Error(typeof detail === 'string' ? detail : 'Request failed')
  }
  return res.json()
}

const get = (path) => req('GET', path)
const post = (path, body) => req('POST', path, body)

// ── Onboarding ────────────────────────────────────────────────────────────────
export const api = {
  onboarding: {
    status: (uid) => get(`/onboarding/status?user_id=${uid}`),
    question: (uid) => get(`/onboarding/question?user_id=${uid}`),
    answer: (uid, question_key, answer) =>
      post('/onboarding/answer', { user_id: uid, question_key, answer }),
  },

  // ── Profile ───────────────────────────────────────────────────────────────
  profile: {
    get: (uid) => get(`/profile?user_id=${uid}`),
  },

  // ── Check-In ─────────────────────────────────────────────────────────────
  checkin: {
    start: (uid) => get(`/checkin/start?user_id=${uid}`),
    // Backend schema expects: energy (not energy_level), stress (required), sleep_quality, mood_note
    submit: (uid, energy, mood_note, sleep_hours, wins, blockers) =>
      post('/checkin', {
        user_id: uid,
        energy,
        stress: 5.0,          // form doesn't collect stress; default to neutral (5/10)
        sleep_quality: sleep_hours ? Math.min(10, sleep_hours) : 7.0,
        mood_note: [wins, blockers, mood_note].filter(Boolean).join(' | '),
      }),
  },

  // ── Habits ───────────────────────────────────────────────────────────────
  habits: {
    list: (uid) => get(`/habits?user_id=${uid}`),
    add: (uid, name, track, target_frequency) =>
      post('/habits', { user_id: uid, name, track, target_frequency }),
    complete: (uid, habit_id, note) =>
      post('/habits/complete', { user_id: uid, habit_id, note }),
  },

  // ── Coach ─────────────────────────────────────────────────────────────────
  coach: {
    respond: (uid, context, goal, track) =>
      post('/coach/respond', { user_id: uid, context, goal, track }),
    message: (uid, message, session_id, goal, track) =>
      post('/coach/conversations/message', {
        user_id: uid, message, session_id: session_id || '', goal: goal || '', track: track || 'general',
      }),
    firstRead: (uid) => get(`/coach/first-read?user_id=${uid}`),
    markFirstReadDelivered: (uid) =>
      post(`/coach/first-read/delivered?user_id=${uid}`, {}),
    trialClosing: (uid) => get(`/coach/trial-closing?user_id=${uid}`),
    memorySummary: (uid) => get(`/coach/memory-summary?user_id=${uid}`),
  },

  // ── Commitments ───────────────────────────────────────────────────────────
  commitments: {
    open: (uid) => get(`/commitments/open?user_id=${uid}`),
    history: (uid) => get(`/commitments/history?user_id=${uid}`),
    create: (uid, commitment_text, due_date) => {
      // Backend requires due_date as a YYYY-MM-DD string — default to 7 days out if not provided
      const d = due_date || new Date(Date.now() + 7 * 86400000).toISOString().slice(0, 10)
      return post('/commitments', { user_id: uid, commitment_text, due_date: d })
    },
    checkin: (uid, commitment_id, status, user_note) =>
      post(`/commitments/${commitment_id}/check-in`, { user_id: uid, status, user_note }),
  },

  // ── Push Notifications ───────────────────────────────────────────────────
  push: {
    getVapidKey: () => get('/push/vapid-public-key'),
    subscribe: (uid, endpoint, p256dh, auth) =>
      post('/push/subscribe', { user_id: uid, endpoint, p256dh, auth, user_agent: navigator.userAgent }),
    unsubscribe: (endpoint) =>
      post('/push/unsubscribe', { endpoint }),
  },

  // ── Spiritual Wisdom ──────────────────────────────────────────────────────
  wisdom: {
    daily: (uid) => get(`/wisdom/daily?user_id=${uid}`),
    ask: (uid, question) => post('/wisdom/ask', { user_id: uid, question }),
    corpus: () => get('/wisdom/corpus'),
  },

  // ── Metrics & Progress ────────────────────────────────────────────────────
  metrics: {
    energy: (uid, days = 30) => get(`/metrics/energy?user_id=${uid}&days=${days}`),
    achievements: (uid) => get(`/metrics/achievements?user_id=${uid}`),
  },

  // ── Council ───────────────────────────────────────────────────────────────
  council: {
    ask: (uid, question, history = []) =>
      post('/council/ask', { user_id: uid, question, history }),
  },

  // ── Health ────────────────────────────────────────────────────────────────
  health: () => get('/healthz'),
}
