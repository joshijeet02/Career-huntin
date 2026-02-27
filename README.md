# Coach App — Personal AI Coaching OS

A FastAPI backend for a personalised AI coaching application.
Users complete a 10-15 minute onboarding interview; every coaching session is then built around their exact profile, goals, and relationships.

## Core Features

- **Onboarding interview** — 8-question conversational intake that builds a rich user profile
- **Fully personalised coaching** — every response references the user's actual goals, stressors, and relationships
- **Multi-turn conversation memory** — encrypted at rest, retention-controlled
- **Research-backed intelligence** — coaching grounded in published science (PubMed, JAMA, Gottman, WHO)
- **Premium tier blueprint** — tiered subscription model ready for iOS monetisation

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/onboarding/status` | Check onboarding progress for a user |
| GET | `/onboarding/question` | Get the current onboarding question |
| POST | `/onboarding/answer` | Submit answer and advance to next step |
| GET | `/profile` | Retrieve the completed user profile |
| POST | `/coach/respond` | Single-turn personalised coaching response |
| POST | `/coach/conversations/message` | Multi-turn coaching with persistent history |
| GET | `/coach/conversations/history` | Retrieve conversation history |
| POST | `/coach/conversations/retention/run` | Purge expired conversations |
| GET | `/coach/intelligence/brief` | View the coach's current research library |
| GET | `/coach/premium/tiers` | Subscription tier definitions |

## Run Locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Set OPENAI_API_KEY, BACKEND_API_KEY, APP_ENCRYPTION_KEY in .env
uvicorn app.main:app --reload
```

Open `/docs` for the interactive API explorer.

## Onboarding Flow

1. App calls `GET /onboarding/question?user_id=<id>` to get the first question
2. User answers; app posts to `POST /onboarding/answer`
3. Response includes the next question (or `complete: true` after step 8)
4. On completion, a `profile_summary` is returned to welcome the user personally
5. All subsequent `/coach/` calls include `user_id` and receive fully personalised responses

## Architecture

- **Backend**: FastAPI + SQLAlchemy + SQLite (persistent disk on Render)
- **AI**: OpenAI (gpt-4o-mini default) with local fallback coaching engine
- **Privacy**: Fernet encryption for all conversation storage
- **iOS**: SwiftUI app in `/ios/JayeshCoachApp` (TestFlight pipeline planned)

## Deploy on Render

1. Push to GitHub
2. Render Dashboard → New → Blueprint → select repo
3. Render auto-detects `render.yaml` and creates the service
4. After deploy: `/docs` for API explorer, `/healthz` for health check

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | Optional | Enables GPT-powered coaching (falls back to local engine if not set) |
| `BACKEND_API_KEY` | Optional | API key auth for all routes |
| `APP_ENCRYPTION_KEY` | Required | Fernet key for conversation encryption |
| `COACH_RETENTION_DAYS` | Optional | Days to retain conversation history (default: 90) |
| `OPENAI_COACH_MODEL` | Optional | Override OpenAI model (default: gpt-4o-mini) |

## Tests

```bash
pytest -q
```
