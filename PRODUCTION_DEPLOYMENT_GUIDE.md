# 🚀 Production Deployment Guide

**AI Outfit Assistant - Complete Deployment to Production**

**Date:** November 22, 2025
**Platforms:** Railway (Keycloak + Backend), Cloudflare Workers (Frontend)

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Deployment Order](#deployment-order)
4. [Step 1: Deploy Keycloak to Railway](#step-1-deploy-keycloak-to-railway)
5. [Step 2: Configure Keycloak](#step-2-configure-keycloak)
6. [Step 3: Deploy Backend to Railway](#step-3-deploy-backend-to-railway)
7. [Step 4: Deploy Frontend to Cloudflare Workers](#step-4-deploy-frontend-to-cloudflare-workers)
8. [Step 5: Final Verification](#step-5-final-verification)
9. [Environment Variables](#environment-variables)
10. [Troubleshooting](#troubleshooting)

---

## Overview

### Architecture

```
┌─────────────────┐
│  Cloudflare     │ ← Frontend (React + Keycloak.js)
│  Workers        │
│  (Frontend)     │
└────────┬────────┘
         │
         ├──────────────────┐
         │                  │
         ▼                  ▼
┌─────────────────┐  ┌─────────────────┐
│   Railway       │  │   Railway       │
│  (Keycloak)     │  │  (Backend API)  │
│  Port: Public   │  │  Port: Public   │
└────────┬────────┘  └─────────────────┘
         │
         ▼
┌─────────────────┐
│   PostgreSQL    │
│   (Railway)     │
└─────────────────┘
```

### Deployment Platforms

- **Keycloak:** Railway (with PostgreSQL)
- **Backend:** Railway (Python/Flask)
- **Frontend:** Cloudflare Workers

### Estimated Time

- ⏱️ **Total:** 30-40 minutes
- Keycloak: 10 minutes
- Backend: 10 minutes
- Frontend: 5 minutes
- Configuration & Testing: 15 minutes

---

## Prerequisites

### Required Accounts

1. ✅ **Railway Account** - https://railway.app
   - Credit card required (free tier available)
   - $5/month free credit

2. ✅ **Cloudflare Account** - https://cloudflare.com
   - Workers free tier (100,000 requests/day)
   - Custom domain (optional)

### Required Tools

```bash
# Railway CLI
npm install -g @railway/cli

# Cloudflare Wrangler CLI
npm install -g wrangler

# Verify installations
railway --version
wrangler --version
```

### Login to Services

```bash
# Login to Railway
railway login

# Login to Cloudflare
wrangler login
```

---

## Deployment Order

**IMPORTANT:** Deploy in this exact order:

1. ✅ Keycloak (Authentication Server)
2. ✅ Backend API (Depends on Keycloak)
3. ✅ Frontend (Depends on both Keycloak & Backend)

---

## Step 1: Deploy Keycloak to Railway

### 1.1 Create New Railway Project

```bash
# Navigate to project root
cd /path/to/outfit-assistant

# Initialize Railway project
railway init

# Create new project when prompted
# Name: "lumora-keycloak"
```

### 1.2 Add PostgreSQL Database

```bash
# Add PostgreSQL service
railway add --database postgresql

# Note the connection details
railway variables
```

### 1.3 Deploy Keycloak

Create `Dockerfile.keycloak` (already exists):

```dockerfile
FROM quay.io/keycloak/keycloak:23.0

# Environment variables will be set in Railway
ENV KC_DB=postgres
ENV KC_HEALTH_ENABLED=true
ENV KC_METRICS_ENABLED=true
ENV KC_HTTP_RELATIVE_PATH=/

# Production mode
ENV KC_HOSTNAME_STRICT=false
ENV KC_PROXY=edge

ENTRYPOINT ["/opt/keycloak/bin/kc.sh", "start", "--optimized"]
```

**Deploy to Railway:**

```bash
# Set Dockerfile
railway up --dockerfile Dockerfile.keycloak

# Or use Railway dashboard:
# 1. Go to railway.app
# 2. Create new project
# 3. Select "Deploy from GitHub repo" or "Empty Project"
# 4. Add PostgreSQL database
# 5. Connect Dockerfile
```

### 1.4 Set Keycloak Environment Variables

In Railway dashboard → Keycloak service → Variables:

```bash
# Database (Auto-filled by Railway PostgreSQL)
KC_DB=postgres
KC_DB_URL=${{Postgres.DATABASE_URL}}

# Admin Credentials
KEYCLOAK_ADMIN=admin
KEYCLOAK_ADMIN_PASSWORD=<STRONG_SECURE_PASSWORD>

# Production Settings
KC_HOSTNAME_STRICT=false
KC_PROXY=edge
KC_HTTP_ENABLED=true
KC_HEALTH_ENABLED=true
KC_METRICS_ENABLED=true
```

### 1.5 Generate Public URL

```bash
# In Railway dashboard:
# Settings → Networking → Generate Domain

# You'll get:
# https://lumora-keycloak-production.up.railway.app
```

### 1.6 Verify Keycloak Deployment

```bash
# Check health
curl https://your-keycloak-url.railway.app/health/ready

# Expected: {"status": "UP", ...}
```

---

## Step 2: Configure Keycloak

### 2.1 Access Keycloak Admin Console

```
URL: https://your-keycloak-url.railway.app
Username: admin
Password: <YOUR_ADMIN_PASSWORD>
```

### 2.2 Create Realm

1. Click "Create Realm"
2. Name: `lumora`
3. Enabled: YES
4. Click "Create"

### 2.3 Create Frontend Client

**Client ID:** `lumora-frontend`

```json
{
  "clientId": "lumora-frontend",
  "enabled": true,
  "publicClient": true,
  "protocol": "openid-connect",
  "redirectUris": [
    "https://lumora.aihack.workers.dev/*",
    "https://your-custom-domain.com/*",
    "http://localhost:5174/*"
  ],
  "webOrigins": [
    "https://lumora.aihack.workers.dev",
    "https://your-custom-domain.com",
    "http://localhost:5174"
  ],
  "attributes": {
    "pkce.code.challenge.method": "S256",
    "post.logout.redirect.uris": "+"
  }
}
```

### 2.4 Create Backend Client

**Client ID:** `lumora-backend`

```json
{
  "clientId": "lumora-backend",
  "enabled": true,
  "publicClient": false,
  "protocol": "openid-connect",
  "serviceAccountsEnabled": true,
  "authorizationServicesEnabled": false,
  "redirectUris": ["*"],
  "webOrigins": ["*"]
}
```

**Get Client Secret:**
1. Go to `lumora-backend` → Credentials
2. Copy the "Client Secret"
3. Save it for backend deployment

### 2.5 Create Test User

1. Users → Add User
2. Username: `test@example.com`
3. Email: `test@example.com`
4. Email Verified: YES
5. Save

6. Credentials tab
7. Set Password
8. Temporary: NO

---

## Step 3: Deploy Backend to Railway

### 3.1 Create Backend Service

```bash
# Create new service in same Railway project
railway service create backend

# Link to service
railway link
```

### 3.2 Set Backend Environment Variables

In Railway dashboard → Backend service → Variables:

```bash
# API Keys
FAL_API_KEY=your-fal-api-key
NANOBANANA_API_KEY=your-nanobanana-api-key
OPENAI_API_KEY=your-openai-api-key

# Flask Settings
FLASK_DEBUG=False
FLASK_ENV=production

# Admin & Security
ADMIN_PASSWORD=<STRONG_PASSWORD>
JWT_SECRET_KEY=<GENERATE_WITH: python3 -c "import secrets; print(secrets.token_hex(32))">

# Keycloak Configuration
KEYCLOAK_SERVER_URL=https://your-keycloak-url.railway.app
KEYCLOAK_REALM=lumora
KEYCLOAK_CLIENT_ID=lumora-backend
KEYCLOAK_CLIENT_SECRET=<FROM_STEP_2.4>
USE_KEYCLOAK=true

# Port
PORT=5001
```

### 3.3 Deploy Backend

```bash
# From backend directory
cd backend

# Deploy to Railway
railway up
```

Or use `railway.json` in backend folder:

```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "NIXPACKS",
    "buildCommand": "pip install -r requirements.txt"
  },
  "deploy": {
    "startCommand": "gunicorn app:app --bind 0.0.0.0:$PORT --workers 4 --timeout 120",
    "healthcheckPath": "/api/health",
    "healthcheckTimeout": 100,
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 3
  }
}
```

### 3.4 Generate Backend Public URL

```bash
# In Railway dashboard:
# Backend service → Settings → Networking → Generate Domain

# You'll get:
# https://lumora-backend-production.up.railway.app
```

### 3.5 Verify Backend Deployment

```bash
# Check health
curl https://your-backend-url.railway.app/api/health

# Expected: {"status": "healthy", "message": "Outfit Assistant API is running"}
```

---

## Step 4: Deploy Frontend to Cloudflare Workers

### 4.1 Configure Wrangler

Create/update `frontend/wrangler.toml`:

```toml
name = "lumora-outfit-assistant"
main = "dist/worker.js"
compatibility_date = "2024-01-01"

[site]
bucket = "./dist"

[vars]
VITE_API_URL = "https://your-backend-url.railway.app/api"
VITE_KEYCLOAK_URL = "https://your-keycloak-url.railway.app"
VITE_KEYCLOAK_REALM = "lumora"
VITE_KEYCLOAK_CLIENT_ID = "lumora-frontend"
```

### 4.2 Build Frontend for Production

```bash
cd frontend

# Install dependencies
npm install

# Build with production env vars
VITE_API_URL=https://your-backend-url.railway.app/api \
VITE_KEYCLOAK_URL=https://your-keycloak-url.railway.app \
VITE_KEYCLOAK_REALM=lumora \
VITE_KEYCLOAK_CLIENT_ID=lumora-frontend \
npm run build
```

### 4.3 Deploy to Cloudflare Workers

```bash
# Deploy
wrangler deploy

# You'll get a URL like:
# https://lumora-outfit-assistant.your-subdomain.workers.dev
```

### 4.4 (Optional) Configure Custom Domain

```bash
# Add custom domain
wrangler domains add your-domain.com

# Follow DNS setup instructions
```

---

## Step 5: Final Verification

### 5.1 Update Keycloak Redirect URIs

Go back to Keycloak Admin Console and update:

**Frontend Client (`lumora-frontend`):**
- Add your Cloudflare Workers URL to Redirect URIs
- Add your Cloudflare Workers URL to Web Origins
- Update post-logout redirect URIs

### 5.2 Test Complete Flow

1. **Visit Frontend URL**
   ```
   https://lumora-outfit-assistant.workers.dev
   ```

2. **Login**
   - Should redirect to Keycloak
   - Login with test credentials
   - Should redirect back to app

3. **Test Rate My Outfit**
   - Upload image
   - Select occasion
   - Click "Rate My Outfit"
   - Should get results

4. **Test Logout**
   - Click user menu → Logout
   - Confirm logout
   - Should redirect to Keycloak login

### 5.3 Check All Services

```bash
# Keycloak
curl https://your-keycloak-url.railway.app/health/ready

# Backend
curl https://your-backend-url.railway.app/api/health

# Frontend
curl https://your-frontend-url.workers.dev
```

---

## Environment Variables Reference

### Backend (.env for production)

```bash
# API Keys
FAL_API_KEY=15f59cde-2e1c-4fb9-a711-74af4877d225:789cceadee161332bc1d59ffe466eaf8
NANOBANANA_API_KEY=dff30a51e8b6482a2337ef1b429351b6
OPENAI_API_KEY=sk-proj-...

# Flask
FLASK_DEBUG=False
FLASK_ENV=production

# Security
ADMIN_PASSWORD=<PRODUCTION_PASSWORD>
JWT_SECRET_KEY=<64_CHAR_HEX_STRING>

# Keycloak
KEYCLOAK_SERVER_URL=https://your-keycloak.railway.app
KEYCLOAK_REALM=lumora
KEYCLOAK_CLIENT_ID=lumora-backend
KEYCLOAK_CLIENT_SECRET=<CLIENT_SECRET>
USE_KEYCLOAK=true

# Port
PORT=5001
```

### Frontend (Cloudflare Workers)

Set as secrets:

```bash
wrangler secret put VITE_API_URL
# Enter: https://your-backend.railway.app/api

wrangler secret put VITE_KEYCLOAK_URL
# Enter: https://your-keycloak.railway.app

wrangler secret put VITE_KEYCLOAK_REALM
# Enter: lumora

wrangler secret put VITE_KEYCLOAK_CLIENT_ID
# Enter: lumora-frontend
```

---

## Troubleshooting

### Issue: Keycloak "Invalid Redirect URI"

**Solution:**
1. Check Keycloak client redirect URIs include your frontend URL
2. Run fix script:
   ```bash
   python3 fix_keycloak_logout.py
   ```

### Issue: Backend CORS Errors

**Solution:**
Update `backend/app.py` CORS configuration:

```python
CORS(app, resources={
    r"/api/*": {
        "origins": [
            "https://your-frontend.workers.dev",
            "http://localhost:5174"
        ],
        "supports_credentials": True
    }
})
```

### Issue: Frontend Can't Connect to Backend

**Solution:**
1. Check `VITE_API_URL` environment variable
2. Verify backend is running: `curl https://backend-url/api/health`
3. Check browser console for CORS errors

### Issue: Railway Deployment Fails

**Solution:**
1. Check build logs in Railway dashboard
2. Verify all environment variables are set
3. Check Dockerfile syntax
4. Ensure dependencies are in requirements.txt

---

## Production Checklist

### Before Deployment

- [ ] Update all API keys to production values
- [ ] Set strong admin passwords
- [ ] Generate new JWT secret key
- [ ] Update CORS origins
- [ ] Remove debug flags
- [ ] Test locally with production settings

### After Deployment

- [ ] Keycloak health check passes
- [ ] Backend health check passes
- [ ] Frontend loads correctly
- [ ] Login flow works
- [ ] Rate My Outfit works
- [ ] Generate Outfit works
- [ ] Logout works
- [ ] Mobile responsive
- [ ] HTTPS enabled
- [ ] Custom domain configured (optional)

---

## Cost Estimation

### Monthly Costs

| Service | Platform | Cost |
|---------|----------|------|
| Keycloak | Railway | $5 (Hobby plan) |
| PostgreSQL | Railway | Free (included) |
| Backend API | Railway | $5 (Hobby plan) |
| Frontend | Cloudflare Workers | Free (up to 100k req/day) |
| **Total** | | **~$10/month** |

### Scaling Costs

- Railway scales automatically
- Cloudflare Workers: $5/month for 10M requests
- Can optimize by using Railway's usage-based pricing

---

## Next Steps

1. ✅ Deploy Keycloak
2. ✅ Deploy Backend
3. ✅ Deploy Frontend
4. ✅ Configure DNS (optional)
5. ✅ Monitor with Railway/Cloudflare dashboards
6. ✅ Set up error tracking (Sentry)
7. ✅ Configure analytics
8. ✅ Set up backups

---

## Support & Resources

- **Railway Docs:** https://docs.railway.app
- **Cloudflare Workers:** https://developers.cloudflare.com/workers/
- **Keycloak Docs:** https://www.keycloak.org/documentation

---

**Deployment Guide Version:** 1.0
**Last Updated:** November 22, 2025
**Status:** Production Ready ✅
