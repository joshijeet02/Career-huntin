# Coach App — Deployment Guide (v2)
### Two iPhones. Zero cost. Step-by-step with screenshots context.

---

## Overview

| Step | What | Where | Time |
|------|------|--------|------|
| 1 | Deploy backend | Render.com | 5 min |
| 2 | Deploy frontend | Vercel.com | 3 min |
| 3 | Connect them | Terminal | 1 min |
| 4 | Install on iPhone | Safari | 2 min |

---

## Step 1 — Deploy Backend on Render

### 1a. Create the Web Service

1. Go to [render.com](https://render.com) → sign in → click **New → Web Service**
2. Click **Connect a repository** → select **Career-huntin**
3. You'll see a form. Fill it in exactly:

| Field | Value |
|-------|-------|
| **Name** | `coach-app` (or anything you like) |
| **Language** | ⚠️ **Python 3** — change this from "Docker" if needed |
| **Branch** | `main` |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| **Plan** | Free |

> ⚠️ **Important:** Render may auto-select "Docker" because there's a Dockerfile in the repo.
> You **must change Language to "Python 3"** — the Build/Start command fields only appear after you do this.

### 1b. Add your OpenAI API key

Scroll down to **Environment Variables** and add:

| Key | Value |
|-----|-------|
| `OPENAI_API_KEY` | your key from [platform.openai.com/api-keys](https://platform.openai.com/api-keys) |

### 1c. Deploy

Click **Create Web Service**. First build takes ~3-5 minutes.

Your backend URL will be something like: `https://coach-app-xxxx.onrender.com`

### 1d. Test it

Open this in your browser:
```
https://coach-app-xxxx.onrender.com/healthz
```
You should see: `{"status":"ok"}`

> **Free tier note:** Render sleeps after 15 min of no traffic. The first request after sleep takes ~30 seconds. This is fine for 2 test users.

---

## Step 2 — Update the Backend URL in the Frontend

Your frontend already has a file called `.env.local` with the API URL. There are two ways to update it:

### Option A — Terminal command (easiest, 1 line)

Open **Terminal** on your Mac and run:

```bash
echo 'VITE_API_URL=https://YOUR-RENDER-URL.onrender.com' > "/Users/jeetjoshi/Documents/New project/frontend/.env.local"
```

Replace `YOUR-RENDER-URL` with your actual Render service name. Example:
```bash
echo 'VITE_API_URL=https://coach-app-abc123.onrender.com' > "/Users/jeetjoshi/Documents/New project/frontend/.env.local"
```

### Option B — Skip this step entirely

If you deploy the frontend via Vercel's website (Step 3, Option B), you can set `VITE_API_URL` as an environment variable in Vercel's dashboard instead — no file editing needed. **This is the easiest approach.**

### Why you can't see .env.local in Finder

The file starts with a dot (`.`), which means Mac hides it by default. To show hidden files in Finder:
- Press **Cmd + Shift + .** (Command + Shift + Period)
- Hidden files will now appear greyed out
- Press the same shortcut again to hide them

---

## Step 3 — Deploy Frontend to Vercel

### Option A — Vercel Website (no command line needed ✅ Recommended)

1. Go to [vercel.com](https://vercel.com) → sign in with GitHub
2. Click **Add New → Project**
3. Find and import **Career-huntin** from your GitHub repos
4. Vercel will auto-detect it. Before clicking Deploy, set:
   - **Root Directory** → click Edit → type `frontend` → click Continue
5. Expand **Environment Variables** and add:
   - Key: `VITE_API_URL`
   - Value: `https://coach-app-xxxx.onrender.com` (your actual Render URL)
6. Click **Deploy**

Vercel will give you a URL like: `https://coach-app-xyz.vercel.app`

---

### Option B — Terminal (3 commands)

```bash
# 1. Go to your frontend folder
cd "/Users/jeetjoshi/Documents/New project/frontend"

# 2. Install Vercel CLI (one-time)
npm install -g vercel

# 3. Deploy
npx vercel --prod
```

Follow the prompts:
- **Set up and deploy?** → Y
- **Which scope?** → your personal account
- **Link to existing project?** → N
- **Project name?** → `coach-app`
- **Directory?** → `./` (just press Enter)
- **Override settings?** → N

---

## Step 4 — Allow the Frontend to Talk to the Backend (CORS)

After Vercel gives you a URL, you need to add it to the backend's allowed list.

**Easiest way — Render environment variable (no code change):**

1. Go to your Render service dashboard
2. Click **Environment** in the left sidebar
3. Add a new variable:
   - Key: `CORS_ORIGINS`
   - Value: `https://your-app.vercel.app` (your actual Vercel URL)
4. Click **Save Changes** — Render will auto-redeploy

---

## Step 5 — Install on iPhone

### Your iPhone:
1. Open **Safari** (must be Safari, not Chrome or Firefox)
2. Go to your Vercel URL: `https://coach-app-xyz.vercel.app`
3. Tap the **Share** button at the bottom (box with an arrow pointing up)
4. Scroll down in the share sheet and tap **"Add to Home Screen"**
5. Name it **"Coach"** → tap **Add**

The app icon now appears on your home screen. Tap it — it opens full-screen, no browser bar.

### Dad's iPhone:
- Send him the Vercel URL via WhatsApp
- He opens it in **Safari** and does the same steps (Share → Add to Home Screen)
- His profile is completely separate — he gets his own user ID automatically

---

## Step 6 — First Time Using the App

When you open it for the first time:
1. You'll go through ~12 onboarding questions (about 5 minutes)
2. The app builds your coach profile
3. Your **First Read** (a personality synthesis) appears on the dashboard after onboarding

Your dad does the same flow separately on his phone.

---

## Troubleshooting

**"Cannot connect" or blank screen**
- Your Render URL in `.env.local` or Vercel env var might be wrong — double-check it has no trailing slash
- Visit `https://your-render-url.onrender.com/healthz` in a browser to test the backend directly

**Render is showing Docker, not Python 3**
- On the Render New Web Service form, click the **Language** dropdown (it says "Docker") and change it to **Python 3**
- The Build Command and Start Command fields will appear below after you switch

**Backend takes 30 seconds on first request**
- Normal on the free tier — Render sleeps after 15 min of inactivity
- Just wait for it to wake up; all subsequent requests are fast

**Can't find .env.local in Finder**
- It's a hidden file. Press **Cmd + Shift + .** in Finder to show hidden files
- Or use the Terminal command in Step 2 Option A — it's one line and much easier

**"Add to Home Screen" not showing in Safari**
- Make sure you're using Safari (not Chrome)
- The option is in the Share sheet — scroll down past the top row of icons

**App doesn't update after redeployment**
- Close the app fully from the app switcher
- Reopen it — it will fetch the latest version automatically

---

## Local Development (testing on your Mac)

```bash
# Terminal 1 — start the backend
cd "/Users/jeetjoshi/Documents/New project"
pip install -r requirements.txt
uvicorn app.main:app --reload

# Terminal 2 — start the frontend
cd "/Users/jeetjoshi/Documents/New project/frontend"
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173) in your browser.

---

## Cost Summary

| Service | Plan | Cost |
|---------|------|------|
| Render (backend) | Free | $0/month |
| Vercel (frontend) | Free | $0/month |
| OpenAI API | Pay-per-use | ~$0.01–0.10/day for 2 users |
| Apple Developer Account | Not needed (PWA) | $0 |
| **Total** | | **~$1–3/month** |

When you're ready to launch publicly, upgrade Render to the **$7/month Starter plan** — no more sleep delays.

---

## Quick Reference — Your URLs

Fill these in once you have them:

| Thing | URL |
|-------|-----|
| Backend (Render) | `https://________________.onrender.com` |
| Frontend (Vercel) | `https://________________.vercel.app` |
| Backend health check | `https://________________.onrender.com/healthz` |
