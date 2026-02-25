# Django Gemini Chatbot - Project Status

**Last reviewed**: February 2026

---

## What's Built (Actually in the codebase)

### Core Chat System - DONE
- Multi-session chat with Google Gemini AI (2.0 Flash / 1.5 Flash)
- Async message processing via background thread + polling
- Markdown rendering (backend python-markdown + frontend marked.js)
- Session create/rename/delete from sidebar
- Per-session model configuration

### Authentication - DONE
- Custom login page (cyan theme, glass morphism)
- Custom register page (magenta theme, password validation)
- Django built-in auth with CSRF protection

### Task Management (Phase 2) - DONE
- Full CRUD via Gemini function calling (chat-driven)
- Priority levels: low / medium / high / urgent
- Status tracking: pending / in_progress / completed
- Due dates with overdue detection

### Calendar Integration (Phase 3) - DONE
- FullCalendar.js visualization at `/calendar/`
- API endpoint returns tasks as calendar events
- Drag-to-reschedule endpoint exists (`api_task_update_due_date`)
- Color-coded by priority

### Notifications & Recurring Tasks (Phase 4) - PARTIALLY DONE
- **Models exist**: Notification, NotificationPreference, RecurringTaskTemplate, RecurringTaskInstance
- **Gemini tools exist**: create/list/skip recurring tasks, notification summary, preference setting
- **API endpoints exist**: list notifications, mark-read, list recurring tasks
- **NOT built**: Actual email sending (no SMTP integration)
- **NOT built**: Scheduled job to create recurring task instances or check deadlines

### Analytics (Phase 5) - PARTIALLY DONE
- **Models exist**: TaskAnalytics, ChatAnalytics (daily snapshots)
- **Gemini tools exist**: productivity metrics, task insights, weekly report
- **API endpoints exist**: metrics, insights, weekly-report
- **NOT built**: Scheduled job to populate daily analytics snapshots

### Admin Interface - DONE
- All 9 models have custom admin classes
- Color-coded badges, linked fields, filters, search

---

## What's NOT Done

| Gap | Impact | Effort to fix |
|-----|--------|---------------|
| No email sending for notifications | Notifications are stored but never delivered | Medium - need SMTP config + sending logic |
| No scheduler for recurring tasks | RecurringTaskTemplate never auto-creates Task instances | Medium - need celery/django-q/cron job |
| No scheduler for analytics snapshots | TaskAnalytics/ChatAnalytics tables stay empty unless manually filled | Low - simple management command + cron |
| No automated test suite | `python manage.py test` has no test files | Medium - models and views need test coverage |
| `dateutil` not in requirements.txt | `create_task` imports it but it's not listed as a dependency | Trivial - add `python-dateutil` to requirements.txt |
| Settings page UI limited | Settings template exists but may not cover notification prefs | Low |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Framework | Django 4.2.3 |
| AI | google-generativeai (Gemini 2.0 Flash) |
| Database | SQLite (9 models, 15 indexes) |
| Async | Python threading + queue (not Celery) |
| Frontend | Django templates, vanilla JS, Bootstrap |
| Calendar | FullCalendar.js (CDN) |
| Markdown | marked.js (client) + python-markdown (server) |

---

## Database Models (9 total)

1. **ChatSession** - conversation containers per user
2. **Chat** - individual message/response pairs
3. **Task** - user tasks with priority/status/due_date
4. **Notification** - notification records
5. **NotificationPreference** - per-user notification settings
6. **RecurringTaskTemplate** - recurring task definitions
7. **RecurringTaskInstance** - tracks generated instances
8. **TaskAnalytics** - daily task statistics
9. **ChatAnalytics** - daily chat activity

---

## API Endpoints (28 total)

- **Auth**: login, register, logout (3)
- **Chat UI**: home, session view, settings (3)
- **Session API**: list, create, detail, update, delete, send-async (6)
- **Models API**: list-models, save-settings (2)
- **Async**: check-response (1)
- **Calendar**: tasks-calendar, update-due-date, calendar-view (3)
- **Notifications**: list, mark-read (2)
- **Recurring**: list (1)
- **Analytics**: metrics, insights, weekly-report (3)
- **Gemini tools**: 22 function-calling tools bound internally (not HTTP endpoints)

---

## File Structure

```
chatbot/
  models.py          # 9 models
  views.py           # All views + Gemini tool functions
  urls.py            # 28+ URL patterns
  admin.py           # Custom admin for all models
  message_queue.py   # Async message processor
  migrations/        # 5 migrations (0001-0005)

templates/
  base.html, login.html, register.html
  chatbot.html, calendar.html, settings.html

django_chatbot/
  settings.py, urls.py, wsgi.py
```

---

## Suggested Next Steps (pick one)

1. **Fix the gaps** - Add the missing scheduler + email sending to make Phases 4-5 fully functional
2. **Add tests** - Write Django TestCase classes for models and views
3. **Deploy** - The core chat + task + calendar features work as-is for a demo
4. **MCP Integration** - Originally planned as a future phase (see plans/NEXT_FEATURES_ANALYSIS.md)

---

## Documentation Index

| Folder | Contents |
|--------|----------|
| [docs/](docs/) | Guides, references, testing docs (16 files) |
| [docs/status/](docs/status/) | Phase completion summaries, archived status reports (19 files) |
| [plans/](plans/) | Date-prefixed plan folders with status READMEs |
| [plans/2025-11-25-initial-enhancement/](plans/2025-11-25-initial-enhancement/) | Original 6-phase plan (completed) |
| [plans/2025-11-27-feature-expansion/](plans/2025-11-27-feature-expansion/) | 5-phase feature plan (partially completed) |
| CLAUDE.md | Project instructions for Claude Code |
