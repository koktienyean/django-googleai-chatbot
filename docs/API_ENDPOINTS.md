# API Endpoints - Django Data Integration

**Date**: November 27, 2025
**Status**: Available for implementation

---

## Overview

While Django Data Integration primarily works through Gemini function calling, REST API endpoints can be added for:

- Direct data access from frontend
- Programmatic integration
- Mobile app support
- Custom analytics

---

## Optional API Endpoints

These are **NOT currently implemented** but can be added easily.

### 1. Search Chat History

```
GET /api/chats/search/?keyword=django&limit=5
```

**Response**:
```json
{
  "count": 2,
  "results": [
    {
      "id": 5,
      "message": "How do I authenticate users in Django?",
      "response_preview": "Use Django's built-in auth system...",
      "created_at": "2025-11-27 10:30",
      "session": "Django Discussion"
    }
  ]
}
```

### 2. Get Chat Statistics

```
GET /api/statistics/
```

**Response**:
```json
{
  "total_messages": 42,
  "total_sessions": 5,
  "most_active_session": "Python Tips",
  "messages_this_week": 8,
  "account_created": "2025-11-20"
}
```

### 3. Get Recent Conversations

```
GET /api/conversations/recent/?limit=5
```

**Response**:
```json
{
  "count": 5,
  "conversations": [
    {
      "id": 42,
      "message": "Explain decorators",
      "response_preview": "Decorators are functions that modify...",
      "created_at": "2025-11-27 14:22:15",
      "session": "Python Tips"
    }
  ]
}
```

### 4. Search by Date Range

```
GET /api/chats/by-date/?start=2025-11-20&end=2025-11-25
```

**Response**:
```json
{
  "count": 12,
  "date_range": "2025-11-20 to 2025-11-25",
  "conversations": [...]
}
```

### 5. Get Session Details

```
GET /api/sessions/10/
```

**Response**:
```json
{
  "session_name": "Django Discussion",
  "session_model": "gemini-2.0-flash",
  "created_at": "2025-11-20 09:15",
  "message_count": 8,
  "last_message_at": "2025-11-27 14:30",
  "first_message_preview": "How do I..."
}
```

### 6. List All Sessions

```
GET /api/sessions/?limit=10
```

**Response**:
```json
{
  "count": 5,
  "sessions": [
    {
      "id": 10,
      "name": "Django Discussion",
      "model": "gemini-2.0-flash",
      "message_count": 8,
      "created_at": "2025-11-20 09:15",
      "last_updated": "2025-11-27 14:30"
    }
  ]
}
```

---

## Implementation (Optional)

### To Add These Endpoints

Add to `urls.py`:

```python
urlpatterns = [
    # ... existing URLs ...

    # Data integration APIs
    path('api/chats/search/', views.api_search_chats, name='api_search_chats'),
    path('api/statistics/', views.api_get_statistics, name='api_statistics'),
    path('api/conversations/recent/', views.api_recent_conversations, name='api_recent_conversations'),
    path('api/chats/by-date/', views.api_search_by_date, name='api_search_by_date'),
    path('api/sessions/<int:session_id>/details/', views.api_session_details, name='api_session_details'),
]
```

Add to `views.py`:

```python
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required

@login_required
def api_search_chats(request):
    """Search user's chat history"""
    keyword = request.GET.get('keyword', '')
    limit = int(request.GET.get('limit', 5))

    if not keyword:
        return JsonResponse({'error': 'keyword parameter required'}, status=400)

    result = search_my_chats(request.user, keyword, limit)
    return JsonResponse(result)

@login_required
def api_get_statistics(request):
    """Get user's chat statistics"""
    stats = get_chat_statistics(request.user)
    return JsonResponse(stats)

@login_required
def api_recent_conversations(request):
    """Get recent conversations"""
    limit = int(request.GET.get('limit', 5))
    result = get_recent_conversations(request.user, limit)
    return JsonResponse(result)

@login_required
def api_search_by_date(request):
    """Search conversations by date range"""
    start = request.GET.get('start')
    end = request.GET.get('end')

    if not start or not end:
        return JsonResponse({'error': 'start and end parameters required'}, status=400)

    result = search_by_date_range(request.user, start, end)
    return JsonResponse(result)

@login_required
def api_session_details(request, session_id):
    """Get session details"""
    result = get_session_summary(request.user, session_id)
    return JsonResponse(result)
```

---

## Why These Are Optional

### Current Design: Function Calling Only

The current implementation achieves the same functionality through Gemini's function calling:

✅ **Advantages**:
- User talks naturally to chatbot
- No need to learn API
- Intelligent context awareness
- Automatic data synthesis

❌ **If APIs needed**:
- Direct programmatic access
- Mobile/external app integration
- Custom dashboards
- Batch operations

### Recommendation

**Keep current design** unless you specifically need:

1. Mobile app that queries data directly
2. Custom dashboard with real-time updates
3. Integration with third-party tools
4. Programmatic batch operations

For normal chatbot usage, the function calling approach is superior.

---

## Frontend Integration Example

If REST endpoints are added, JavaScript could use them:

```javascript
// Get statistics and display in sidebar
async function updateStatistics() {
    const response = await fetch('/api/statistics/');
    const stats = await response.json();

    document.getElementById('total-messages').textContent = stats.total_messages;
    document.getElementById('total-sessions').textContent = stats.total_sessions;
    document.getElementById('most-active').textContent = stats.most_active_session;
}

// Search interface
document.getElementById('search-btn').addEventListener('click', async () => {
    const keyword = document.getElementById('search-input').value;
    const response = await fetch(`/api/chats/search/?keyword=${keyword}&limit=10`);
    const results = await response.json();
    displaySearchResults(results.results);
});
```

---

## Performance Considerations

### Current Function Calling
- Query latency: ~1-2 seconds (includes Gemini API roundtrip)
- Suitable for: Natural conversation, user-initiated queries
- Frequency: Typical conversation (few messages per minute)

### With REST APIs
- Query latency: ~200-500ms (direct database)
- Suitable for: Dashboard updates, real-time monitoring
- Frequency: Can handle many requests per second

### Recommendation
- Keep function calling for chatbot interaction
- Add REST APIs only if dashboard/monitoring needed

---

## Security Notes

All endpoints would include:

✅ `@login_required` decorator
✅ User data filtering by `request.user`
✅ No cross-user data access
✅ Proper error handling
✅ Rate limiting (if needed)

---

## Conclusion

REST APIs are **not currently needed** for the Django Data Integration feature.

The function calling approach is elegant, user-friendly, and sufficient.

**Consider REST APIs only for Phase 2-3** when additional features (tasks, calendar) might benefit from programmatic access.

---

*Documentation Date: November 27, 2025*
