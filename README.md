# Lumora - AI Outfit Assistant (Backend)

🚀 **AI-Powered Fashion API with Keycloak Integration**

## Features

- 🔐 **Keycloak Integration** - OAuth2/OIDC authentication
- 🤖 **OpenAI GPT-4 Vision** - Outfit analysis
- 🎨 **Nanobanana API** - Outfit generation
- 🖼️ **FAL.ai** - Image processing
- 📊 **Fashion Arena** - Community submissions
- 👥 **Style Squad** - Social features

## Tech Stack

- Python 3.11+
- Flask
- Keycloak Python Adapter
- OpenAI API
- Nanobanana API
- FAL.ai API

## Quick Start

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your API keys and Keycloak config

# Run development server
python app.py
```

## Production Deployment

This backend is designed to deploy to **Railway**.

See `PRODUCTION_DEPLOYMENT_GUIDE.md` for complete deployment instructions.

## Environment Variables

```bash
# API Keys
FAL_API_KEY=your-fal-api-key
NANOBANANA_API_KEY=your-nanobanana-key
OPENAI_API_KEY=your-openai-key

# Keycloak
KEYCLOAK_SERVER_URL=https://your-keycloak.railway.app
KEYCLOAK_REALM=lumora
KEYCLOAK_CLIENT_ID=lumora-backend
KEYCLOAK_CLIENT_SECRET=your-client-secret
USE_KEYCLOAK=true

# Security
ADMIN_PASSWORD=your-admin-password
JWT_SECRET_KEY=your-jwt-secret

# Flask
FLASK_ENV=production
FLASK_DEBUG=False
PORT=5001
```

## Frontend Repository

Frontend App: https://github.com/saileshsharma/lumora-web

---

🤖 Built with AI assistance from Claude Code
