# Django Gemini Chatbot - Enhancement Plan

## Executive Summary
This document outlines a comprehensive enhancement strategy for the Django-based Gemini chatbot. The proposed changes focus on four main areas: (1) Settings page with model configuration, (2) Multiple chat sessions support, (3) Thread-based async processing to prevent API congestion, and (4) Modern, distinctive UI design.

---

## FEATURE 1: Settings Page & Model Configuration

### Current State
- Hard-coded model: `gemini-1.5-flash`
- Unused `generate_model()` view exists but isn't routed
- No user-facing model selection interface

### Proposed Solution

#### Database Changes
**New Model: `ChatSession`**
```python
class ChatSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    model = models.CharField(max_length=100, default='gemini-1.5-flash')
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-created_at']
```

**Update: `Chat` Model**
```python
class Chat(models.Model):
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE)
    message = models.TextField()
    response = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
```

#### Views Required
1. **`settings(request)`** - Display user settings
   - Show list of available Gemini models (fetched from API)
   - Allow user to select default model for new sessions
   - Display current API status

2. **`api/models/`** (API endpoint) - Return available models as JSON
   - Fetch from Google Generative AI API
   - Cache results (TTL: 1 hour)
   - Format: `[{name: 'gemini-1.5-flash', display_name: 'Gemini 1.5 Flash'}, ...]`

3. **`api/settings/save/`** (API endpoint) - Save user settings
   - Accept POST with model selection
   - Validate model name against available models
   - Return success/error JSON

#### Frontend Changes
**New Page: `settings.html`**
- Settings header with navigation
- Model selector dropdown/radio buttons
- Display model capabilities and info
- Save button with confirmation feedback
- Test model connection button

#### URL Routing
```python
path('settings/', views.settings, name='settings'),
path('api/models/', views.api_models, name='api_models'),
path('api/settings/save/', views.api_settings_save, name='api_settings_save'),
```

---

## FEATURE 2: Multiple Chat Sessions

### Current State
- Single global chat for each user
- All messages stored in flat Chat model
- No session management

### Proposed Solution

#### User Experience
1. **Session Sidebar** (new UI component)
   - List of all user's chat sessions
   - Show session name and creation date
   - Indicator for active session
   - Hover to show actions: delete, rename, export

2. **Session Management**
   - New chat button → creates ChatSession, redirects to new chat
   - Click session → loads that session's messages
   - Rename session: double-click name or action menu
   - Delete session: confirmation dialog
   - Star/pin favorite sessions

3. **Session Persistence**
   - Browser remembers active session in localStorage
   - URL includes session ID: `/chat/session/{session_id}/`
   - Maintains scroll position per session

#### Views Required
1. **`session_list(request)`** - GET all user sessions
   - Return JSON: `[{id, name, model, message_count, last_message_date}, ...]`

2. **`session_create(request)`** - POST to create new session
   - Create ChatSession with default model
   - Return JSON with session details

3. **`session_detail(request, session_id)`** - GET single session
   - Verify ownership
   - Return session data with all messages

4. **`session_update(request, session_id)`** - POST to update session
   - Allow name, model, or is_active changes
   - Validate user ownership

5. **`session_delete(request, session_id)`** - POST to delete session
   - Soft delete or hard delete (user choice)
   - Cascade delete messages

#### URL Routing
```python
path('api/sessions/', views.api_session_list, name='api_session_list'),
path('api/sessions/create/', views.api_session_create, name='api_session_create'),
path('api/sessions/<int:session_id>/', views.api_session_detail, name='api_session_detail'),
path('api/sessions/<int:session_id>/update/', views.api_session_update, name='api_session_update'),
path('api/sessions/<int:session_id>/delete/', views.api_session_delete, name='api_session_delete'),
path('chat/', views.chatbot_home, name='chatbot_home'),
path('chat/<int:session_id>/', views.chatbot_session, name='chatbot_session'),
```

---

## FEATURE 3: Async Thread-Based Processing

### Current State
- Synchronous request handling
- Potential bottleneck if API is slow
- User sees loading spinner with no timeout

### Proposed Solution

#### Architecture
Use Django's `threading` module or `celery` for background task processing.

**Approach: Threading (simpler, no additional service)**
```python
import threading
import queue

# Request queue and response store
message_queue = queue.Queue()
response_cache = {}  # {request_id: response_text}

def process_messages():
    """Background thread that processes queued messages"""
    while True:
        request_id, user_id, session_id, message = message_queue.get()
        try:
            response = ask_gemini(message)
            response_cache[request_id] = response
            Chat.objects.create(
                session_id=session_id,
                message=message,
                response=response
            )
        except Exception as e:
            response_cache[request_id] = f"Error: {str(e)}"
        finally:
            message_queue.task_done()

# Start background thread on app startup
processor_thread = threading.Thread(target=process_messages, daemon=True)
processor_thread.start()
```

#### Views Required
1. **`send_message(request, session_id)`** - POST message
   - Generate request_id (UUID)
   - Queue message with metadata
   - Immediately return JSON with request_id
   - No blocking wait for response

2. **`check_response(request, request_id)`** - GET/poll for response
   - Check if response_cache has result
   - Return JSON: `{status: 'pending'|'completed'|'error', response: null|text}`
   - Allow client-side polling (every 500ms)

#### Frontend Changes
- Modify AJAX to not wait for response
- Implement polling mechanism (check status every 500ms)
- Show "Waiting..." state until response arrives
- Handle timeout (e.g., after 60 seconds)
- Display error if response returns error status

#### URL Routing
```python
path('api/message/send/', views.api_send_message, name='api_send_message'),
path('api/message/<str:request_id>/status/', views.api_check_response, name='api_check_response'),
```

#### Alternative: Use Celery (for production)
If you want a more robust async system:
- Install celery and redis
- Define task: `@shared_task def ask_gemini_async(message_id, user_id, session_id, message)`
- Replace threading with celery tasks
- Use Django signals to trigger tasks

---

## FEATURE 4: UI/UX Enhancements - Modern, Distinctive Design

### Current State
- Generic Bootstrap design
- Flat colors (#dcf8c6, #f1f0f0)
- Arial fonts
- No animations beyond loading spinner
- Centered single-column layout

### Proposed Aesthetic

#### Typography
- **Primary Font**: `JetBrains Mono` for code, `Inter` stripped (AVOID!)
- **Recommended**: `Grotesk` family or `Space Mono` for AI feels
- **Alternative Premium**: `Poppins`, `Sora`, `DM Sans`
- **Code Blocks**: Fira Code or IBM Plex Mono (distinctive monospace)

#### Color Scheme (NEW)
Instead of generic blues, adopt a **"Data Terminal" + "AI Glow" aesthetic**:

```css
/* Primary Palette */
--surface-primary: #0a0e27;      /* Deep navy/purple dark */
--surface-secondary: #1a1f3a;    /* Slightly lighter */
--accent-primary: #00d9ff;       /* Cyan/electric blue */
--accent-secondary: #ff006e;     /* Hot pink/magenta */
--accent-tertiary: #ffbe0b;      /* Bright yellow */

/* Text */
--text-primary: #e0e0e0;         /* Light gray */
--text-secondary: #a0a0a0;       /* Medium gray */
--text-accent: #00d9ff;          /* Cyan */

/* Semantic */
--success: #06d6a0;              /* Teal */
--error: #ff006e;                /* Pink */
--warning: #ffbe0b;              /* Yellow */
```

#### Layout Changes
**New sidebar layout:**
```
┌─────────────────────────────────────┐
│ Logo | Settings                     │
├─────────┬───────────────────────────┤
│ Sessions│  Chat Window              │
│ ─────  │                           │
│ Chat 1 │  ┌──────────────────────┐ │
│ Chat 2 │  │ AI: Hello there!     │ │
│ Chat 3 │  │                      │ │
│ +New   │  │ You: Hi!             │ │
│ ─────  │  │                      │ │
│ Search │  │ Input Box            │ │
│        │  └──────────────────────┘ │
└─────────┴───────────────────────────┘
```

**Features:**
- Collapsible sidebar (hamburger on mobile)
- Session search/filter
- Pinned sessions at top
- Last message preview in session list
- Active session highlighted

#### Animations & Motion
1. **Page Load**: Staggered fade-in (0.2s each)
   - Logo/header → Sidebar → Main content

2. **Message Arrival**:
   - Slide in from bottom (200ms)
   - Fade in with slight scale (0.95 → 1)

3. **Session Hover**:
   - Subtle background shift (50ms)
   - Action buttons fade in
   - Cursor changes to pointer

4. **Loading State**:
   - Replace spinner with animated gradient pulse
   - Shimmer effect on message container

5. **Button Interactions**:
   - Hover: Scale 1.05, slight glow
   - Click: Scale 0.98 (press effect)
   - Ripple effect on release

#### Background & Depth
- **Main background**: Subtle radial gradient from center
  ```css
  background: radial-gradient(
    ellipse at bottom right,
    rgba(0, 217, 255, 0.1),
    rgba(255, 0, 110, 0.05),
    rgba(10, 14, 39, 1) 100%
  );
  ```
- **Glass morphism** for message bubbles:
  ```css
  backdrop-filter: blur(10px);
  border: 1px solid rgba(0, 217, 255, 0.2);
  ```
- **Card elevation**: Use box-shadow with multiple layers
  ```css
  box-shadow:
    0 10px 30px rgba(0, 0, 0, 0.3),
    inset 0 1px 0 rgba(255, 255, 255, 0.1);
  ```

#### Code Block Enhancements
- **Language badge** in top-right corner
- **Copy button** that shows success feedback
- **Line numbers** for code
- **Syntax highlighting** using Prism.js (not just language classes)
- **Theme-aware** background (darker than messages)

#### Responsive Design
- **Desktop**: Sidebar + main (described above)
- **Tablet**: Collapsible sidebar, full chat width
- **Mobile**: Bottom sheet for sessions, full-width chat
  - Slide up from bottom to see sessions
  - Swipe gestures to navigate

#### Dark Mode Enforcement
- This design is dark-first (no light mode)
- Uses high contrast for accessibility
- WCAG AA compliant color ratios

### HTML Structure (conceptual)
```html
<div class="app-container">
  <aside class="sidebar">
    <div class="sidebar-header">
      <img src="logo.svg" alt="Gemini Chat">
      <button class="settings-btn">⚙️</button>
    </div>
    <div class="sessions-list">
      <button class="new-session-btn">+ New Chat</button>
      <div class="search-box">
        <input type="search" placeholder="Search sessions...">
      </div>
      <div class="sessions-container">
        <!-- Sessions rendered here -->
      </div>
    </div>
  </aside>

  <main class="chat-container">
    <div class="messages-area">
      <!-- Messages rendered here -->
    </div>
    <div class="input-area">
      <textarea placeholder="Ask anything..."></textarea>
      <button type="submit">Send</button>
    </div>
  </main>
</div>
```

### CSS Organization
Create separate files:
- `styles/base.css` - Reset, variables, animations
- `styles/layout.css` - Grid, sidebar, responsive
- `styles/components.css` - Buttons, cards, messages
- `styles/code-blocks.css` - Code syntax and styling
- `styles/animations.css` - Keyframes and transitions

---

## Implementation Priority

### Phase 1 (MVP - 2-3 weeks)
1. Database changes (ChatSession model)
2. Settings page with model selection
3. Multiple sessions UI (sidebar)
4. Basic session switching

### Phase 2 (Polish - 1-2 weeks)
1. Async/threading implementation
2. Response polling mechanism
3. Error handling and timeouts

### Phase 3 (Polish - 1-2 weeks)
1. New CSS styling (dark terminal aesthetic)
2. Animations and transitions
3. Code block enhancements
4. Responsive refinements

---

## Technical Debt & Considerations

### Security
- Validate model names server-side against whitelist
- Sanitize session names (XSS prevention)
- Ensure user can only access own sessions
- Rate limit API calls to prevent abuse

### Performance
- Cache available models list (1 hour TTL)
- Implement pagination for session list (50 per page)
- Use database indexes on `(user_id, created_at)`
- Consider lazy-loading message history

### Database
- Migration strategy for existing Chat records
  - Option A: Keep as-is, create ChatSession for each user with all Chats
  - Option B: Archive old Chats, start fresh with ChatSession model

### API Limits
- Gemini API may have rate limits
- Implement exponential backoff for retries
- Queue system helps smooth burst requests
- Monitor API quotas

### Scalability
- Threading solution works for single-process dev
- For production with multiple workers (Gunicorn), use Celery + Redis
- Database connection pooling may be needed

---

## Files Affected

### New Files
- `chatbot/models.py` (add ChatSession)
- `templates/settings.html` (new)
- `templates/base.html` (update navbar)
- `templates/chatbot.html` (significant refactor)
- `static/css/styles/base.css` (new)
- `static/css/styles/layout.css` (new)
- `static/css/styles/components.css` (new)
- `static/css/styles/animations.css` (new)
- `static/js/session-manager.js` (new)
- `static/js/message-handler.js` (new)

### Modified Files
- `chatbot/views.py` (add new views, refactor existing)
- `chatbot/urls.py` (add new routes)
- `templates/base.html` (add sidebar, navigation)
- `templates/chatbot.html` (major refactor)

### Migration Files
- `chatbot/migrations/0002_chatsession.py` (auto-generated)
- `chatbot/migrations/0003_alter_chat.py` (alter Chat model)

---

## Testing Strategy

### Unit Tests
- Test ChatSession creation/deletion
- Test model selection validation
- Test response queue processing
- Test API endpoint authorization

### Integration Tests
- User creates session → messages flow → session appears in list
- Model change affects new messages
- Session deletion cascades properly
- Message threading doesn't lose data

### UI Tests
- Sidebar responsive on all screen sizes
- Session switching preserves scroll position
- Animations don't break on low-end devices
- Code blocks render correctly

### Load Tests
- 100 concurrent users sending messages
- Message queue handles 1000+ queued items
- Response polling doesn't overwhelm server

---

## Rollout Plan

1. **Feature branch**: `feature/multi-session-settings`
2. **Testing**: Local + staging environment
3. **Migration**: Run migrations safely with backup
4. **Gradual rollout**: Deploy to 10% of users, monitor
5. **Full rollout**: After 1 week without issues
6. **Feedback**: Collect user input on new features

