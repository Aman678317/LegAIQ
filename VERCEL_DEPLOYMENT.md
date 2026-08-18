# Deploying Jurisiva AI Frontend on Vercel

This guide walks you step-by-step through deploying the **Next.js Frontend** to [Vercel](https://vercel.com).

---

## 1. Required Environment Variables

When deploying to Vercel, configure these variables under **Project Settings → Environment Variables**:

| Variable Name | Description | Example Production Value |
| :--- | :--- | :--- |
| `NEXT_PUBLIC_APP_URL` | Your live frontend URL on Vercel | `https://your-frontend-app.vercel.app` |
| `NEXT_PUBLIC_API_URL` | Live backend API URL (FastAPI `/api/v1`) | `https://jurisiva-api.onrender.com/api/v1` |
| `NEXT_PUBLIC_SUPABASE_URL` | Your Supabase project URL | `https://your-project-id.supabase.co` |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Your Supabase anonymous public key | `eyJhbGciOiJIUzI1NiIsIn...` |
| `NEXT_PUBLIC_OLLAMA_URL` *(Optional)* | Self-hosted Ollama server endpoint | `http://localhost:11434` *(or your server)* |

> **Note:** In Vercel, select all environments (**Production**, **Preview**, **Development**) for these variables.

---

## 2. Option A: Deploy via Vercel Web Dashboard (Recommended)

1. **Push your code to GitHub / GitLab / Bitbucket**:
   Ensure all changes are committed and pushed to your remote repository.

2. **Import Project to Vercel**:
   - Go to [vercel.com/new](https://vercel.com/new).
   - Select and import your GitHub repository (`Aman678317/LegAIQ`).

3. **Configure Project Settings**:
   - **Framework Preset**: `Next.js` (automatically detected).
   - **Root Directory**: Click **Edit** and set it to `frontend` *(Crucial since the repo contains both backend and frontend)*.
   - **Build Command**: `next build` (default).
   - **Output Directory**: `.next` (default).
   - **Install Command**: `npm install` (default).

4. **Add Environment Variables**:
   - Expand the **Environment Variables** section.
   - Add the 4 environment variables listed in Section 1.

5. **Click Deploy**:
   - Vercel will clone, build, and deploy the application.
   - Your frontend will be live at `https://<your-project-name>.vercel.app`.

---

## 3. Option B: Deploy via Vercel CLI

If you prefer deploying directly from your terminal:

1. **Install Vercel CLI globally**:
   ```bash
   npm install -g vercel
   ```

2. **Navigate to the frontend folder**:
   ```bash
   cd frontend
   ```

3. **Log in to your Vercel account**:
   ```bash
   vercel login
   ```

4. **Deploy Preview**:
   ```bash
   vercel
   ```
   Follow the interactive prompts:
   - Link to existing project? `N` (or `Y` if already created)
   - Project name? `jurisiva-frontend`
   - In which directory is your code located? `./`

5. **Deploy to Production**:
   ```bash
   vercel --prod
   ```

6. **Add Environment Variables via CLI (or Dashboard)**:
   ```bash
   vercel env add NEXT_PUBLIC_APP_URL production
   vercel env add NEXT_PUBLIC_API_URL production
   vercel env add NEXT_PUBLIC_SUPABASE_URL production
   vercel env add NEXT_PUBLIC_SUPABASE_ANON_KEY production
   ```

---

## 4. Post-Deployment Configuration (Essential Checklist)

### A. Backend CORS Settings
Ensure your deployed backend accepts requests from your Vercel domain.
- In your backend environment settings (e.g. Render/Railway/Docker):
  ```env
  CORS_ORIGINS=https://your-frontend-app.vercel.app,http://localhost:3000
  ```

### B. Supabase Authentication Redirect URLs
In the [Supabase Dashboard](https://supabase.com/dashboard):
1. Navigate to **Authentication** → **URL Configuration**.
2. Set **Site URL** to:
   ```
   https://your-frontend-app.vercel.app
   ```
3. Add to **Redirect URLs**:
   ```
   https://your-frontend-app.vercel.app/**
   https://your-frontend-app.vercel.app/auth/callback
   ```
4. Save changes.
