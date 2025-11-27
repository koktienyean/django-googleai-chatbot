# Quick Start - Django Gemini Chatbot (Enhanced)

## What's New

This is an **enhanced version** of the Django Gemini Chatbot with the following features:

### ✅ Completed Features

1. **Multiple Chat Sessions** 💬
   - Create, switch, rename, and delete chat sessions
   - Each session maintains separate message history
   - Session list in left sidebar

2. **Model Configuration** ⚙️
   - Settings page to select AI model
   - List of available Gemini models from API
   - Save model preference per session
   - Test model connectivity button

3. **Async Message Processing** ⚡
   - Non-blocking message submission
   - Background queue for processing
   - Real-time polling for responses
   - Prevents API congestion

4. **Improved UI** 🎨
   - Sidebar with session list
   - Clean, responsive design
   - Loading states and error handling
   - Mobile-friendly layout

---

## Getting Started

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Setup Environment
```bash
# Create .env file with your Gemini API key
echo "API_SECRET_KEY=your_gemini_api_key" > .env
```

### 3. Run Migrations
```bash
python manage.py migrate
```

### 4. Create Superuser (optional for admin)
```bash
python manage.py createsuperuser
```

### 5. Run Development Server
```bash
python manage.py runserver
```

### 6. Access the Application
```
http://localhost:8000/
```

---

## Usage

### First Time
1. Go to `/register/` to create account
2. Login with credentials
3. You're automatically redirected to a new chat session

### Chat Interface
- **Send Message**: Type in input box and press Send or Enter
- **Switch Session**: Click session name in left sidebar
- **New Chat**: Click "+ New Chat" button
- **Delete Session**: Hover over session and click 🗑️
- **Settings**: Click ⚙️ in top right

### Settings Page
1. Go to `/settings/` or click ⚙️ in chat header
2. Select desired Gemini model from dropdown
3. Click "Test Model" to verify connection
4. Click "Save Settings" to update

---

## API Endpoints

### Authentication
```
POST   /login/              - User login
POST   /register/           - User registration
POST   /logout/             - User logout
```

### Chat
```
GET    /                    - Chat home (redirects to latest session)
GET    /chat/<session_id>/  - View specific chat session
POST   /chat/<session_id>/  - Send message in session
```

### Sessions
```
GET    /api/sessions/                      - List all user sessions
POST   /api/sessions/create/               - Create new session
GET    /api/sessions/<id>/                 - Get session details
POST   /api/sessions/<id>/update/          - Update session
POST   /api/sessions/<id>/delete/          - Delete session
```

### Messages (Async)
```
POST   /api/sessions/<id>/send/            - Queue message (returns request_id)
GET    /api/message/<request_id>/status/   - Poll for response
```

### Settings
```
GET    /settings/           - Settings page
GET    /api/models/         - List available models (cached)
POST   /api/settings/save/  - Save model preference
```

---

## Project Structure

```
django-googleai-chatbot/
├── django_chatbot/              # Main Django project
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── chatbot/                     # Main app
│   ├── models.py               # ChatSession, Chat models
│   ├── views.py                # All views and API endpoints
│   ├── urls.py                 # URL routing
│   ├── message_queue.py        # Async message processor
│   ├── migrations/
│   │   ├── 0001_initial.py
│   │   ├── 0002_chatsession_*.py
│   │   └── 0003_migrate_*.py
│   └── admin.py
├── templates/
│   ├── base.html               # Base template
│   ├── chatbot.html            # Main chat interface
│   ├── login.html              # Login page
│   ├── register.html           # Registration page
│   └── settings.html           # Settings page
├── db.sqlite3                  # SQLite database
├── manage.py                   # Django management
├── requirements.txt            # Python dependencies
├── ENHANCEMENT_PLAN.md         # Detailed enhancement plan
├── IMPLEMENTATION_ROADMAP.md   # Implementation roadmap
├── IMPLEMENTATION_PROGRESS.md  # Progress report
└── README.md                   # Original project README
```

---

## Database Schema

### ChatSession
```sql
id            - Primary key
user_id       - Foreign key to User
name          - Session name (e.g., "Python Help")
model         - AI model name (e.g., "gemini-1.5-flash")
created_at    - Timestamp
updated_at    - Timestamp
is_active     - Boolean (soft delete)
```

### Chat
```sql
id            - Primary key
session_id    - Foreign key to ChatSession
message       - User message
response      - AI response
created_at    - Timestamp
is_deleted    - Boolean (soft delete)
```

---

## Key Features Explained

### Multiple Sessions
- Each user can create multiple chat sessions
- Sessions store separate conversation histories
- Switch between sessions without losing data
- Sessions sorted by most recent first

### Model Configuration
- Select which Gemini model to use
- Available models fetched from Gemini API
- Model selection saved per session
- Easy to switch models anytime

### Async Processing
1. Client submits message → returns immediately with `request_id`
2. Message queued in background processor
3. Client polls `/api/message/{request_id}/status/` every 500ms
4. When response ready, client updates UI
5. Message + response saved to database

**Benefits:**
- Non-blocking request handling
- Server can handle multiple concurrent requests
- Client doesn't need to wait for slow API
- Better UX with immediate feedback

### Responsive Design
- Works on desktop, tablet, mobile
- Sidebar collapses on small screens
- Touch-friendly buttons and inputs
- Optimized for all screen sizes

---

## Common Tasks

### Create a New Session
```javascript
// Via UI: Click "+ New Chat" button
// Via API:
fetch('/api/sessions/create/', {
  method: 'POST',
  body: new URLSearchParams({
    'csrfmiddlewaretoken': getCookie('csrftoken')
  })
})
```

### Send a Message
```javascript
// Synchronous (old way):
POST /chat/<session_id>/

// Asynchronous (new way):
POST /api/sessions/<session_id>/send/  // Returns request_id
GET  /api/message/<request_id>/status/ // Poll for response
```

### Change AI Model
1. Go to Settings
2. Select model from dropdown
3. Click "Test Model" (optional)
4. Click "Save Settings"

### Delete a Session
```javascript
// Via UI: Hover over session name, click 🗑️
// Via API:
fetch('/api/sessions/<id>/delete/', {
  method: 'POST',
  body: new URLSearchParams({
    'csrfmiddlewaretoken': getCookie('csrftoken')
  })
})
```

---

## Troubleshooting

### Issue: "Model not found" error
**Solution:** Check that you have a valid Gemini API key in `.env`

### Issue: Settings page won't load models
**Solution:**
- Check API_SECRET_KEY in `.env`
- Verify internet connection
- Check browser console for errors

### Issue: Messages not processing
**Solution:**
- Check that background processor thread is running
- Look at Django logs for errors
- Verify database is accessible

### Issue: Timeout waiting for response
**Solution:**
- Default timeout is 60 seconds
- Gemini API might be slow
- Try a shorter message
- Check network connectivity

---

## Performance Tips

### For Development
- Use SQLite (already configured)
- Enable Django Debug Toolbar
- Use `python manage.py runserver` for hot-reload

### For Production
1. **Cache**: Configure Redis/Memcached
   - Model list cached 1 hour
   - Responses cached during polling

2. **Database**: Migrate to PostgreSQL
   - Better for concurrent users
   - Faster queries with indexes

3. **Message Queue**: Migrate to Celery + Redis
   - Better scaling than threading
   - Persistent queue, no message loss
   - Can distribute across workers

4. **Web Server**: Use Gunicorn/uWSGI
   - Multiple worker processes
   - Better handling of concurrent requests

---

## Architecture Notes

### Message Flow
```
User Input
    ↓
Form Submit (AJAX)
    ↓
/api/sessions/<id>/send/
    ↓
Queue Message (MessageProcessor)
    ↓
Return request_id Immediately
    ↓
Client Polls /api/message/<request_id>/status/
    ↓
Background Worker Processes
    ↓
Calls Gemini API
    ↓
Saves to Database
    ↓
Polling Gets Response
    ↓
Update UI
```

### Threading Model
- Main Django thread: Handles HTTP requests
- Background worker: Single daemon thread processing queue
- Thread-safe: Uses `queue.Queue()` for thread-safe communication
- No race conditions: Each message has unique request_id

---

## Future Enhancements

### Phase 5 (Partial)
- [ ] Complete CSS architecture with variables
- [ ] Dark terminal aesthetic + AI glow
- [ ] Code block language badges
- [ ] Copy code button in code blocks
- [ ] Advanced animations

### Phase 6 (Planned)
- [ ] Comprehensive unit tests
- [ ] Integration tests
- [ ] Load testing (100 concurrent users)
- [ ] Accessibility testing (WCAG AA)

### Post-Launch
- [ ] WebSocket for real-time updates
- [ ] Chat export to JSON/PDF
- [ ] Conversation search
- [ ] Message editing/deletion
- [ ] Rich text editor with markdown preview
- [ ] File upload support
- [ ] Voice input/output

---

## Support

For issues or questions:
1. Check `IMPLEMENTATION_PROGRESS.md` for detailed info
2. Review Django logs: `python manage.py` commands
3. Check browser console (F12) for client errors
4. Review API responses with network tab

---

## License & Attribution

Original project: Django Gemini Chatbot
Enhancement: Multi-session, async processing, settings management
Date: November 2025

