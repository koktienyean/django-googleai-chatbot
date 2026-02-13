# Django Gemini Chatbot - Implementation Roadmap

## Overview
This document outlines a detailed, step-by-step implementation plan with specific tasks, dependencies, and estimated effort for all four enhancement features.

---

## PHASE 1: DATABASE & MODEL SETUP (Week 1)

### 1.1 Update Models
**File**: `chatbot/models.py`
**Effort**: 2 hours
**Status**: Ready to implement

#### Changes:
1. Create `ChatSession` model
   ```python
   class ChatSession(models.Model):
       user = models.ForeignKey(User, on_delete=models.CASCADE)
       name = models.CharField(max_length=200)
       model = models.CharField(max_length=100, default='gemini-1.5-flash')
       created_at = models.DateTimeField(auto_now_add=True)
       updated_at = models.DateTimeField(auto_now=True)
       is_active = models.BooleanField(default=True)

       class Meta:
           ordering = ['-created_at']

       def __str__(self):
           return f"{self.user.username} - {self.name}"
   ```

2. Update `Chat` model
   - Replace `user` FK with `session` FK
   - Add `is_deleted` field for soft deletes
   ```python
   class Chat(models.Model):
       session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages')
       message = models.TextField()
       response = models.TextField()
       created_at = models.DateTimeField(auto_now_add=True)
       is_deleted = models.BooleanField(default=False)

       def __str__(self):
           return f"{self.session.name} - {self.message[:50]}"

       def response_md(self):
           return mark_safe(md.convert(self.response))
   ```

3. Create database migration
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

### 1.2 Handle Data Migration
**File**: `chatbot/migrations/0002_data_migration.py`
**Effort**: 1 hour
**Status**: After schema migration

#### Steps:
1. Create data migration to move existing Chats to ChatSessions
   ```bash
   python manage.py makemigrations --empty chatbot --name migrate_chats_to_sessions
   ```

2. Write migration logic:
   - For each user with Chat records
   - Create ChatSession per user named "Previous Chats"
   - Link all Chat records to that session

---

## PHASE 2: SETTINGS PAGE & MODEL CONFIGURATION (Week 1-2)

### 2.1 Create Settings View & API Endpoints
**File**: `chatbot/views.py`
**Effort**: 3 hours
**Status**: After Phase 1

#### New Views:
1. `settings_page(request)` - Render settings.html
   - Fetch user's current settings
   - Pass available models to template

2. `api_list_models(request)` - GET available models
   - Fetch from Google Generative AI API
   - Cache results for 1 hour
   - Return JSON: `[{id, name, display_name, capabilities}, ...]`

3. `api_save_settings(request)` - POST user settings
   - Validate model name
   - Save to database
   - Return success/error JSON

4. `api_test_model(request)` - POST test message
   - Test connection to selected model
   - Return status and sample response

#### Implementation Details:
```python
import functools
from datetime import datetime, timedelta
from django.core.cache import cache

def api_list_models(request):
    """Fetch available Gemini models with caching"""
    cache_key = 'gemini_models_list'
    models = cache.get(cache_key)

    if not models:
        try:
            models = genai.list_models()
            # Filter for generateContent capable models
            models = [m for m in models if 'generateContent' in m.supported_generation_methods]
            cache.set(cache_key, models, timeout=3600)  # 1 hour
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({
        'models': [{'name': m.name, 'display': m.display_name} for m in models]
    })

def api_save_settings(request):
    """Save user model preference"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=400)

    model_name = request.POST.get('model')

    # Validate model exists
    try:
        genai.GenerativeModel(model_name)
    except:
        return JsonResponse({'error': 'Invalid model'}, status=400)

    # Save to user settings (create UserProfile model or use simple JSON field)
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    profile.default_model = model_name
    profile.save()

    return JsonResponse({'success': True, 'message': 'Settings saved'})
```

### 2.2 Create Settings Template & Frontend
**File**: `templates/settings.html`
**Effort**: 2 hours
**Status**: After API endpoints created

#### Features:
1. Model selection dropdown
2. Current model indicator
3. Model capabilities display
4. Test model button
5. Save button with feedback
6. API status indicator

#### HTML Structure:
```html
{% extends 'base.html' %}

{% block content %}
<div class="settings-container">
    <h2>Settings</h2>

    <div class="settings-section">
        <h3>AI Model Selection</h3>
        <select id="model-select">
            <option>Loading models...</option>
        </select>
        <button id="test-model-btn">Test Model</button>
        <button id="save-settings-btn">Save Settings</button>
        <div id="status-message"></div>
    </div>
</div>

<script>
    // Fetch and populate models
    fetch('/api/models/')
        .then(r => r.json())
        .then(data => {
            const select = document.getElementById('model-select');
            select.innerHTML = '';
            data.models.forEach(m => {
                const opt = document.createElement('option');
                opt.value = m.name;
                opt.textContent = m.display;
                select.appendChild(opt);
            });
        });

    // Save settings
    document.getElementById('save-settings-btn').addEventListener('click', () => {
        const model = document.getElementById('model-select').value;
        fetch('/api/settings/save/', {
            method: 'POST',
            headers: {'Content-Type': 'application/x-www-form-urlencoded'},
            body: new URLSearchParams({'model': model, 'csrfmiddlewaretoken': getCookie('csrftoken')})
        })
        .then(r => r.json())
        .then(d => {
            document.getElementById('status-message').textContent = d.success ? 'Saved!' : d.error;
        });
    });
</script>
{% endblock %}
```

### 2.3 Update URL Routes
**File**: `chatbot/urls.py`
**Effort**: 30 minutes

#### New Routes:
```python
path('settings/', views.settings_page, name='settings'),
path('api/models/', views.api_list_models, name='api_models'),
path('api/settings/save/', views.api_save_settings, name='api_settings_save'),
path('api/model/test/', views.api_test_model, name='api_test_model'),
```

### 2.4 Update Base Template Navigation
**File**: `templates/base.html`
**Effort**: 30 minutes

#### Changes:
- Add settings link to navbar
- Add logout link
- Update navbar styling for new design

---

## PHASE 3: MULTIPLE CHAT SESSIONS (Week 2-3)

### 3.1 Create Session Management Views
**File**: `chatbot/views.py`
**Effort**: 4 hours
**Status**: After Phase 1

#### Views to Add:
1. `session_list(request)` - GET all user sessions
2. `session_create(request)` - POST create new session
3. `session_detail(request, session_id)` - GET session data
4. `session_update(request, session_id)` - POST update session
5. `session_delete(request, session_id)` - POST delete session
6. `session_export(request, session_id)` - GET export as JSON/PDF

#### Key Implementation:
```python
from django.http import JsonResponse
from django.shortcuts import get_object_or_404

def api_session_list(request):
    """Get all sessions for user"""
    sessions = ChatSession.objects.filter(user=request.user, is_active=True)
    return JsonResponse({
        'sessions': [{
            'id': s.id,
            'name': s.name,
            'model': s.model,
            'message_count': s.messages.count(),
            'created_at': s.created_at.isoformat(),
            'last_updated': s.updated_at.isoformat(),
        } for s in sessions]
    })

def api_session_create(request):
    """Create new chat session"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=400)

    name = request.POST.get('name', 'New Chat')
    model = request.POST.get('model', 'gemini-1.5-flash')

    session = ChatSession.objects.create(
        user=request.user,
        name=name,
        model=model
    )

    return JsonResponse({
        'id': session.id,
        'name': session.name,
        'model': session.model,
        'created_at': session.created_at.isoformat()
    })

def api_session_detail(request, session_id):
    """Get single session with all messages"""
    session = get_object_or_404(ChatSession, id=session_id, user=request.user)
    messages = session.messages.filter(is_deleted=False).order_by('created_at')

    return JsonResponse({
        'session': {
            'id': session.id,
            'name': session.name,
            'model': session.model,
        },
        'messages': [{
            'id': m.id,
            'message': m.message,
            'response': m.response_md(),
            'created_at': m.created_at.isoformat(),
        } for m in messages]
    })

def api_session_delete(request, session_id):
    """Delete session"""
    session = get_object_or_404(ChatSession, id=session_id, user=request.user)
    hard_delete = request.POST.get('hard_delete', False) == 'true'

    if hard_delete:
        session.delete()
    else:
        session.is_active = False
        session.save()

    return JsonResponse({'success': True})
```

### 3.2 Update Chatbot View for Sessions
**File**: `chatbot/views.py`
**Effort**: 2 hours
**Status**: After session views created

#### Refactor `chatbot` view:
```python
@login_required
def chatbot_home(request):
    """Redirect to latest active session or create one"""
    latest = ChatSession.objects.filter(
        user=request.user,
        is_active=True
    ).first()

    if latest:
        return redirect('chatbot_session', session_id=latest.id)

    # Create default session
    session = ChatSession.objects.create(
        user=request.user,
        name='Chat'
    )
    return redirect('chatbot_session', session_id=session.id)

@login_required
def chatbot_session(request, session_id):
    """Main chat view for specific session"""
    session = get_object_or_404(ChatSession, id=session_id, user=request.user)

    if request.method == 'POST':
        message = request.POST.get('message')
        response = ask_gemini(request, message, session.model)

        chat = Chat.objects.create(
            session=session,
            message=message,
            response=response
        )

        return JsonResponse({
            'message': message,
            'response': chat.response_md(),
            'id': chat.id
        })

    messages = session.messages.filter(is_deleted=False)
    return render(request, 'chatbot.html', {
        'session': session,
        'messages': messages
    })
```

### 3.3 Update Chatbot Template for Sessions
**File**: `templates/chatbot.html`
**Effort**: 3 hours
**Status**: After session views complete

#### Major Changes:
1. Add sidebar with session list
2. Refactor message rendering
3. Add session header with model display
4. Add new chat button
5. Add session rename/delete actions

#### Structure:
```html
{% extends 'base.html' %}

{% block content %}
<div class="chat-wrapper">
    <!-- Sidebar -->
    <aside class="sessions-sidebar">
        <button class="new-chat-btn" id="new-chat">+ New Chat</button>
        <input type="search" id="session-search" placeholder="Search...">
        <div class="sessions-list" id="sessions-list">
            <!-- Sessions rendered by JS -->
        </div>
    </aside>

    <!-- Main Chat -->
    <div class="chat-container">
        <div class="session-header">
            <h2 id="session-name">{{ session.name }}</h2>
            <span class="model-badge">{{ session.model }}</span>
            <button class="menu-btn">⋮</button>
        </div>

        <div class="messages-box" id="messages-box">
            <!-- Messages rendered here -->
        </div>

        <form class="message-form" id="message-form">
            {% csrf_token %}
            <textarea class="message-input" placeholder="Type message..."></textarea>
            <button type="submit" class="btn-send">Send</button>
        </form>
    </div>
</div>

<script src="/static/js/session-manager.js"></script>
<script src="/static/js/message-handler.js"></script>
{% endblock %}
```

### 3.4 Create Frontend Session Manager
**File**: `static/js/session-manager.js`
**Effort**: 2 hours
**Status**: After template updates

#### Functions:
- `loadSessions()` - Fetch all sessions
- `createSession()` - POST new session
- `switchSession(sessionId)` - Load different session
- `renameSession(sessionId, newName)` - Update session name
- `deleteSession(sessionId)` - Delete session
- `renderSessionList()` - Update DOM

### 3.5 Update Message Handler for Sessions
**File**: `static/js/message-handler.js`
**Effort**: 1 hour
**Status**: After session manager created

#### Updates:
- Modify form submission to use current session ID
- Update POST endpoint to `/chat/{session_id}/`
- Maintain message list per session

### 3.6 Update URL Routes
**File**: `chatbot/urls.py`
**Effort**: 30 minutes

#### Add Routes:
```python
path('', views.chatbot_home, name='chatbot_home'),
path('chat/<int:session_id>/', views.chatbot_session, name='chatbot_session'),
path('api/sessions/', views.api_session_list, name='api_session_list'),
path('api/sessions/create/', views.api_session_create, name='api_session_create'),
path('api/sessions/<int:session_id>/', views.api_session_detail, name='api_session_detail'),
path('api/sessions/<int:session_id>/update/', views.api_session_update, name='api_session_update'),
path('api/sessions/<int:session_id>/delete/', views.api_session_delete, name='api_session_delete'),
```

---

## PHASE 4: ASYNC THREAD-BASED PROCESSING (Week 3-4)

### 4.1 Implement Message Queue System
**File**: `chatbot/message_queue.py` (new)
**Effort**: 3 hours
**Status**: Can start after Phase 1

#### Implementation:
```python
import threading
import queue
import uuid
from datetime import datetime
from django.core.cache import cache
from . import views

class MessageQueue:
    def __init__(self):
        self.queue = queue.Queue()
        self.responses = {}  # request_id -> response
        self.worker_thread = threading.Thread(target=self._worker, daemon=True)
        self.worker_thread.start()

    def _worker(self):
        """Background worker processing messages"""
        while True:
            try:
                request_id, user_id, session_id, message = self.queue.get(timeout=1)

                # Get model from session
                from .models import ChatSession
                session = ChatSession.objects.get(id=session_id)

                # Process message
                response = self._ask_gemini(message, session.model)

                # Store response
                self.responses[request_id] = {
                    'status': 'completed',
                    'response': response,
                    'timestamp': datetime.now().isoformat()
                }

                # Save to database
                Chat.objects.create(
                    session=session,
                    message=message,
                    response=response
                )

            except queue.Empty:
                continue
            except Exception as e:
                self.responses[request_id] = {
                    'status': 'error',
                    'error': str(e)
                }

    def _ask_gemini(self, message, model='gemini-1.5-flash'):
        """Call Gemini API"""
        genai.configure(api_key=os.getenv('API_SECRET_KEY'))
        model_obj = genai.GenerativeModel(model)
        chat = model_obj.start_chat()
        response = chat.send_message(message)
        return response.text

    def queue_message(self, user_id, session_id, message):
        """Queue a message for processing"""
        request_id = str(uuid.uuid4())
        self.queue.put((request_id, user_id, session_id, message))
        return request_id

    def get_response(self, request_id):
        """Get response status"""
        if request_id in self.responses:
            response = self.responses[request_id]
            # Clean up after retrieval (optional)
            # del self.responses[request_id]
            return response
        return {'status': 'pending'}

# Global queue instance
message_processor = MessageQueue()
```

### 4.2 Update Views for Async Processing
**File**: `chatbot/views.py`
**Effort**: 2 hours
**Status**: After queue system created

#### New Views:
1. `api_send_message(request, session_id)` - Queue message, return immediately
2. `api_check_response(request, request_id)` - Poll for response status

#### Implementation:
```python
from .message_queue import message_processor

def api_send_message(request, session_id):
    """Queue message and return request ID"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=400)

    session = get_object_or_404(ChatSession, id=session_id, user=request.user)
    message = request.POST.get('message', '').strip()

    if not message:
        return JsonResponse({'error': 'Empty message'}, status=400)

    # Queue the message
    request_id = message_processor.queue_message(
        request.user.id,
        session_id,
        message
    )

    # Return request ID immediately
    return JsonResponse({
        'request_id': request_id,
        'status': 'queued'
    })

def api_check_response(request, request_id):
    """Check if response is ready"""
    response = message_processor.get_response(request_id)
    return JsonResponse(response)
```

### 4.3 Update Frontend for Polling
**File**: `static/js/message-handler.js`
**Effort**: 2 hours
**Status**: After async views created

#### Implementation:
```javascript
const POLL_INTERVAL = 500;  // Check every 500ms
const TIMEOUT = 60000;      // Give up after 60s

async function sendMessage(message, sessionId) {
    // 1. Send message, get request_id
    const sendResponse = await fetch(`/chat/${sessionId}/send/`, {
        method: 'POST',
        body: new URLSearchParams({
            'message': message,
            'csrfmiddlewaretoken': getCookie('csrftoken')
        })
    });

    const sendData = await sendResponse.json();
    const requestId = sendData.request_id;

    // 2. Add to UI with loading state
    const messageEl = addMessageToUI(message, 'sent');
    const responseEl = addMessageToUI('', 'received', 'loading');

    // 3. Start polling for response
    const startTime = Date.now();
    const pollResponse = setInterval(async () => {
        const checkResponse = await fetch(`/message/${requestId}/status/`);
        const status = await checkResponse.json();

        if (status.status === 'completed') {
            clearInterval(pollResponse);
            responseEl.textContent = status.response;
            responseEl.classList.remove('loading');
        } else if (status.status === 'error') {
            clearInterval(pollResponse);
            responseEl.textContent = `Error: ${status.error}`;
            responseEl.classList.add('error');
        } else if (Date.now() - startTime > TIMEOUT) {
            clearInterval(pollResponse);
            responseEl.textContent = 'Timeout - please try again';
            responseEl.classList.add('error');
        }
    }, POLL_INTERVAL);
}
```

### 4.4 Update URL Routes
**File**: `chatbot/urls.py`
**Effort**: 30 minutes

#### Add Routes:
```python
path('chat/<int:session_id>/send/', views.api_send_message, name='api_send_message'),
path('message/<str:request_id>/status/', views.api_check_response, name='api_check_response'),
```

---

## PHASE 5: UI/UX DESIGN OVERHAUL (Week 4-5)

### 5.1 Create CSS Architecture
**File**: `static/css/` (new directory)
**Effort**: 1 hour
**Status**: Independent

#### Files:
1. `base.css` - Variables, reset, animations
2. `layout.css` - Grid, sidebar, responsive
3. `components.css` - Buttons, cards, messages
4. `code-blocks.css` - Code highlighting
5. `animations.css` - Keyframes

#### Key Variables (base.css):
```css
:root {
    --surface-primary: #0a0e27;
    --surface-secondary: #1a1f3a;
    --accent-primary: #00d9ff;
    --accent-secondary: #ff006e;
    --accent-tertiary: #ffbe0b;
    --text-primary: #e0e0e0;
    --text-secondary: #a0a0a0;
    --success: #06d6a0;
    --error: #ff006e;
}
```

### 5.2 Refactor Base Template
**File**: `templates/base.html`
**Effort**: 1 hour
**Status**: After CSS created

#### Changes:
- Replace Bootstrap with custom CSS
- Update navbar styling
- Add CSS imports
- Update meta tags

### 5.3 Refactor Chat Template
**File**: `templates/chatbot.html`
**Effort**: 3 hours
**Status**: After base template and CSS done

#### Updates:
- Implement sidebar layout
- Update message styling with glass morphism
- Add animations
- Refactor HTML structure
- Remove Bootstrap dependencies

### 5.4 Refactor Auth Templates
**File**: `templates/login.html`, `templates/register.html`
**Effort**: 2 hours
**Status**: After CSS framework done

#### Changes:
- Apply new color scheme
- Update animations
- Improve responsive design
- Remove Bootstrap

### 5.5 Create Code Block Component
**File**: `static/js/code-block-renderer.js` (new)
**Effort**: 2 hours
**Status**: After base CSS done

#### Features:
- Language badge
- Copy button with feedback
- Line numbers
- Syntax highlighting (Prism.js integration)

#### Implementation:
```javascript
function enhanceCodeBlocks() {
    document.querySelectorAll('pre > code').forEach(codeBlock => {
        const language = codeBlock.className.split('language-')[1] || 'text';

        // Create wrapper
        const wrapper = document.createElement('div');
        wrapper.className = 'code-block-wrapper';

        // Add header
        const header = document.createElement('div');
        header.className = 'code-block-header';
        header.innerHTML = `
            <span class="language-badge">${language}</span>
            <button class="copy-btn" title="Copy code">Copy</button>
        `;

        codeBlock.parentElement.insertBefore(header, codeBlock);
        codeBlock.parentElement.classList.add('code-block');

        // Copy handler
        header.querySelector('.copy-btn').addEventListener('click', () => {
            navigator.clipboard.writeText(codeBlock.textContent);
            // Show "Copied!" feedback
        });
    });
}
```

### 5.6 Add Animations Library
**File**: `static/css/animations.css`
**Effort**: 1 hour
**Status**: After layout CSS done

#### Keyframes:
- `fade-in` - Opacity 0 to 1
- `slide-up` - Transform Y position
- `scale-pop` - Scale 0.95 to 1
- `shimmer` - Gradient animation for loading
- `pulse-glow` - Glowing pulse effect

---

## PHASE 6: TESTING & REFINEMENT (Week 5)

### 6.1 Unit Tests
**File**: `chatbot/tests.py`
**Effort**: 3 hours

#### Test Cases:
- ChatSession creation/deletion
- Model selection validation
- Message queue functionality
- Response polling
- Authorization checks

### 6.2 Integration Tests
**File**: `chatbot/tests.py`
**Effort**: 2 hours

#### Scenarios:
- User creates session → sends message → receives response
- Session switching preserves history
- Model change works correctly
- Async processing completes

### 6.3 UI/UX Testing
**Effort**: 2 hours

#### Manual Tests:
- Responsive design (mobile, tablet, desktop)
- Animation smoothness
- Cross-browser compatibility
- Accessibility (keyboard nav, contrast)

### 6.4 Performance Testing
**Effort**: 1 hour

#### Load Tests:
- 10 concurrent users
- 100 queued messages
- Memory usage of queue
- Database query optimization

---

## TIMELINE & DEPENDENCIES

```
PHASE 1 (Week 1)
├─ 1.1 Models (2h)
├─ 1.2 Migration (1h)
└─ Status: BLOCKING for Phases 2-4

PHASE 2 (Week 1-2) - Depends on Phase 1
├─ 2.1 Views (3h)
├─ 2.2 Template (2h)
├─ 2.3 URLs (0.5h)
└─ Status: Can start after 1.1 complete

PHASE 3 (Week 2-3) - Depends on Phase 1
├─ 3.1 Session Views (4h)
├─ 3.2 Chatbot Refactor (2h)
├─ 3.3 Template (3h)
├─ 3.4 JS Manager (2h)
├─ 3.5 Message Handler (1h)
├─ 3.6 URLs (0.5h)
└─ Status: Can start after 1.1 complete

PHASE 4 (Week 3-4) - Depends on Phase 1, 3
├─ 4.1 Queue System (3h)
├─ 4.2 Async Views (2h)
├─ 4.3 Frontend Polling (2h)
└─ 4.4 URLs (0.5h)

PHASE 5 (Week 4-5) - Can start Week 1
├─ 5.1 CSS Setup (1h)
├─ 5.2 Base Template (1h)
├─ 5.3 Chat Template (3h)
├─ 5.4 Auth Templates (2h)
├─ 5.5 Code Blocks (2h)
└─ 5.6 Animations (1h)

PHASE 6 (Week 5) - After all phases
├─ 6.1 Unit Tests (3h)
├─ 6.2 Integration Tests (2h)
├─ 6.3 UI Testing (2h)
└─ 6.4 Performance (1h)
```

## CRITICAL PATH
**Minimum timeline: 5 weeks (with parallel work)**
- Week 1: Phase 1 + Phase 2 + Phase 5.1
- Week 2: Phase 2 complete + Phase 3 start + Phase 5.2-5.4
- Week 3: Phase 3 complete + Phase 4 start + Phase 5.5-5.6
- Week 4: Phase 4 complete + Polish
- Week 5: Testing + Bug fixes + Deployment

## EFFORT SUMMARY

| Phase | Total Hours | Dependencies |
|-------|-------------|--------------|
| 1 | 3h | None |
| 2 | 6h | Phase 1 |
| 3 | 13h | Phase 1 |
| 4 | 7.5h | Phase 1, 3 |
| 5 | 10h | Independent |
| 6 | 8h | All phases |
| **Total** | **47.5h** | **~6 weeks** |

---

## ROLLOUT STRATEGY

### Development Environment
1. Create feature branch: `feature/all-enhancements`
2. Develop all phases in isolated features
3. Daily commits with clear messages

### Staging Environment
1. Deploy after Phase 1 (database changes)
2. Run migrations in staging
3. Test data migration logic
4. Run all test suites

### Production Deployment
1. **Backup database** before migration
2. Run migrations: `python manage.py migrate`
3. Monitor for errors
4. Gradual rollout to 10% of users
5. Monitor performance and errors
6. Full rollout if stable

### Post-Launch
1. Collect user feedback
2. Fix critical issues immediately
3. Plan Phase 2 refinements
4. Monitor queue performance

---

## Risk Mitigation

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|-----------|
| Database migration fails | Medium | Critical | Test in staging first, have rollback plan |
| Queue system loses messages | Low | Critical | Use database backup, implement logging |
| API rate limits exceeded | Medium | High | Implement backoff + queue batching |
| CSS conflicts with existing styles | Low | Medium | Use CSS modules or BEM naming |
| Performance degradation | Medium | High | Profile early, optimize queries |
| Threading issues | Medium | High | Extensive testing, use Celery for prod |

---

## Success Criteria

- ✅ All unit tests pass
- ✅ All integration tests pass
- ✅ Settings page fully functional
- ✅ Multiple sessions work correctly
- ✅ Async queue processes messages reliably
- ✅ UI loads and responds smoothly (<200ms)
- ✅ Code blocks render with syntax highlighting
- ✅ Mobile responsive design verified
- ✅ No database errors on migration
- ✅ Zero message loss in queue system

