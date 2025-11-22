# Deploy Lumora Backend to Railway

## Quick Deploy Steps

### 1. Go to Railway
Visit: **https://railway.app**

### 2. Create New Project
- Click **"Start a New Project"**
- Select **"Deploy from GitHub repo"**
- Choose **`saileshsharma/lumora-web-be`**

### 3. Configure Environment Variables

**CRITICAL:** Add these environment variables in Railway dashboard:

```
OPENAI_API_KEY=your_openai_api_key_here
FAL_API_KEY=your_fal_api_key_here
NANOBANANA_API_KEY=your_nanobanana_api_key_here
FLASK_ENV=production
FLASK_DEBUG=False
```

**To add variables:**
1. Click on your service
2. Go to "Variables" tab
3. Click "New Variable"
4. Add each variable above
5. Click "Deploy" to apply

### 4. Railway Auto-Deploys

Railway will:
- ✅ Detect Python app
- ✅ Install dependencies from `requirements.txt`
- ✅ Run `python app.py`
- ✅ Assign a public URL

### 5. Get Your Backend URL

1. Go to "Settings" → "Domains"
2. Click "Generate Domain"
3. Your URL will be like: `https://lumora-web-be-production.up.railway.app`

### 6. Update Frontend

Update the frontend to use your new backend URL:

In `frontend/src/constants/index.ts`:
```typescript
const backendUrl = 'https://YOUR-NEW-BACKEND-URL.up.railway.app/api';
```

## Verify Deployment

Test the health endpoint:
```bash
curl https://YOUR-BACKEND-URL.up.railway.app/api/health
```

Should return:
```json
{
  "success": true,
  "status": "healthy",
  "message": "Lumora API is running"
}
```

## CORS is Pre-Configured

The backend already has CORS configured for:
- ✅ `https://lumora-web-production.up.railway.app`
- ✅ `localhost` for development

## Troubleshooting

**Build fails?**
- Check Railway logs
- Verify `requirements.txt` is present
- Ensure Python 3.11 is selected

**App crashes?**
- Check environment variables are set
- View runtime logs in Railway
- Verify PORT is not hardcoded (uses `os.getenv('PORT')`)

**CORS errors?**
- Make sure frontend URL matches exactly in `app.py`
- Check Railway deployment logs

## Update After Changes

Simply push to GitHub:
```bash
git add .
git commit -m "Update backend"
git push origin main
```

Railway automatically redeploys! 🚀

## Cost

Railway free tier:
- $5 free credit per month
- Enough for development/testing
- Upgrade for production use

---

**Repository:** https://github.com/saileshsharma/lumora-web-be
**Frontend Repo:** https://github.com/saileshsharma/lumora-web
