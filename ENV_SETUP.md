# Environment Setup Guide

## Overview

The backend uses environment variables to securely store API keys and configuration. The application uses Python's `python-dotenv` library to load these variables.

## Environment Files

You have three environment files:

1. **`.env`** - Active environment file (loaded by default)
2. **`.env.dev`** - Development environment backup
3. **`.env.example`** - Template with placeholders (safe to commit to Git)

## How It Works

The backend (`app.py`) loads environment variables using:

```python
from dotenv import load_dotenv
load_dotenv()  # Automatically loads .env by default
```

## Current Configuration

### ✅ Active Environment File: `.env`

The following variables are currently loaded:

```
✅ OPENAI_API_KEY        - Set correctly
✅ FAL_API_KEY           - Set correctly
✅ NANOBANANA_API_KEY    - Set correctly
✅ FLASK_ENV             - development
✅ FLASK_DEBUG           - True
⚠️  PORT                 - Using default (5001)
```

### Verification

Run the environment check script:

```bash
cd backend
source ../venv/bin/activate
python3 check_env.py
```

## Setup for New Developers

1. Copy the example file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and add your API keys:
   - **OpenAI API Key**: Get from https://platform.openai.com/api-keys
   - **FAL API Key**: Get from https://fal.ai/
   - **NanoBanana API Key**: Get from https://nanobanana.ai/

3. Verify the setup:
   ```bash
   python3 check_env.py
   ```

## File Priority

When using `load_dotenv()`:
- Loads `.env` by default
- Does NOT override existing environment variables
- If you need a different file, use: `load_dotenv('.env.dev')`

## Security Notes

⚠️ **IMPORTANT**:
- Never commit `.env` or `.env.dev` to Git
- Only commit `.env.example` with placeholder values
- Both `.env` and `.env.dev` are in `.gitignore`

## Testing Connectivity

### 1. Check Backend Health
```bash
curl http://localhost:5001/api/health
```

Expected response:
```json
{
  "status": "healthy",
  "message": "Outfit Assistant API is running"
}
```

### 2. Test CORS
```bash
curl -X OPTIONS http://localhost:5001/api/rate-outfit \
  -H "Origin: http://localhost:5173" \
  -H "Access-Control-Request-Method: POST" \
  -v 2>&1 | grep -i "access-control"
```

Should show:
```
< Access-Control-Allow-Origin: http://localhost:5173
< Access-Control-Allow-Credentials: true
```

### 3. Test Endpoint Structure
```bash
curl -X POST http://localhost:5001/api/rate-outfit \
  -H "Content-Type: application/json" \
  -d '{"image":"test","occasion":"test"}'
```

Should return an error (expected - validates endpoint is working):
```json
{
  "error": "Error code: 400 - {...invalid_image_url...}"
}
```

## Troubleshooting

### Backend won't start
1. Check if virtual environment is activated:
   ```bash
   which python3  # Should point to venv/bin/python3
   ```

2. Verify environment variables are loaded:
   ```bash
   python3 check_env.py
   ```

3. Check if port 5001 is available:
   ```bash
   lsof -i :5001
   ```

### API Keys not working
1. Ensure `.env` file exists in `/backend` directory
2. Check for typos in variable names
3. Restart the backend server after changing `.env`

### CORS Errors
1. Check backend CORS configuration in `app.py`
2. Verify frontend URL is in allowed origins
3. Check browser console for specific CORS error messages

## Current Status

✅ Backend running on: http://localhost:5001
✅ Frontend running on: http://localhost:5173
✅ All API keys loaded correctly
✅ CORS configured for localhost
✅ All endpoints responding correctly

## Next Steps

1. Test the application at http://localhost:5173
2. Upload an image and try "Rate My Outfit"
3. Test "Generate New Outfit" feature
4. Check new dropdown and slider styling
5. Verify no console errors in browser (F12)
