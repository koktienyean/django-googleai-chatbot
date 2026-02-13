# Plan: Feature Expansion (2025-11-27)

**Status**: PARTIALLY COMPLETED — reference only

## Summary

5-phase plan to add data integration, task management, calendar, notifications, and analytics on top of the initial chatbot.

| Phase | Feature | Status |
|-------|---------|--------|
| Phase 1 | Django Data Integration (Gemini function calling) | Completed |
| Phase 2 | Task Management System | Completed |
| Phase 3 | Calendar Integration (FullCalendar.js) | Completed |
| Phase 4 | Notifications & Recurring Tasks | Partial — models/API exist, no email sending or scheduler |
| Phase 5 | Advanced Analytics & Reporting | Partial — models/API exist, no scheduled job to populate data |
| Future | MCP Integration | Skipped — deemed too complex for current scope |

## Files in this plan

- **NEXT_FEATURES_ANALYSIS.md** — Analysis of 4 proposed features with difficulty/value rankings
- **PHASE_3_CALENDAR_PLAN.md** — Detailed calendar integration implementation plan
- **PHASE_4_5_IMPLEMENTATION_PLAN.md** — Combined plan for notifications, recurring tasks, and analytics

## What's still missing from this plan

1. **No email delivery** — Notification model stores records but SMTP sending was never wired up
2. **No scheduler** — RecurringTaskTemplate never auto-creates Task instances (needs celery/django-q/cron)
3. **No analytics cron** — TaskAnalytics/ChatAnalytics models exist but no job populates daily snapshots
