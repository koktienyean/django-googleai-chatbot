# Quick Reference Guide - Django Gemini Chatbot

**Last Updated**: November 27, 2025
**Version**: 2.0 (Phase 5 Complete)

---

## 🚀 Quick Start (5 minutes)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set up environment
export API_SECRET_KEY="your-google-gemini-api-key"

# 3. Run migrations
python manage.py migrate

# 4. Create admin account
python manage.py createsuperuser

# 5. Start server
python manage.py runserver
# Visit http://localhost:8000/login/
```

---

## 📍 Key URLs

| Purpose | URL |
|---------|-----|
| Login | `/login/` |
| Register | `/register/` |
| Chat | `/` |
| Settings | `/settings/` |
| Logout | `/logout/` |
| Admin | `/admin/` |

---

## 🏗️ Architecture at a Glance

```
User (authenticated)
  ↓
ChatSession (one or many)
  ├─ name, model, created_at, updated_at
  └─ Chat Messages (many)
      ├─ message (user text)
      ├─ response (AI response)
      └─ created_at
```

---

## 🎨 Design System - Quick Reference

### Colors
```css
--color-primary: #00d9ff;        /* Cyan - main accent */
--color-secondary: #ff006e;      /* Magenta - action */
--color-accent: #06d6a0;         /* Teal - success */
--bg-primary: #0f1419;           /* Dark background */
--text-primary: #e0e0e0;         /* Light text */
```

### Fonts
```
Playfair Display  → Headings
Outfit            → Body text
JetBrains Mono   → Code blocks
```

### Patterns
- Glass morphism: `rgba(26, 31, 42, 0.7) + blur(10px)`
- Gradients: `linear-gradient(135deg, cyan → magenta)`
- Shadows: `0 8px 24px rgba(0, 217, 255, 0.3)`
- Hover: `translateY(-2px)` with shadow boost

---

## 💻 File Locations

**Core Application**:
- `chatbot/models.py` - Database models
- `chatbot/views.py` - All views and API endpoints
- `chatbot/urls.py` - URL routing

**Templates**:
- `templates/login.html` - Login page
- `templates/register.html` - Register page
- `templates/chatbot.html` - Main chat interface
- `templates/settings.html` - Settings page
- `templates/base.html` - Base template

**Documentation**:
- `📋_START_HERE.md` - Beginner's guide
- `QUICK_START.md` - Setup instructions
- `HOW_AI_CHAT_WORKS.md` - Message flow
- `UI_POLISH_PHASE_5.md` - Design system
- `PROJECT_STATUS_COMPLETE.md` - Full status

---

## 🔌 API Endpoints Reference

### Sessions
```
GET  /api/sessions/              - List all user sessions
POST /api/sessions/create/       - Create new session
GET  /api/sessions/<id>/         - Get session details
POST /api/sessions/<id>/update/  - Update session
POST /api/sessions/<id>/delete/  - Delete session
```

### Messages & Chat
```
POST /chat/<session_id>/         - Send message (sync)
GET  /api/sessions/<id>/send/    - Queue message (async)
GET  /api/message/<id>/status/   - Check response status
```

### Configuration
```
GET  /api/models/                - List available models
POST /api/settings/save/         - Save user settings
```

---

## 🔧 Common Tasks

### Create a New Session
```javascript
fetch('/api/sessions/create/', {
  method: 'POST',
  body: new URLSearchParams({
    'csrfmiddlewaretoken': getCookie('csrftoken')
  })
})
.then(r => r.json())
.then(data => location.href = `/chat/${data.id}/`)
```

### Send a Message
```javascript
const message = "Hello, AI!";
fetch(`/chat/${sessionId}/`, {
  method: 'POST',
  body: new URLSearchParams({
    'message': message,
    'csrfmiddlewaretoken': getCookie('csrftoken')
  })
})
.then(r => r.json())
.then(data => console.log(data.response))
```

### Delete a Session
```javascript
fetch(`/api/sessions/${sessionId}/delete/`, {
  method: 'POST',
  body: new URLSearchParams({
    'csrfmiddlewaretoken': getCookie('csrftoken')
  })
})
```

---

## 🐛 Troubleshooting

| Problem | Solution |
|---------|----------|
| 404 on login | Ensure `urls.py` includes auth paths |
| API key error | Check `API_SECRET_KEY` environment variable |
| Database locked | Delete `db.sqlite3` and re-run migrations |
| UI looks broken | Clear browser cache (Ctrl+Shift+Delete) |
| Sessions not loading | Check browser console for JS errors |
| Model list empty | Verify API key has correct permissions |

---

## 📊 Database Queries

### Get user's sessions
```python
from chatbot.models import ChatSession
sessions = ChatSession.objects.filter(user=request.user)
```

### Get session messages
```python
from chatbot.models import Chat
messages = Chat.objects.filter(session=session_id)
```

### Count messages
```python
messages_count = Chat.objects.filter(session=session_id).count()
```

---

## 🔐 Security Checklist

- [x] CSRF tokens on all forms
- [x] User ownership verification
- [x] SQL injection protection (ORM used)
- [x] XSS protection (templates escape)
- [x] Session-based auth
- [x] Password hashing (Django default)

---

## 🎨 UI Customization

### Change Primary Color
Edit `templates/chatbot.html` line 12:
```css
--color-primary: #your-color;
```

### Change Font
Edit imported fonts (line 7):
```css
@import url('https://fonts.googleapis.com/...')
```

### Adjust Animations
Edit transition speeds (lines 39-42):
```css
--transition-fast: 0.2s ease;
--transition-smooth: 0.3s ease;
```

---

## 📈 Performance Tips

1. **Caching**: Model list cached for 1 hour
2. **Indexes**: Database queries optimized with indexes
3. **Async**: Long operations don't block requests
4. **CSS**: No image assets, pure CSS design
5. **Load**: Minimize external dependencies

---

## 🚢 Deployment

### Environment Variables Needed
```bash
API_SECRET_KEY=your-google-api-key
DJANGO_SECRET_KEY=your-django-secret
DEBUG=False
ALLOWED_HOSTS=yourdomain.com
```

### Database Setup
```bash
# Production: Use PostgreSQL
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'chatbot_db',
        'USER': 'postgres',
        'PASSWORD': 'secure_password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

### Server
```bash
# Use gunicorn in production
pip install gunicorn
gunicorn django_chatbot.wsgi:application --bind 0.0.0.0:8000 --workers 4
```

---

## 📚 Documentation Map

```
📋_START_HERE.md
  └─ For new developers (start here!)

QUICK_START.md
  └─ Installation & setup

QUICK_REFERENCE.md (this file)
  └─ Common tasks & commands

HOW_AI_CHAT_WORKS.md
  └─ Complete message flow

UI_POLISH_PHASE_5.md
  └─ Design system details

AUTH_DESIGN_GUIDE.md
  └─ Authentication pages

PROJECT_STATUS_COMPLETE.md
  └─ Full project overview
```

---

## ✅ Pre-Deployment Checklist

- [ ] Environment variables set
- [ ] Database migrated
- [ ] Admin user created
- [ ] API key verified working
- [ ] Static files collected
- [ ] DEBUG=False in settings
- [ ] ALLOWED_HOSTS configured
- [ ] CSRF_TRUSTED_ORIGINS set
- [ ] HTTPS enforced
- [ ] Database backed up

---

## 🆘 Getting Help

**For setup issues**: See `QUICK_START.md`
**For architecture questions**: See `HOW_AI_CHAT_WORKS.md`
**For design questions**: See `UI_POLISH_PHASE_5.md`
**For full project info**: See `PROJECT_STATUS_COMPLETE.md`

---

## 📞 Command Reference

```bash
# Development
python manage.py runserver              # Start dev server
python manage.py shell                  # Python shell
python manage.py dbshell                # Database shell

# Database
python manage.py migrate                # Apply migrations
python manage.py makemigrations         # Create migrations
python manage.py dumpdata               # Backup database

# Django
python manage.py check                  # System check
python manage.py createsuperuser        # Create admin
python manage.py changepassword         # Change user password
python manage.py collectstatic          # Collect static files

# Testing
python manage.py test                   # Run tests
coverage run --source='.' manage.py test # Coverage report
```

---

## 🎯 Key Features at a Glance

✅ **Multi-Session Chat**: Create unlimited conversations
✅ **Model Selection**: Choose from available Gemini models
✅ **Settings Page**: Configure AI behavior
✅ **Async Processing**: Non-blocking message handling
✅ **Dark Terminal UI**: Professional modern design
✅ **Responsive**: Works on all devices
✅ **Markdown Support**: Rich text formatting
✅ **Security**: Proper authentication & CSRF protection

---

**Quick Reference v2.0**
*Created: November 27, 2025*
*Phase 5 Complete*
