# Coach App — Full Feature Roadmap
### From Personal Tool to Premium Coaching OS for High Earners

---

## The Vision

Most apps talk at you. This one listens, remembers, studies, and grows with you.

Every other productivity or coaching app gives everyone the same experience. This one knows your name, your mission, your biggest relationship challenge, your energy trends, and the frameworks your coach has been studying this week — and it uses all of that, every single time you open it.

This is not another wellness app. This is a personal operating system for people who lead at the highest level and take their inner life as seriously as their results.

---

## What Is Already Built (V1 — Backend Complete)

| Feature | Status | Description |
|---|---|---|
| Onboarding Interview | DONE | 8-question intake that builds a full UserProfile |
| Personalised Coaching | DONE | Every response references user's actual goals and stressors |
| Encrypted Conversation Memory | DONE | Full history, retention-controlled, Fernet-encrypted |
| Daily Check-In / Burnout Sentinel | DONE | 30-second check-in with 7-day trend tracking and alerts |
| Habit Compounding | DONE | Track keystone habits, streaks, and weekly completion rate |
| Weekly Reflection Ritual | DONE | Sunday synthesis with coach-generated commitment |
| Living Knowledge Base | DONE | DB-backed, PubMed-ingested, replacing static catalog |
| Smart Knowledge Retrieval | DONE | Recency + tag + quality scoring for every coaching call |
| Manual Knowledge Curation | DONE | Add any paper, book, or framework via API |
| "What Your Coach Is Studying" | DONE | Users see recently ingested items — builds trust |

---

## V2 — The Features That Justify Premium Pricing

### 1. Morning Intelligence Brief
**Every morning, personalised to that exact day.**

The coach looks at: your calendar (via CalDAV/Google Calendar sync), your last check-in, your 90-day goals, and what's currently in your knowledge base. It generates a 5-bullet brief:

- Your energy yesterday was 6/10. Today's priority: protect one deep-work block.
- You have 3 back-to-back meetings. Block 10 minutes before your board call to centre.
- Your commitment last Sunday was to repair the conversation with your deputy. You have not logged any action on this. Today is the day.
- Your coach this week studied: _Emotional Regulation in High-Stakes Leadership_ (Stanford, 2025). Key takeaway: leaders who pause 6 seconds before reacting make decisions their future self respects.
- One sentence to carry today: "Calm is a leadership choice, not a personality trait."

**Why this is powerful:** No other app does this. This is what a real personal assistant does — but for your inner life.

---

### 2. Relationship Tracker
**For each key relationship named in onboarding, the coach keeps a living record.**

For every person (partner, board member, co-founder, parent):
- Date of last meaningful interaction
- Current health score (1-10, updated after every relevant coaching session)
- Pending repair items (flagged automatically when conflict language appears in conversations)
- Upcoming important dates (birthday, big meeting, anniversary)
- A 30-day trend graph

The coach proactively prompts: "You haven't mentioned your partner in 12 days. How are things at home?"

This is the feature that makes high-earning professionals emotional about the app.

---

### 3. Decision Log with Pre-Mortem Framework
**Before any big decision: structured thinking. After: accountability.**

When a user says "I have a big decision to make," the coach:
1. Asks 4 questions (What is the decision? What could go wrong? Who else is affected? What does your gut say?)
2. Runs a structured pre-mortem (imagine it failed — why?)
3. Issues a recommendation with the reasoning made explicit
4. Saves the decision + reasoning to the Decision Log

Every 30 days, the coach reviews: "Here are 3 decisions you made last month. How did they turn out? What pattern do you notice?"

Over time, users see their own decision-making patterns clearly. That is worth $500/month alone.

---

### 4. Voice Capture → Coaching Loop
**The fastest path from thought to coaching action.**

User holds down a button, speaks for 30 seconds: "Just had a horrible board meeting. Felt undermined in front of the whole team. Really angry right now."

The app:
1. Transcribes (Whisper API)
2. Detects emotion + track (relationship + leadership)
3. Fires an immediate coaching response: centering, reframe, 3 actions
4. Optionally saves to conversation history

This is the feature that fits into real life. In a car. After a tough meeting. Before a difficult conversation.

---

### 5. Conflict Preparation Script
**Before any difficult conversation: the coach walks you through it.**

User says: "I need to have a hard conversation with my CFO tomorrow about performance."

Coach runs the Gottman soft-startup framework + ICF pre-conversation structure:
- What is the core issue? (separate behaviour from character)
- What is your part in this?
- What do you want the relationship to look like after this conversation?
- Here is your opening line. Here is what to say if it escalates. Here is how to end it well.

User goes into the conversation prepared, not reactive.

---

### 6. Coach's Notebook (Pattern Recognition)
**The coach maintains a private notebook about each user.**

Every week, the AI reads the user's check-ins, habit completions, conversations, and reflections, and writes 3 sentences:
- "You tend to lose energy mid-week when you have more than 4 meetings on Wednesday."
- "Your relationship conversations happen most frequently on Sunday evenings — you're doing the work."
- "You have mentioned 'board pressure' in 7 of the last 14 sessions. This is the dominant stressor."

Users can ask at any time: "What patterns do you notice in me?" and the coach synthesises from everything it knows.

This is what transforms the app from a tool to a relationship.

---

### 7. 90-Day Sprint Dashboard
**Visual progress on the goals set during onboarding.**

For each 90-day goal:
- A progress bar updated from coaching conversations (when user says "I completed X", the coach updates it)
- Weekly check-in question specific to that goal
- 30/60/90 day milestones
- Coach-generated forecast: "At your current pace, you will achieve this goal. Here is what would accelerate it."

---

### 8. Bilingual Coaching (English + Hindi)
**For Indian users: the coach speaks their full emotional language.**

Many high-earning Indian professionals think in Hindi but present in English. Emotional vocabulary is richer in the mother tongue.

The app detects when the user writes in Hindi (or mixed) and responds in kind. Onboarding preference captures this. The coaching style ("bhai", warmth, directness, family-centric framing) adapts.

This is a differentiated feature for the Indian premium market — and it is deeply personal.

---

## V3 — The Features That Create a Category

### 9. HealthKit Integration (iOS)
**Physical data informing emotional coaching.**

When the user consents: resting heart rate, HRV, sleep data, and step count flow in automatically. The coach sees:
- "Your HRV dropped 20% this week. Your body is under more stress than your words suggest."
- "You slept 5.5 hours for 3 consecutive nights. Your energy score reflects this. Let's talk about what's in the way."

Evidence-based connection between physical metrics and leadership capacity.

---

### 10. Monthly Coaching Report
**A beautifully designed PDF that users actually want to re-read.**

At the end of every month:
- Energy and stress trends (visualised)
- Habit completion chart
- Biggest wins and lessons from Weekly Reflections
- Knowledge highlights (what the coach studied this month + how it applied to you)
- One paragraph from the Coach's Notebook
- Goal progress across all 3 tracks

This is the artifact that makes users renew. It is proof that the coaching is working. It is something they show their spouse, their therapist, their business partner.

---

### 11. Team / Family Edition
**The same philosophy, shared across a small trusted circle.**

A CEO and their leadership team each have individual profiles. The CEO can see (with consent) team-level energy trends — not individual data, but aggregate signals.

A parent and spouse can share a "family track" where they both log relationship health, and the coach facilitates a shared weekly reflection.

This is the network effect. When one person pays, they invite others.

---

## Pricing Architecture

| Tier | Price | For | Key Value |
|---|---|---|---|
| Essential | $49/month | Professional individual | Onboarding + daily coaching + habits + check-in |
| Executive | $149/month | Senior leader / founder | + Morning brief + Relationship tracker + Decision log + Voice capture |
| Chairman | $499/month | CEO / board member | + Monthly report + Coach's notebook + HealthKit + bilingual |
| Concierge | $2,000/month | One dedicated user (Papa-style) | All features + weekly human coach review of AI output |

---

## Why This Wins Against Every Competitor

**BetterUp** — corporate, group-focused, generic, no persistent memory. $200-500/month with a human coach who sees you once a week and forgets everything by next session.

**Headspace / Calm** — meditation apps with no coaching, no memory, no personalisation.

**ChatGPT** — powerful but blank slate every session. No profile, no history, no proactive intelligence.

**Tony Robbins / MasterClass** — passive content consumption. No accountability, no feedback loop.

**This app** — knows you, remembers you, studies for you, grows with you, and costs a fraction of a human coach. For a high earner, $149/month is one hour with a decent consultant. This gives them 30 days of daily intelligence.

---

## The One Sentence Pitch

*"Your private coach — the one who actually reads, remembers everything you've told them, and shows up every morning with exactly what you need."*
