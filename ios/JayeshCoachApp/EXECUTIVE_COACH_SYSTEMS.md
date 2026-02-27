# What a Real Executive Coach Actually Does
### The Full System — Built Into This App

---

## The Question That Built This

> *"If I hire Robin Sharma right now, what will he do? Would his only job be answering my calls?
> What all things will he proactively do? What systems will he make me adopt?
> What rituals would he teach me? What accountability would he force me to have?"*

This document answers that question completely.
Every answer is implemented in the app.

---

## The Fundamental Difference

A mediocre coach answers questions.
A great coach **installs operating systems**.

When Robin Sharma takes on a CEO client, he does not sit and wait for them to ask how to handle a board meeting. He shows up **before the board meeting** with a ritual, a framework, and an accountability structure. He **notices** what the client cannot see about themselves. He **enforces** commitments when the client wants to avoid them.

This app does all of that. Here is how.

---

## The 7 Systems a Real Executive Coach Installs

---

### System 1: The Morning Architecture

**What Robin Sharma would do:**
Day one, he would ask: "Walk me through your morning." Then he would redesign it entirely.
He would not suggest a morning routine. He would *assign* one, customised to your life, and make you accountable for it every single week.

**What the app does:**
Every morning, before the user opens anything else, the app delivers the **Morning Intelligence Brief** — a personalised 5-point brief that includes:

1. Yesterday's energy reading and what it means for today
2. A 7-day trend signal (if burnout is building, the coach flags it before the user feels it)
3. The commitment the user made last Sunday — and whether they've taken action yet
4. Habit momentum from the last 3 days — positive reinforcement or a gentle flag
5. One insight from what the coach has been studying this week

This is not a notification. This is what a coach who read your data this morning would say to you before you leave the house.

**Endpoint:** `GET /coach/proactive/morning-brief?user_id=...`

---

### System 2: The Evening Power Review

**What Robin Sharma would do:**
He would require a nightly ritual. Not a journal. Not a to-do list review. Three specific questions, answered honestly, every single night. No exceptions. Because the quality of your reflection determines the quality of your growth.

**What the app does:**
At 8pm (configurable), the app sends a notification:
*"Your coach has three questions. 5 minutes. No excuses."*

The three questions:
1. What is the single most important thing you accomplished today?
2. What is the one thing you wish you had done differently?
3. Who did you show up for today — and was it enough?

The coach reads the answers and returns one observation — a pattern it noticed, a blindspot it caught, a challenge for tomorrow. Not a summary. Not a reflection. A **coaching observation**.

**Endpoint:** `GET /coach/proactive/evening-questions` + `POST /coach/proactive/evening-review`

---

### System 3: The Weekly Accountability Architecture

**What Robin Sharma would do:**
Every Sunday evening, a real coach calls. The call has a structure. It is not a conversation — it is a ritual. The same format, every week, with no exceptions for travel, busyness, or bad weeks. *Especially* bad weeks.

**What the app does:**
Every Sunday, the **Weekly Reflection Ritual** activates:
- 3 questions: Biggest win. Biggest lesson. One binding commitment for next week.
- The coach synthesises the week using that week's energy scores, habit completion rate, and the answers
- One commitment is extracted and made explicit — it will appear in every Morning Brief that follows
- At the end of 4 weeks, the **Coach's Notebook** is updated with pattern observations

The word "binding" is used intentionally. The coach treats commitments as contracts with the self.

**Endpoint:** `POST /reflection/weekly`

---

### System 4: The Coach's Notebook (Pattern Recognition)

**What Robin Sharma would do:**
After 30-60 days with a CEO, Robin Sharma would know things about them that they do not know about themselves. He would notice: "You always crash on Wednesdays." "You always overcommit when you're in high-stress months." "You use busyness as a defence against emotional conversations." He would name these patterns — and naming them changes everything.

**What the app does:**
The **Coach's Notebook** runs weekly, reading all available data:
- Check-in energy scores by day of week (to find the Wednesday crash pattern)
- Mood notes across check-ins (keyword frequency for dominant stressors)
- Habit completion by habit name (to find the "I keep starting but not finishing" pattern)
- Reflection commitments across 4 weeks (to track follow-through vs. avoidance)

It writes 3-5 observations in plain English. These are not summaries. They are **noticing**.

*"You have mentioned board pressure in 7 of the last 14 sessions. This is the dominant stressor."*
*"Your energy peaks on Monday and crashes by Wednesday. What is scheduled on Wednesdays?"*
*"Your meditation habit is at 28% completion over 14 days. This is a design problem, not a motivation problem."*

**Endpoint:** `GET /coach/proactive/coach-notebook?user_id=...`

---

### System 5: The Relationship Maintenance Protocol

**What Robin Sharma would do:**
He would ask, in the first session: "Name the 5 relationships most critical to your happiness and success." Then, every single session thereafter, he would ask: "How are things with [each of those people]?" Because he knows that the biggest failures in executive life — the burnout, the divorce, the broken partnership — come from neglected relationships, not failed strategies.

**What the app does:**
Onboarding question 3 captures **key relationships** (partner, co-founder, board chair, etc.).

Every 10 days, if a named relationship hasn't appeared in any check-in or coaching conversation, the coach sends a proactive nudge:
*"You haven't mentioned [your partner] in 12 days. How are things at home? Sometimes the most important relationship gets the least intentional attention. Is that true here?"*

When a user mentions conflict language in a check-in ("fight," "argument," "upset"), the coach immediately routes the conversation to **relationship coaching mode** — using the Gottman framework and ICF conversation-prep structure.

**Endpoint:** `GET /coach/proactive/relationship-nudges?user_id=...`

---

### System 6: The Decision Accountability Framework

**What Robin Sharma would do:**
Before any big decision, he would sit with the client for a structured pre-mortem: "Imagine it's 12 months from now and this decision failed. What happened?" Then he would push back on the reasoning, surface the assumptions, and make the client commit to a decision on paper — with a review date.

**What the app does:**
When the user mentions a big decision in any coaching conversation (detected by keywords: "decision," "choosing," "considering," "should I"), the coach activates the **Decision Pre-Mortem Protocol**:

1. What is the decision?
2. What could go wrong in the best realistic scenario?
3. Who else will be affected by this — and have you thought about them?
4. What does your gut say, separate from your analysis?

The coach then issues a recommendation with explicit reasoning, and saves it to the **Decision Log**. Every 30 days, the coach reviews: "Here are 3 decisions you made last month. What actually happened? What pattern do you see in how you decide?"

*(Decision Log — coming in V2)*

---

### System 7: The Proactive Reading System

**What Robin Sharma would do:**
He would assign reading. Every week, one book, one article, one framework — specific to what you're working through. And he would *ask you about it* the following week, which means you actually read it.

**What the app does:**
Every Monday, the **Weekly Reading Assignment** is generated:
- The coach selects one item from its living knowledge base (recently ingested via PubMed + manual curation)
- It is matched to the user's dominant coaching track (leadership, energy, relationships)
- The assignment includes: the title, the key takeaway, the personal application, and one question the coach will ask about it on Sunday

This is not a reading list. It is an assignment with accountability built in.

**Endpoint:** `GET /coach/proactive/reading-assignment?user_id=...`

---

## The Voice Dimension

A great coach does not communicate only in text.
The voice is the most direct path to real presence.

**What the app will do (V2 iOS):**
The user holds one button. Speaks. The app listens — not just to the words, but to the *voice*:
- Slow speech + flat affect → energy is low, coach goes softer and more direct
- Fast speech + high pitch → elevated stress or excitement, coach goes grounding and calm
- Broken speech + pauses → something emotional is happening, coach goes present before advice

The iOS app uses AVAudioEngine to extract:
- Speaking rate (words per minute)
- Pitch variance
- Pause frequency

These become the `tone_hint` field sent to the API. The backend uses it to modify the coaching register.

The response comes back in **a beautiful Indian woman's voice** — warm, authoritative, unhurried. Not a robot. Not a generic Western voice. Someone who sounds like she understands your world.

**Why this matters:** High-earning Indian professionals think in Hindi but present in English. The emotional register of their mother tongue is richer. A voice that carries that warmth — the directness, the care, the familiarity of a didi or a wise colleague — creates trust that text never can. This is a deep competitive differentiation.

Implementation:
- **Speech-to-text:** Whisper API (runs in iOS layer, sends transcript to API)
- **Text-to-speech:** ElevenLabs with a custom Indian-English voice, or OpenAI TTS `nova` / `shimmer` voices as fallback
- **Tone analysis:** iOS native (AVAudioEngine before Whisper transcription)

**Endpoint:** `POST /coach/voice`

---

## The Conversational Check-In

The old way: "Enter energy 1-10, stress 1-10, sleep 1-10."
The real way: "How are you waking up today? What's the first thing on your mind?"

A real coach never opens a session with a form.
They open with a question and listen.

**What the app now does:**
When the user opens the check-in:

1. Coach opens: *"Good morning, Jayesh. Before the day pulls you in — how are you, really?"*
2. User responds in natural language (text or voice)
3. Coach extracts energy, stress, sleep quality, and emotional tone from the response
4. If the response is ambiguous, coach asks one targeted follow-up question
5. Once signals are extracted, coach issues a full coaching response
6. Data is saved to the same DailyCheckIn model — fully backward compatible

If the user says *"Oh my God, I just had a terrible fight with my wife"* — the system detects the relationship flag, routes to relationship coaching mode, and responds with Gottman-based repair guidance — not a burnout alert.

**The app meets the user where they are, not where the form expects them to be.**

**Endpoint:** `GET /checkin/start` + `POST /checkin/converse`

---

## The Full Proactive Coaching Schedule

| Trigger | What the Coach Does | Endpoint |
|---|---|---|
| Every morning | Morning Intelligence Brief | `GET /coach/proactive/morning-brief` |
| Every evening 8pm | Evening Power Review (3 questions) | `GET /coach/proactive/evening-questions` |
| Every Sunday | Weekly Reflection + Commitment Extraction | `POST /reflection/weekly` |
| Every Monday | Weekly Reading Assignment | `GET /coach/proactive/reading-assignment` |
| Every week | Coach's Notebook update (pattern recognition) | `GET /coach/proactive/coach-notebook` |
| Every 10 days | Relationship nudge if key person not mentioned | `GET /coach/proactive/relationship-nudges` |
| Any big decision detected | Decision Pre-Mortem activation | (in conversation flow) |
| Low energy 3 days in a row | Burnout intervention | (in morning brief + check-in alert) |

---

## The One Sentence That Defines This

*"A mediocre coach answers your questions. A great coach changes the questions you ask yourself."*

This app is designed to do the second thing — every single day, without being asked.

---

*Last updated: V2 planning phase*
