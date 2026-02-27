# Coach App — Deployment Guide
## Two iPhones. Zero cost. 15 minutes.

This guide gets the app running on your iPhone and your dad's iPhone as a
Progressive Web App (PWA) — looks and behaves like a native app on the home screen.

---

## What you'll do

1. Deploy the **backend** (FastAPI) to Render — it may already be there
2. Deploy the **frontend** (React PWA) to Vercel — free, takes 3 minutes
3. Open the URL in Safari on each iPhone → Add to Home Screen

---

## Step 1 — Backend on Render

Your backend is already configured. If it's not yet deployed:

1. Go to https://render.com and sign in (or create a free account)
2. Click **New → Web Service**
3. Connect your GitHub repo
4. Settings:
   - **Build command:** `pip install -r requirements.txt`
   - **Start command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Environment:** Python 3
   - **Plan:** Free
5. Add environment variables:
   - `OPENAI_API_KEY` → your OpenAI key (get from platform.openai.com)
6. Deploy. Note your URL: `https://your-service-name.onrender.com`

**Test it:** Visit `https://your-service-name.onrender.com/healthz` — should return `{"status":"ok"}`

---

## Step 2 — Add your backend URL to the frontend

1. Open the file: `frontend/.env.local`
2. Replace the URL with your actual Render URL:
   ```
   VITE_API_URL=https://your-service-name.onrender.com
   ```
3. Save the file.

---

## Step 3 — Deploy the frontend to Vercel

### Option A — Vercel CLI (recommended, 3 commands)

```bash
# Install Vercel CLI
npm install -g vercel

# Go to the frontend folder
cd frontend

# Deploy (follow the prompts — all defaults are fine)
vercel --prod
```

During the prompts:
- **Set up and deploy?** → Y
- **Which scope?** → your personal account
- **Link to existing project?** → N (first time)
- **Project name?** → `coach-app` (or anything)
- **Directory?** → `./` (already in frontend)
- **Override settings?** → N

Vercel will give you a URL like: `https://coach-app-xyz.vercel.app`

### Option B — Vercel website (no command line)

1. Go to https://vercel.com and sign in with GitHub
2. Click **Add New → Project**
3. Import your GitHub repo
4. Set **Root Directory** to `frontend`
5. Add environment variable: `VITE_API_URL` = your Render URL
6. Click **Deploy**

---

## Step 4 — Update CORS on the backend

After Vercel gives you a URL, add it to the backend so the browser can connect.

Open `app/main.py` and find this section (around line 110):

```python
_CORS_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:3000",
    # Vercel deployments: add your Vercel URL here after first deploy
    # "https://your-app.vercel.app",
]
```

Uncomment and update the Vercel line:
```python
    "https://coach-app-xyz.vercel.app",  # ← your actual Vercel URL
```

Then redeploy the backend on Render (it auto-deploys if connected to GitHub).

**Alternative (no code change):** In Render, add an environment variable:
- Key: `CORS_ORIGINS`
- Value: `https://your-vercel-url.vercel.app`

---

## Step 5 — Install on your iPhone

1. Open **Safari** on your iPhone (must be Safari, not Chrome)
2. Go to your Vercel URL: `https://coach-app-xyz.vercel.app`
3. Tap the **Share** button (box with arrow at the bottom)
4. Scroll down and tap **"Add to Home Screen"**
5. Name it **"Coach"** → tap **Add**

The app icon now appears on your home screen. Tap it — it opens full-screen, no browser bar.

**For your dad's iPhone:**
- Send him the Vercel URL via WhatsApp
- He opens it in Safari and follows the same steps (Share → Add to Home Screen)
- His account is separate — the app gives each device its own user ID automatically

---

## Step 6 — First launch

When you first open the app, it will:
1. Ask you ~12 onboarding questions (takes about 5 minutes)
2. Build your coach profile
3. Generate your **First Read** — a personality synthesis (appears on the dashboard)

Your dad does the same when he opens it on his phone.

---

## User IDs

Each device gets its own user ID stored locally. This means:
- Your data and dad's data are completely separate
- If dad clears his browser storage, he'll start a new profile
- You can find your user ID in the browser: Settings → Developer → Local Storage → `coach_user_id`

---

## Troubleshooting

**"Cannot connect to backend"**
- Check that the Render service is not sleeping (free tier sleeps after 15min)
- Visit the Render URL directly in a browser to wake it up
- The first request after sleep takes ~30 seconds

**"Onboarding keeps failing"**
- Check that `VITE_API_URL` in `.env.local` matches your actual Render URL exactly
- Make sure there's no trailing slash in the URL

**"App doesn't update after I redeploy"**
- Close the app from the app switcher, reopen it
- Or: Settings → Safari → Clear History and Website Data (last resort)

---

## Development (local testing on Mac)

```bash
# Terminal 1 — backend
cd "New project"
pip install -r requirements.txt
uvicorn app.main:app --reload

# Terminal 2 — frontend
cd "New project/frontend"
npm install
npm run dev
```

Then open http://localhost:5173 in your browser.

---

## Cost summary

| Service | Plan | Cost |
|---------|------|------|
| Render (backend) | Free | $0 |
| Vercel (frontend) | Free | $0 |
| OpenAI API | Pay-per-use | ~$0.01-0.10/day for 2 users |
| Apple Developer | Not needed | $0 |
| **Total** | | **~$1-3/month** |

When you're ready to go to paid users, upgrade Render to the $7/month plan (no more sleep) and keep Vercel free.
