# Phase 3: Calendar Integration - Implementation Plan

**Date**: December 1, 2025
**Status**: READY FOR IMPLEMENTATION
**Estimated Duration**: 2-3 weeks (can be done incrementally)

---

## Overview

Add a visual calendar view for task management using FullCalendar.js. Users can see their tasks on a calendar, drag to reschedule, and filter by priority/status.

---

## Phase 3 Features (In Order of Implementation)

### Feature 1: Calendar API Endpoint ✅ READY
**What**: Create `/api/tasks/calendar/` endpoint
**Why**: FullCalendar needs events in JSON format
**Implementation**:
```python
# In chatbot/views.py

@login_required
def api_tasks_calendar(request):
    """Return tasks as calendar events (iCal/JSON format)"""
    tasks = Task.objects.filter(user=request.user)

    events = []
    for task in tasks:
        if task.due_date:
            events.append({
                'id': task.id,
                'title': task.title,
                'start': task.due_date.isoformat(),
                'end': (task.due_date + timedelta(hours=1)).isoformat(),
                'color': task.get_priority_color(),
                'extendedProps': {
                    'priority': task.priority,
                    'status': task.status,
                    'description': task.description,
                    'isOverdue': task.is_overdue(),
                }
            })

    return JsonResponse({'events': events})
```

**URL**: Add to `chatbot/urls.py`
```python
path('api/tasks/calendar/', views.api_tasks_calendar, name='calendar'),
```

---

### Feature 2: Calendar Template ✅ READY
**What**: Create `calendar.html` with FullCalendar.js
**Why**: Display tasks visually
**Components**:
1. FullCalendar.js library (CDN)
2. Calendar container
3. Filters (priority, status)
4. Legend (color codes)
5. Integration with chat sidebar

**Structure**:
```html
<!-- templates/calendar.html -->
{% extends 'base.html' %}

{% block styles %}
<link href='https://cdn.jsdelivr.net/npm/fullcalendar@6.1.10/index.global.min.css' rel='stylesheet' />
<style>
  .calendar-container { ... }
  .event-urgent { background-color: #F44336; }
  .event-high { background-color: #FF9800; }
  .event-medium { background-color: #2196F3; }
  .event-low { background-color: #4CAF50; }
</style>
{% endblock %}

{% block content %}
<div class="calendar-wrapper">
  <!-- Filters -->
  <div class="calendar-filters">
    <label>Priority: <select id="priority-filter">...</select></label>
    <label>Status: <select id="status-filter">...</select></label>
  </div>

  <!-- Calendar -->
  <div id='calendar'></div>
</div>
{% endblock %}

{% block scripts %}
<script src='https://cdn.jsdelivr.net/npm/fullcalendar@6.1.10/index.global.min.js'></script>
<script>
  document.addEventListener('DOMContentLoaded', function() {
    var calendarEl = document.getElementById('calendar');
    var calendar = new FullCalendar.Calendar(calendarEl, {
      initialView: 'dayGridMonth',
      headerToolbar: {
        left: 'prev,next today',
        center: 'title',
        right: 'dayGridMonth,timeGridWeek,listWeek'
      },
      events: '/api/tasks/calendar/',
      editable: true,
      eventDrop: handleEventDrop,
      eventClick: handleEventClick,
    });
    calendar.render();
  });
</script>
{% endblock %}
```

---

### Feature 3: Drag-and-Drop ✅ READY
**What**: Update task due date when dragging on calendar
**Why**: Quick deadline adjustment
**Implementation**:
```python
# In chatbot/views.py

@login_required
def api_task_update_due_date(request, task_id):
    """Update task due date via drag-drop"""
    task = get_object_or_404(Task, id=task_id, user=request.user)

    new_date = request.POST.get('due_date')
    if new_date:
        task.due_date = datetime.fromisoformat(new_date)
        task.save()

    return JsonResponse({
        'success': True,
        'task_id': task.id,
        'new_due_date': task.due_date.isoformat()
    })
```

**JavaScript Handler**:
```javascript
function handleEventDrop(info) {
  var taskId = info.event.id;
  var newDate = info.event.start;

  fetch(`/api/tasks/${taskId}/update_due_date/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
      'X-CSRFToken': getCookie('csrftoken')
    },
    body: 'due_date=' + newDate.toISOString()
  })
  .then(response => response.json())
  .then(data => {
    if (!data.success) {
      info.revert(); // Revert if error
    }
  });
}
```

---

### Feature 4: Event Detail Modal ✅ READY
**What**: Show task details when clicking calendar event
**Why**: View/edit full task information
**Implementation**:
```javascript
function handleEventClick(info) {
  var event = info.event;

  // Create modal content
  var modal = `
    <div class="modal">
      <h3>${event.title}</h3>
      <p><strong>Priority:</strong> ${event.extendedProps.priority}</p>
      <p><strong>Status:</strong> ${event.extendedProps.status}</p>
      <p><strong>Description:</strong> ${event.extendedProps.description}</p>
      <p><strong>Due Date:</strong> ${event.start}</p>
      <button onclick="editTask(${event.id})">Edit</button>
      <button onclick="completeTask(${event.id})">Mark Done</button>
      <button onclick="deleteTask(${event.id})">Delete</button>
    </div>
  `;

  showModal(modal);
}
```

---

### Feature 5: Priority Color Coding ✅ READY
**What**: Calendar events colored by priority
**Why**: Visual task management
**Mapping**:
- 🔴 Urgent: #F44336 (Red)
- 🟠 High: #FF9800 (Orange)
- 🔵 Medium: #2196F3 (Blue)
- 🟢 Low: #4CAF50 (Green)

**Implementation**: Already available via `task.get_priority_color()`

---

### Feature 6: Filter & Search ✅ READY
**What**: Filter calendar by priority, status
**Why**: Focus on important tasks
**Dropdowns**:
```html
<select id="priority-filter">
  <option value="">All Priorities</option>
  <option value="urgent">Urgent</option>
  <option value="high">High</option>
  <option value="medium">Medium</option>
  <option value="low">Low</option>
</select>

<select id="status-filter">
  <option value="">All Status</option>
  <option value="pending">Pending</option>
  <option value="in_progress">In Progress</option>
  <option value="completed">Completed</option>
  <option value="cancelled">Cancelled</option>
</select>
```

**JavaScript Handler**:
```javascript
document.getElementById('priority-filter').addEventListener('change', function() {
  var priority = this.value;
  var status = document.getElementById('status-filter').value;

  // Fetch filtered events
  var url = `/api/tasks/calendar/?priority=${priority}&status=${status}`;
  calendar.refetchEvents(); // Reload with new URL
});
```

---

### Feature 7: Calendar Views ✅ READY
**FullCalendar provides**:
- Month view (default)
- Week view (time grid)
- Day view (time grid)
- Agenda/List view

**User can toggle between views** using toolbar buttons

---

### Feature 8: Multiple Calendar Types (Optional)
**Could add**:
- Heatmap view (color intensity = task count)
- Kanban view (cards by status)
- Timeline view (Gantt-style)
- Agenda view (list with dates)

---

## Implementation Order (Recommended)

### Week 1: Core Functionality
1. ✅ Create API endpoint (`api_tasks_calendar/`)
2. ✅ Create calendar template
3. ✅ FullCalendar.js integration
4. ✅ Test basic display

### Week 2: Interactivity
5. ✅ Drag-and-drop functionality
6. ✅ Event click handlers
7. ✅ Modal for event details
8. ✅ Test interactions

### Week 3: Polish
9. ✅ Priority color coding (refined)
10. ✅ Filter/search dropdown
11. ✅ Responsive design
12. ✅ Performance optimization
13. ✅ Full end-to-end testing

---

## Files to Modify/Create

### Create
```
templates/calendar.html                    (NEW - 200+ lines)
chatbot/static/js/calendar.js             (NEW - 300+ lines)
chatbot/static/css/calendar.css           (NEW - 150+ lines)
```

### Modify
```
chatbot/views.py                          (ADD 50+ lines)
  - api_tasks_calendar()
  - api_task_update_due_date()

chatbot/urls.py                           (ADD 2 lines)
  - path('api/tasks/calendar/', ...)
  - path('api/tasks/<id>/update_due_date/', ...)

templates/base.html                       (ADD 1 line)
  - Link to calendar page from sidebar
```

---

## Database Changes Required

✅ **NONE** - Task model already has `due_date` field

The existing indexes are perfect:
```
Index(fields=['user', '-due_date'])  ← Optimized for calendar queries
```

---

## API Endpoints (Summary)

### Get Calendar Events
```
GET /api/tasks/calendar/
Parameters: ?priority=high&status=pending (optional filters)
Returns: { events: [...] }
```

### Update Task Due Date
```
POST /api/tasks/<id>/update_due_date/
Body: due_date=2025-12-25T10:30:00
Returns: { success: true, task_id: X, new_due_date: ... }
```

### Existing Endpoints (Reuse)
```
GET /api/tasks/list/ - Get tasks
POST /api/tasks/create/ - Create task
POST /api/tasks/<id>/update_status/ - Change status
POST /api/tasks/<id>/update_priority/ - Change priority
```

---

## CSS Variables to Use

From existing `chatbot.html`:
```css
--color-primary: #00d9ff      (Cyan)
--color-secondary: #ff006e    (Magenta)
--color-accent: #06d6a0       (Green)
--bg-primary: #0f1419         (Dark Navy)
--bg-secondary: #1a1f2e       (Slightly lighter)
--text-primary: #e0e0e0       (Light Gray)
--text-secondary: #999        (Gray)
--border-primary: #2d3142     (Dark border)
--transition-fast: 0.2s ease  (Animation speed)
```

---

## Testing Plan

### Unit Tests
- [ ] API endpoint returns correct event format
- [ ] Drag-drop updates database
- [ ] Filters work correctly
- [ ] Modal displays correct data

### Integration Tests
- [ ] Create task → appears on calendar
- [ ] Drag task → due date updates
- [ ] Filter → calendar refreshes
- [ ] Click event → modal shows

### User Tests
- [ ] Month view displays all tasks
- [ ] Can switch between views
- [ ] Drag-drop is smooth
- [ ] Mobile responsive
- [ ] Colors match priority levels
- [ ] Filters work with Gemini tasks

---

## Estimated Lines of Code

```
API Endpoints (views.py):        ~50 lines
Template (calendar.html):         ~200 lines
JavaScript (calendar.js):         ~300 lines
CSS (calendar.css):               ~150 lines
URL configuration (urls.py):      ~5 lines
────────────────────────────────
Total New Code:                   ~705 lines
```

---

## Potential Challenges & Solutions

### Challenge 1: Time Zone Issues
- **Problem**: Browser sends local time, server stores UTC
- **Solution**: Convert to UTC on server, convert back to local on client
- **Code**:
```python
from django.utils import timezone
due_date = timezone.make_aware(datetime.fromisoformat(new_date))
```

### Challenge 2: Performance with Many Tasks
- **Problem**: 100+ tasks = slow calendar
- **Solution**: Implement pagination/lazy loading
- **FullCalendar Feature**: `lazySegs` option

### Challenge 3: Drag-Drop Conflicts
- **Problem**: Touch devices don't drag well
- **Solution**: Also add quick-edit button in modal
- **Fallback**: Form to enter new date manually

### Challenge 4: Real-time Updates
- **Problem**: Another user changes task, calendar doesn't update
- **Solution**: Implement polling or WebSocket (optional for Phase 3)
- **Basic Version**: Refresh button to reload events

---

## Phase 3 Milestones

✅ **Milestone 1**: API + Basic Calendar Display (Day 1-2)
✅ **Milestone 2**: Drag-Drop + Modal (Day 3-4)
✅ **Milestone 3**: Filters + Color Coding (Day 5)
✅ **Milestone 4**: Testing + Polish (Day 6-7)
✅ **Milestone 5**: Documentation + Deployment (Day 8)

---

## Success Criteria

Phase 3 is complete when:
- ✅ Calendar displays all user's tasks with due dates
- ✅ Can drag tasks to reschedule
- ✅ Can click tasks to view/edit details
- ✅ Tasks color-coded by priority
- ✅ Can filter by priority and status
- ✅ Works on mobile devices
- ✅ All tests passing
- ✅ No performance issues (< 500ms load)
- ✅ Fully documented

---

## Optional Phase 3+ Features

### Phase 3.1 - Advanced Calendar
- Recurring tasks (show multiple instances)
- Multi-day events
- All-day events (no specific time)
- Event serialization (copy to clipboard)

### Phase 3.2 - Integrations
- Export calendar (iCal format)
- Import from Google Calendar
- Sync with calendar app
- Webhook notifications

### Phase 3.3 - Analytics
- Heatmap showing task density
- Completion rate chart
- Missed deadlines analysis
- Productivity trends

---

## Ready to Start?

This plan is **implementation-ready**. All components are specified, code examples are provided, and the database is already optimized.

**Next Steps**:
1. Review this plan
2. Confirm you want to proceed
3. I'll implement Feature 1 (API endpoint) first
4. Then build the calendar template
5. Add interactivity
6. Run comprehensive tests

Say "proceed" when ready! 🚀

---

*Phase 3: Calendar Integration - Implementation Plan*
*Ready for development*
*Estimated completion: 2-3 weeks*
