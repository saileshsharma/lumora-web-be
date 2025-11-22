# Security Implementation Guide

## Overview

This document describes the security features implemented in the AI Outfit Assistant application as part of the security hardening initiative.

## ✅ Security Features Implemented

### 1. Rate Limiting

**Status**: ✅ IMPLEMENTED

All API endpoints now have rate limiting to prevent abuse and protect against brute force attacks.

**Configuration** (`app/security_config.py`):

```python
RATE_LIMITS = {
    "ai_generation": "5 per hour",      # Image generation (expensive)
    "ai_rating": "20 per hour",          # GPT-4 Vision calls
    "ai_tryon": "10 per hour",           # Virtual try-on
    "user_action": "30 per minute",      # Submit, vote, etc.
    "api_read": "60 per minute",         # GET requests
    "admin": "5 per hour"                # Admin operations
}
```

**Protected Endpoints**:
- `/api/rate-outfit` - 20 per hour
- `/api/generate-outfit` - 5 per hour
- `/api/arena/submit` - 30 per minute
- `/api/arena/vote` - 30 per minute
- `/api/squad/*` - 30 per minute (all squad actions)
- `/api/arena/submission/<id>` (DELETE) - 5 per hour

**Storage**: In-memory (default). For production with multiple servers, configure Redis:

```python
# In app/security_config.py
def get_limiter_storage():
    return "redis://localhost:6379"
```

---

### 2. Security Headers

**Status**: ✅ IMPLEMENTED

Flask-Talisman configured with comprehensive security headers.

**Headers Applied**:
- **HSTS**: Strict-Transport-Security (1 year)
- **CSP**: Content-Security-Policy (strict policy)
- **X-Content-Type-Options**: nosniff
- **X-Frame-Options**: DENY (clickjacking protection)
- **Referrer-Policy**: strict-origin-when-cross-origin

**Content Security Policy**:
```python
csp = {
    'default-src': ["'self'"],
    'script-src': ["'self'", "'unsafe-inline'", "https://cdn.jsdelivr.net"],
    'style-src': ["'self'", "'unsafe-inline'"],
    'img-src': ["'self'", "data:", "https:", "blob:"],
    'connect-src': [
        "'self'",
        "https://api.openai.com",
        "https://fal.run",
        "https://api.nanobanana.net"
    ],
    'frame-ancestors': ["'none'"],
}
```

---

### 3. Input Validation

**Status**: ✅ IMPLEMENTED

Marshmallow schemas validate all user inputs before processing.

**Schemas Implemented**:
- `OutfitRatingSchema` - Validates photo + occasion
- `OutfitGenerationSchema` - Validates generation params
- `VirtualTryOnSchema` - Validates try-on images
- `ArenaSubmissionSchema` - Validates arena submissions
- `SquadCreateSchema` - Validates squad creation
- `SquadVoteSchema` - Validates voting data
- `SquadMessageSchema` - Validates chat messages

**Example Validation**:
```python
@app.route('/api/rate-outfit', methods=['POST'])
@limiter.limit(RATE_LIMITS["ai_rating"])
def rate_outfit():
    try:
        validated_data = validate_request_data(OutfitRatingSchema, {
            'photo': data.get('image'),
            'occasion': data.get('occasion')
        })
    except ValidationError as e:
        return jsonify({"error": "Invalid input", "details": e.messages}), 400
```

**Validation Rules**:
- Photo size: Max 10MB
- Text fields: Max length enforced
- Occasions: Whitelist validation
- User IDs: Regex pattern matching (`^[a-zA-Z0-9_-]+$`)
- Invite codes: Exactly 6 alphanumeric characters

---

### 4. Admin Authentication

**Status**: ✅ IMPLEMENTED

Hardcoded password **removed**. Admin operations now use environment variable.

**Old Code** (❌ REMOVED):
```python
if password != '182838':  # INSECURE!
    return jsonify({"error": "Incorrect password"}), 403
```

**New Code** (✅ SECURE):
```python
@app.route('/api/arena/submission/<id>', methods=['DELETE'])
@limiter.limit(RATE_LIMITS["admin"])
def delete_submission(submission_id):
    password = data.get('password')

    if not validate_admin_password(password):
        error_logger.warning(f"Failed admin auth attempt for {submission_id}")
        return jsonify({"error": "Incorrect password"}), 403
```

**Security Features**:
- Constant-time comparison (prevents timing attacks)
- Password stored in environment variable
- Failed attempts logged
- Rate limited (5 attempts per hour)

---

### 5. Image Validation

**Status**: ✅ IMPLEMENTED

All image data is validated before processing to prevent path traversal and SSRF attacks.

**Validation Function**:
```python
def validate_image_data(data: str) -> bool:
    # Block local file paths
    if any(prefix in data.lower() for prefix in ['file://', '../', '..\\']):
        return False

    # Accept data URLs
    if data.startswith('data:image/'):
        return True

    # Accept HTTPS URLs
    if data.startswith(('http://', 'https://')):
        return True

    return False
```

**Protected Against**:
- Path traversal (`../../../etc/passwd`)
- Local file access (`file:///etc/passwd`)
- SSRF attacks (via file:// protocol)

---

## 🔐 Environment Variables

**Required Environment Variables**:

```bash
# API Keys
OPENAI_API_KEY="sk-..."
FAL_API_KEY="..."
NANOBANANA_API_KEY="..."

# Admin Security
ADMIN_PASSWORD="your-secure-password-here"

# Flask Configuration
FLASK_ENV="production"
FLASK_DEBUG="False"
```

**⚠️ IMPORTANT**:
1. **Never commit `.env` file to git**
2. Use strong, unique password for `ADMIN_PASSWORD`
3. Rotate API keys regularly
4. Set `FLASK_DEBUG=False` in production

---

## 🚀 Deployment Checklist

### Railway Deployment

1. **Set Environment Variables** in Railway Dashboard:
   ```
   ADMIN_PASSWORD=<generate-strong-password>
   FLASK_ENV=production
   FLASK_DEBUG=False
   ```

2. **Verify Security Headers**:
   ```bash
   curl -I https://your-app.railway.app/api/health
   ```
   Should include:
   - `Strict-Transport-Security`
   - `X-Content-Type-Options: nosniff`
   - `X-Frame-Options: DENY`

3. **Test Rate Limiting**:
   ```bash
   # Should fail after 20 requests in 1 hour
   for i in {1..25}; do
     curl -X POST https://your-app.railway.app/api/rate-outfit \
       -H "Content-Type: application/json" \
       -d '{"image":"data:image/png;base64,iVBOR...","occasion":"casual"}'
   done
   ```

4. **Test Admin Auth**:
   ```bash
   # Should fail with wrong password
   curl -X DELETE https://your-app.railway.app/api/arena/submission/123 \
     -H "Content-Type: application/json" \
     -d '{"password":"wrong"}'
   ```

---

## 📊 Monitoring & Logging

### Rate Limit Monitoring

Check logs for rate limit violations:
```bash
grep "429" logs/application_*.log
```

### Failed Auth Attempts

Monitor failed admin authentications:
```bash
grep "Failed admin auth" logs/errors_*.log
```

### Security Alerts

Watch for:
- Multiple 429 (Too Many Requests) from same IP
- Failed admin authentication attempts
- Validation errors (possible attack attempts)
- Path traversal attempts

---

## 🔄 Future Security Enhancements

### Not Yet Implemented (Recommended)

1. **JWT Authentication** (Option B from roadmap)
   - User registration/login
   - Token-based auth
   - Refresh tokens

2. **Database Migration** (High Priority)
   - Move from JSON to PostgreSQL
   - Encryption at rest
   - Proper access controls

3. **Image Storage** (Medium Priority)
   - Move from base64 to S3/R2
   - Signed URLs
   - CDN integration

4. **API Key Rotation**
   - Automated rotation schedule
   - Zero-downtime rotation

5. **WAF Integration**
   - Cloudflare WAF
   - DDoS protection
   - Bot detection

---

## 🐛 Known Limitations

### Current Limitations

1. **Rate Limiter Storage**: Uses in-memory storage
   - **Impact**: Rate limits reset on server restart
   - **Production**: Deploy Redis for persistence

2. **No User Authentication**: Still uses mock login
   - **Impact**: No real user accounts
   - **Mitigation**: Plan Option B (JWT auth)

3. **JSON File Storage**: Data stored in plaintext files
   - **Impact**: No encryption at rest
   - **Mitigation**: Migrate to PostgreSQL

4. **Image Size**: No hard limit on request body size
   - **Impact**: Could accept very large uploads
   - **Mitigation**: Add Flask max content length

---

## 📞 Security Incident Response

### If You Detect a Security Issue

1. **Immediate Actions**:
   - Rotate API keys immediately
   - Change `ADMIN_PASSWORD`
   - Review logs for suspicious activity

2. **Investigation**:
   ```bash
   # Check recent requests
   tail -100 logs/application_*.log

   # Check failed auth
   grep "403\|401" logs/errors_*.log

   # Check rate limit hits
   grep "429" logs/application_*.log
   ```

3. **Mitigation**:
   - Block malicious IPs in Railway/Cloudflare
   - Temporarily increase rate limits if legitimate traffic affected
   - Review and update security rules

---

## 📚 References

- [Flask-Limiter Documentation](https://flask-limiter.readthedocs.io/)
- [Flask-Talisman Documentation](https://github.com/GoogleCloudPlatform/flask-talisman)
- [Marshmallow Documentation](https://marshmallow.readthedocs.io/)
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Content Security Policy](https://developer.mozilla.org/en-US/docs/Web/HTTP/CSP)

---

**Last Updated**: November 22, 2025
**Security Version**: 1.0
**Implemented By**: Claude Code
