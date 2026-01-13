# Flossy Deployment Guide
## Complete Guide for Deploying with GitHub Actions & Custom Domain

---

## 📋 Table of Contents
1. [Project Overview](#project-overview)
2. [Prerequisites](#prerequisites)
3. [Architecture Overview](#architecture-overview)
4. [Domain & DNS Setup](#domain--dns-setup)
5. [Backend Deployment (FastAPI)](#backend-deployment-fastapi)
6. [Frontend Deployment (Vite/React)](#frontend-deployment-vitereact)
7. [Database Setup (PostgreSQL)](#database-setup-postgresql)
8. [GitHub Actions CI/CD](#github-actions-cicd)
9. [Environment Variables](#environment-variables)
10. [SSL/HTTPS Configuration](#sslhttps-configuration)
11. [Post-Deployment Verification](#post-deployment-verification)
12. [Troubleshooting](#troubleshooting)

---

## 🎯 Project Overview

**Flossy** is a full-stack dental clinic management system featuring:
- **Frontend**: React + Vite (flossy-ui)
- **Backend**: FastAPI + Python (flossy_backend)
- **Database**: PostgreSQL
- **Authentication**: Clerk
- **AI Integration**: Google Gemini, Groq, LiveKit Voice AI
- **PDF Generation**: ReportLab

### Project Structure
```
Flossy/
├── flossy-ui/          # React frontend (Vite)
│   ├── src/
│   ├── package.json
│   └── vite.config.js
├── flossy_backend/     # FastAPI backend
│   ├── app/
│   ├── main.py
│   └── requirements.txt
└── .github/
    └── workflows/      # GitHub Actions CI/CD
```

---

## ✅ Prerequisites

### Required Accounts
- [ ] **GitHub Account** - For repository and GitHub Actions
- [ ] **Domain Registrar** (GoDaddy, Namecheap, Cloudflare, etc.)
- [ ] **Cloud Provider** - Choose one:
  - Railway.app (Recommended - easy setup)
  - Render.com
  - DigitalOcean
  - AWS (EC2 + RDS)
  - Google Cloud Platform
- [ ] **Clerk Account** - For authentication (https://clerk.com)
- [ ] **Google Cloud** - For Gemini AI API
- [ ] **Groq Account** - For LLM API (optional)
- [ ] **LiveKit Account** - For voice AI (optional)

### Required Tools (Local)
```bash
# Node.js 18+
node --version

# Python 3.10+
python --version

# Git
git --version
```

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        YOUR DOMAIN                               │
│                    (e.g., smileartists.com)                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   ┌─────────────────┐              ┌─────────────────────────┐  │
│   │   Frontend      │              │      Backend API        │  │
│   │   (Vercel/      │   HTTPS      │    (Railway/Render)     │  │
│   │    Netlify)     │◄────────────►│                         │  │
│   │                 │              │   api.smileartists.com  │  │
│   │smileartists.com │              │                         │  │
│   └─────────────────┘              └───────────┬─────────────┘  │
│                                                │                 │
│                                                ▼                 │
│                                    ┌─────────────────────────┐  │
│                                    │     PostgreSQL DB       │  │
│                                    │    (Railway/Supabase)   │  │
│                                    └─────────────────────────┘  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🌐 Domain & DNS Setup

### Step 1: Purchase Domain
Purchase a domain from your preferred registrar (e.g., GoDaddy, Namecheap, Cloudflare).

### Step 2: Configure DNS Records

| Type | Name | Value | TTL |
|------|------|-------|-----|
| A | @ | `<Frontend IP>` | 3600 |
| CNAME | www | `<your-domain.com>` | 3600 |
| CNAME | api | `<backend-url.railway.app>` | 3600 |

**Example for smileartists.com:**
```
A     @      76.76.21.21          # Vercel IP (if using Vercel)
CNAME www    smileartists.com
CNAME api    flossy-backend.up.railway.app
```

---

## 🔧 Backend Deployment (FastAPI)

### Option A: Deploy to Railway (Recommended)

#### 1. Create Railway Account & Project
```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Initialize project in flossy_backend folder
cd flossy_backend
railway init
```

#### 2. Create `railway.toml` in `flossy_backend/`:
```toml
[build]
builder = "nixpacks"

[deploy]
startCommand = "uvicorn app.main:app --host 0.0.0.0 --port $PORT"
healthcheckPath = "/"
healthcheckTimeout = 300
restartPolicyType = "on_failure"
restartPolicyMaxRetries = 3
```

#### 3. Create `Procfile` in `flossy_backend/`:
```
web: uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
```

#### 4. Update `requirements.txt`:
```txt
fastapi==0.109.0
uvicorn[standard]==0.27.0
sqlalchemy==2.0.25
psycopg2-binary==2.9.9
python-jose[cryptography]==3.3.0
httpx==0.26.0
google-generativeai==0.3.2
groq==0.4.2
reportlab==4.0.8
python-multipart==0.0.6
python-dotenv==1.0.0
livekit==0.9.0
livekit-agents==0.7.2
```

#### 5. Deploy to Railway
```bash
railway up
```

#### 6. Add PostgreSQL Database
In Railway dashboard:
1. Click "New" → "Database" → "PostgreSQL"
2. Railway auto-injects `DATABASE_URL`

### Option B: Deploy to Render

#### 1. Create `render.yaml` in project root:
```yaml
services:
  - type: web
    name: flossy-backend
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn app.main:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: DATABASE_URL
        fromDatabase:
          name: flossy-db
          property: connectionString

databases:
  - name: flossy-db
    plan: starter
```

---

## 🎨 Frontend Deployment (Vite/React)

### Option A: Deploy to Vercel (Recommended)

#### 1. Install Vercel CLI
```bash
npm install -g vercel
```

#### 2. Create `vercel.json` in `flossy-ui/`:
```json
{
  "buildCommand": "npm run build",
  "outputDirectory": "dist",
  "framework": "vite",
  "rewrites": [
    { "source": "/(.*)", "destination": "/index.html" }
  ],
  "headers": [
    {
      "source": "/(.*)",
      "headers": [
        { "key": "X-Content-Type-Options", "value": "nosniff" },
        { "key": "X-Frame-Options", "value": "DENY" },
        { "key": "X-XSS-Protection", "value": "1; mode=block" }
      ]
    }
  ]
}
```

#### 3. Update `vite.config.js`:
```javascript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  build: {
    outDir: 'dist',
    sourcemap: false,
  },
  server: {
    port: 5173,
  },
})
```

#### 4. Deploy
```bash
cd flossy-ui
vercel --prod
```

#### 5. Add Custom Domain in Vercel Dashboard
1. Go to Project Settings → Domains
2. Add `smileartists.com` and `www.smileartists.com`
3. Follow DNS configuration instructions

### Option B: Deploy to Netlify

#### 1. Create `netlify.toml` in `flossy-ui/`:
```toml
[build]
  command = "npm run build"
  publish = "dist"

[[redirects]]
  from = "/*"
  to = "/index.html"
  status = 200
```

---

## 🗄️ Database Setup (PostgreSQL)

### Option A: Railway PostgreSQL (Included with Railway)
Automatically provisioned when you add PostgreSQL plugin.

### Option B: Supabase (Free Tier Available)
1. Create project at https://supabase.com
2. Get connection string from Settings → Database
3. Use in `DATABASE_URL` environment variable

### Option C: Neon (Serverless PostgreSQL)
1. Create account at https://neon.tech
2. Create a new project
3. Copy connection string

### Database Migration
After deployment, run migrations:
```bash
# Connect to your deployed backend
railway run python -c "from app.core.database import init_db; init_db()"
```

---

## 🔄 GitHub Actions CI/CD

### Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy Flossy

on:
  push:
    branches: [main, master]
  pull_request:
    branches: [main, master]

env:
  NODE_VERSION: '18'
  PYTHON_VERSION: '3.11'

jobs:
  # ========================================
  # FRONTEND BUILD & DEPLOY
  # ========================================
  frontend:
    name: Build & Deploy Frontend
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: ./flossy-ui

    steps:
      - name: Checkout Repository
        uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}
          cache: 'npm'
          cache-dependency-path: './flossy-ui/package-lock.json'

      - name: Install Dependencies
        run: npm ci

      - name: Build Application
        run: npm run build
        env:
          VITE_API_URL: ${{ secrets.VITE_API_URL }}
          VITE_CLERK_PUBLISHABLE_KEY: ${{ secrets.VITE_CLERK_PUBLISHABLE_KEY }}
          VITE_LIVEKIT_URL: ${{ secrets.VITE_LIVEKIT_URL }}

      - name: Deploy to Vercel
        uses: amondnet/vercel-action@v25
        with:
          vercel-token: ${{ secrets.VERCEL_TOKEN }}
          vercel-org-id: ${{ secrets.VERCEL_ORG_ID }}
          vercel-project-id: ${{ secrets.VERCEL_PROJECT_ID }}
          working-directory: ./flossy-ui
          vercel-args: '--prod'

  # ========================================
  # BACKEND BUILD & DEPLOY
  # ========================================
  backend:
    name: Build & Deploy Backend
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: ./flossy_backend

    steps:
      - name: Checkout Repository
        uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
          cache: 'pip'
          cache-dependency-path: './flossy_backend/requirements.txt'

      - name: Install Dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt

      - name: Run Linting
        run: |
          pip install flake8
          flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics || true

      - name: Deploy to Railway
        uses: bervProject/railway-deploy@main
        with:
          railway_token: ${{ secrets.RAILWAY_TOKEN }}
          service: flossy-backend

  # ========================================
  # NOTIFY ON COMPLETION
  # ========================================
  notify:
    name: Deployment Notification
    runs-on: ubuntu-latest
    needs: [frontend, backend]
    if: always()

    steps:
      - name: Send Success Notification
        if: ${{ needs.frontend.result == 'success' && needs.backend.result == 'success' }}
        run: echo "✅ Deployment successful!"

      - name: Send Failure Notification
        if: ${{ needs.frontend.result == 'failure' || needs.backend.result == 'failure' }}
        run: echo "❌ Deployment failed!"
```

### Alternative: Separate Workflows

#### `.github/workflows/frontend.yml`:
```yaml
name: Frontend CI/CD

on:
  push:
    branches: [main]
    paths:
      - 'flossy-ui/**'

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Deploy to Vercel
        uses: amondnet/vercel-action@v25
        with:
          vercel-token: ${{ secrets.VERCEL_TOKEN }}
          vercel-org-id: ${{ secrets.VERCEL_ORG_ID }}
          vercel-project-id: ${{ secrets.VERCEL_PROJECT_ID }}
          working-directory: ./flossy-ui
```

#### `.github/workflows/backend.yml`:
```yaml
name: Backend CI/CD

on:
  push:
    branches: [main]
    paths:
      - 'flossy_backend/**'

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Deploy to Railway
        uses: bervProject/railway-deploy@main
        with:
          railway_token: ${{ secrets.RAILWAY_TOKEN }}
          service: flossy-backend
```

---

## 🔐 Environment Variables

### GitHub Secrets (Settings → Secrets → Actions)

| Secret Name | Description | Example |
|-------------|-------------|---------|
| `VERCEL_TOKEN` | Vercel API token | Get from Vercel dashboard |
| `VERCEL_ORG_ID` | Vercel organization ID | Get from Vercel settings |
| `VERCEL_PROJECT_ID` | Vercel project ID | Get from Vercel settings |
| `RAILWAY_TOKEN` | Railway API token | Get from Railway dashboard |
| `VITE_API_URL` | Backend API URL | `https://api.smileartists.com` |
| `VITE_CLERK_PUBLISHABLE_KEY` | Clerk public key | `pk_live_xxx` |
| `VITE_LIVEKIT_URL` | LiveKit server URL | `wss://your-app.livekit.cloud` |

### Backend Environment Variables (Railway/Render Dashboard)

```env
# Database
DATABASE_URL=postgresql://user:pass@host:5432/dbname

# App Config
APP_PORT=8000
SECRET_KEY=your-super-secret-key-min-32-chars
CORS_ORIGINS=https://smileartists.com,https://www.smileartists.com

# Clerk Authentication
CLERK_SECRET_KEY=sk_live_xxxxx
CLERK_PUBLISHABLE_KEY=pk_live_xxxxx
CLERK_JWKS_URL=https://your-clerk-id.clerk.accounts.dev/.well-known/jwks.json

# AI Services
GOOGLE_API_KEY=AIzaSy-xxxxxx
GEMINI_API_KEY=AIzaSy-xxxxxx
GROQ_API_KEY=gsk_xxxxxx

# LiveKit (Voice AI)
LIVEKIT_API_KEY=APIxxxxxx
LIVEKIT_API_SECRET=xxxxxx
LIVEKIT_URL=wss://your-app.livekit.cloud

# PDF Generation
CLINIC_NAME=Smile Artists Dental Studio
CLINIC_ADDRESS=Your Clinic Address
CLINIC_PHONE=+91 XXXXXXXXXX
CLINIC_EMAIL=contact@smileartists.com
```

### Frontend Environment Variables (Vercel Dashboard)

```env
VITE_API_URL=https://api.smileartists.com
VITE_CLERK_PUBLISHABLE_KEY=pk_live_xxxxx
VITE_LIVEKIT_URL=wss://your-app.livekit.cloud
```

---

## 🔒 SSL/HTTPS Configuration

### Vercel (Frontend)
- ✅ Automatic SSL certificates
- ✅ Auto-renewal

### Railway (Backend)
- ✅ Automatic SSL certificates
- ✅ Custom domain with SSL

### Cloudflare (Optional - Recommended)
1. Add your domain to Cloudflare
2. Update nameservers at your registrar
3. Enable "Full (Strict)" SSL mode
4. Enable "Always Use HTTPS"

---

## ✅ Post-Deployment Verification

### 1. Health Checks
```bash
# Frontend
curl -I https://smileartists.com

# Backend API
curl https://api.smileartists.com/
curl https://api.smileartists.com/api/treatments
```

### 2. Authentication Test
1. Visit your domain
2. Try signing up/logging in with Clerk
3. Verify role-based redirects work

### 3. Database Connection
```bash
# Check via backend logs in Railway/Render dashboard
# Should see "DB tables ensured" on startup
```

### 4. AI Features
- Test FlossyAI chat
- Test Voice Agent (LiveKit)

---

## 🛠️ Troubleshooting

### Common Issues

#### 1. CORS Errors
**Solution**: Update `CORS_ORIGINS` in backend env to include your domain:
```env
CORS_ORIGINS=https://smileartists.com,https://www.smileartists.com
```

#### 2. Database Connection Refused
**Solution**: Check `DATABASE_URL` format:
```
postgresql://username:password@hostname:5432/database_name
```

#### 3. Clerk Authentication Fails
**Solution**: 
- Verify `CLERK_SECRET_KEY` and `CLERK_PUBLISHABLE_KEY`
- Check JWKS URL is correct
- Ensure domain is added in Clerk dashboard

#### 4. Build Fails on Vercel
**Solution**: Check environment variables are set in Vercel dashboard

#### 5. Railway Deploy Fails
**Solution**: 
```bash
# Check logs
railway logs

# Verify Procfile exists
cat Procfile
```

#### 6. PDF Generation Fails
**Solution**: Ensure `reportlab` is in requirements.txt and clinic env vars are set

---

## 📞 Support & Resources

- **Vercel Docs**: https://vercel.com/docs
- **Railway Docs**: https://docs.railway.app
- **Clerk Docs**: https://clerk.com/docs
- **FastAPI Docs**: https://fastapi.tiangolo.com
- **Vite Docs**: https://vitejs.dev

---

## 🚀 Quick Deployment Checklist

- [ ] Push code to GitHub
- [ ] Set up Railway project with PostgreSQL
- [ ] Set up Vercel project
- [ ] Configure DNS records for custom domain
- [ ] Add all environment variables
- [ ] Configure GitHub Secrets
- [ ] Create GitHub Actions workflow file
- [ ] Push to main branch
- [ ] Verify deployment
- [ ] Test all features
- [ ] Enable monitoring/alerts

---

*Documentation last updated: January 2026*
*Project: Flossy - Dental Clinic Management System*
