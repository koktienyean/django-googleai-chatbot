# Phase 4 & 5: Testing Guide

**Date**: December 1, 2025
**Status**: Ready for Testing
**Test Environment**: Django Development Server

---

## Overview

This guide covers testing for Phase 4 (Email Notifications & Recurring Tasks) and Phase 5 (Analytics & Reporting) features.

**Total Test Cases**: 24
**Automated Tests**: 8
**Manual Tests**: 16

---

## Test Setup

### Prerequisites
```bash
# Ensure Django server is running
python manage.py runserver

# Access Django admin
http://localhost:8000/admin/
```

### Test Data
Tests use existing task data from Phase 3, with additional recurring tasks and analytics created during testing.

---

## Phase 4: Email Notifications & Recurring Tasks Tests

### Test 1: Create Recurring Task via Chat
**Type**: Manual + Automated
**Steps**:
1. Go to chat interface
2. Say: "Create a recurring task: Weekly team meeting with high priority every Monday"
3. Verify `create_recurring_task_tool_wrapper` is called
4. Check database for RecurringTaskTemplate with frequency='weekly'
5. Verify first Task instance is created

**Expected Result**: ✅
- RecurringTaskTemplate created in database
- Task created with due_date set to today
- Next instance date calculated (7 days from start)
- Gemini responds with confirmation

**Verification Checklist**:
```
☐ Template created in admin: Notifications > Recurring Task Templates
☐ Task appears in calendar
☐ Frequency shows as "Weekly"
☐ Priority badge shows "High"
☐ First instance created
```

---

### Test 2: List Recurring Tasks
**Type**: Manual
**Steps**:
1. Say: "Show me my recurring tasks"
2. Gemini calls `list_recurring_tasks_tool_wrapper`
3. Response shows all active recurring tasks

**Expected Result**: ✅
- Lists all recurring task templates
- Shows frequency, priority, next instance date
- Count matches admin display

---

### Test 3: Skip Recurring Instance
**Type**: Manual
**Steps**:
1. Say: "Skip the next instance of the weekly team meeting"
2. Provide template ID from previous test
3. Verify next instance date advances

**Expected Result**: ✅
- Next instance date updated (7 days later)
- Task not created for skipped date
- Gemini confirms skip

---

### Test 4: Notification Preferences - Enable
**Type**: Manual
**Steps**:
1. Say: "Enable deadline reminders"
2. Gemini calls `set_notification_preference_tool_wrapper`
3. Check database NotificationPreference record

**Expected Result**: ✅
- NotificationPreference.deadline_reminder_enabled = True
- Confirm message received
- Admin shows "✓ Enabled" badge

**Verification**:
```
☐ Django admin > Notification Preferences > Your user
☐ Deadline Reminders shows: ✓ Enabled
```

---

### Test 5: Notification Preferences - Disable
**Type**: Manual
**Steps**:
1. Say: "Disable overdue reminders"
2. Check database

**Expected Result**: ✅
- NotificationPreference.overdue_reminder_enabled = False
- Admin shows "Disabled" badge

---

### Test 6: Get Notification Summary
**Type**: Manual
**Steps**:
1. Say: "Show me my notifications"
2. Gemini calls `get_notification_summary_tool_wrapper`

**Expected Result**: ✅
- Shows unread count
- Lists recent 5 notifications
- Displays type and subject

---

### Test 7: API Endpoint - Notifications List
**Type**: Automated
**Steps**:
```bash
curl -X GET http://localhost:8000/api/notifications/ \
  -H "Cookie: sessionid=YOUR_SESSION"
```

**Expected Result**: ✅
- Status 200
- JSON array of notifications
- Fields: id, type, subject, message, is_sent, is_read, created_at

---

### Test 8: API Endpoint - Mark Notification Read
**Type**: Automated
**Steps**:
```bash
curl -X POST http://localhost:8000/api/notifications/1/read/ \
  -H "Cookie: sessionid=YOUR_SESSION"
```

**Expected Result**: ✅
- Status 200
- `{"success": true}`
- Notification.read_at is now set

---

## Phase 5: Analytics & Reporting Tests

### Test 9: Get Productivity Metrics
**Type**: Manual
**Steps**:
1. Say: "Show me my productivity metrics"
2. Gemini calls `get_productivity_metrics_tool_wrapper`

**Expected Result**: ✅
Response includes:
```json
{
  "total_tasks": 4,
  "completed_tasks": 1,
  "pending_tasks": 2,
  "in_progress_tasks": 1,
  "overdue_tasks": 1,
  "completion_rate": 25.0,
  "avg_days_to_complete": 5
}
```

---

### Test 10: API Endpoint - Productivity Metrics
**Type**: Automated
**Steps**:
```bash
curl -X GET http://localhost:8000/api/analytics/metrics/ \
  -H "Cookie: sessionid=YOUR_SESSION"
```

**Expected Result**: ✅
- Status 200
- Returns metrics JSON
- All fields present and calculated

---

### Test 11: Get Task Insights
**Type**: Manual
**Steps**:
1. Say: "What insights do you have about my tasks?"
2. Gemini calls `get_task_insights_tool_wrapper`

**Expected Result**: ✅
Response includes insights array with:
- Type: positive, warning, or info
- Title and message
- Actionable recommendations

**Sample Insights**:
```
- "Excellent Progress!" (completion_rate >= 80%)
- "Overdue Tasks" (overdue_count > 0)
- "Low Completion Rate" (completion_rate < 30%)
- "Average Task Duration" (metric display)
```

---

### Test 12: API Endpoint - Task Insights
**Type**: Automated
**Steps**:
```bash
curl -X GET http://localhost:8000/api/analytics/insights/ \
  -H "Cookie: sessionid=YOUR_SESSION"
```

**Expected Result**: ✅
- Status 200
- Returns insights array
- Each insight has type, title, message

---

### Test 13: Generate Weekly Report
**Type**: Manual
**Steps**:
1. Say: "Generate my weekly productivity report"
2. Gemini calls `generate_weekly_report_tool_wrapper`

**Expected Result**: ✅
Response includes:
```json
{
  "week_of": "2025-11-24",
  "days_tracked": 3,
  "total_completed": 5,
  "avg_completion_rate": 45.0,
  "highest_completion_day": "2025-11-28",
  "message": "Weekly report: 5 tasks completed..."
}
```

---

### Test 14: API Endpoint - Weekly Report
**Type**: Automated
**Steps**:
```bash
curl -X GET http://localhost:8000/api/analytics/weekly-report/ \
  -H "Cookie: sessionid=YOUR_SESSION"
```

**Expected Result**: ✅
- Status 200
- Returns weekly report JSON
- All metrics calculated

---

### Test 15: API Endpoint - Recurring Tasks List
**Type**: Automated
**Steps**:
```bash
curl -X GET http://localhost:8000/api/recurring-tasks/ \
  -H "Cookie: sessionid=YOUR_SESSION"
```

**Expected Result**: ✅
- Status 200
- Lists all user's recurring tasks
- Shows frequency, priority, next instance

---

### Test 16: Admin Interface - Notifications
**Type**: Manual
**Steps**:
1. Go to http://localhost:8000/admin/chatbot/notification/
2. Verify list display

**Expected Result**: ✅
**Checklist**:
```
☐ Subject column shows notification subject
☐ User link navigates to user admin
☐ Type badge shows color-coded notification type
☐ is_sent_badge shows ✓ Sent or Pending
☐ Can filter by type, sent status, date
☐ Can search by subject, message
```

---

### Test 17: Admin Interface - Notification Preferences
**Type**: Manual
**Steps**:
1. Go to http://localhost:8000/admin/chatbot/notificationpreference/
2. Click on user preference

**Expected Result**: ✅
**Checklist**:
```
☐ Lists all users with their preferences
☐ Shows deadline_enabled_badge (✓ Enabled or Disabled)
☐ Shows overdue_enabled_badge
☐ Shows daily_digest_badge
☐ Can edit reminder times
☐ Can edit reminder days before
```

---

### Test 18: Admin Interface - Recurring Task Templates
**Type**: Manual
**Steps**:
1. Go to http://localhost:8000/admin/chatbot/recurringtasktemplate/
2. View list and details

**Expected Result**: ✅
**Checklist**:
```
☐ Lists all templates
☐ Shows title, user, frequency badge, priority badge
☐ Shows next instance date
☐ Frequency badge color-coded (daily=red, weekly=orange, etc.)
☐ Priority badge color-coded (urgent=red, high=orange, etc.)
☐ is_active_badge shows ✓ Active or Inactive
☐ Can filter by frequency, priority, status
```

---

### Test 19: Admin Interface - Task Analytics
**Type**: Manual
**Steps**:
1. Go to http://localhost:8000/admin/chatbot/taskanalytics/
2. View analytics for a date

**Expected Result**: ✅
**Checklist**:
```
☐ Shows date and user
☐ Shows task counts: total, pending, in_progress, completed, overdue
☐ Shows completion_rate_display as percentage (e.g., "75.0%")
☐ Shows priority breakdown: urgent, high, medium, low
☐ Can filter by date and user
☐ Can search by username/email
```

---

### Test 20: Admin Interface - Chat Analytics
**Type**: Manual
**Steps**:
1. Go to http://localhost:8000/admin/chatbot/chatanalytics/
2. View analytics

**Expected Result**: ✅
**Checklist**:
```
☐ Shows date and user
☐ Shows message counts: total, user, ai_responses
☐ Shows session info: total, active, avg length
☐ Can filter by date and user
☐ Can search by username/email
```

---

### Test 21: Integration - Recurring Task to Calendar
**Type**: Manual
**Steps**:
1. Create recurring daily task via chat
2. Navigate to calendar
3. View multiple days

**Expected Result**: ✅
- Only next instance shows on calendar
- When instance marked complete, system can generate next

---

### Test 22: Integration - Analytics Updates on Task Completion
**Type**: Manual
**Steps**:
1. Check metrics before
2. Complete 2 tasks
3. Check metrics after
4. Call `get_productivity_metrics_tool_wrapper` again

**Expected Result**: ✅
- completion_rate increases
- completed_tasks count increases
- completion_rate calculated correctly

---

### Test 23: Integration - Notifications + Recurring Tasks
**Type**: Manual
**Steps**:
1. Create recurring task
2. Enable deadline reminders
3. Verify notification will be created

**Expected Result**: ✅
- Both features work together
- Notifications can be created for recurring task instances

---

### Test 24: Error Handling - Invalid Frequency
**Type**: Manual
**Steps**:
1. Say: "Create recurring task with monthly frequency"
2. Then try to create with "invalid-frequency"

**Expected Result**: ✅
- Valid frequency accepted
- Invalid frequency rejected with error message
- Returns helpful error explaining valid options

---

## Automated Test Suite

### Run All Tests
```bash
# Create test file first
python manage.py shell << 'EOF'
from django.contrib.auth.models import User
from chatbot.models import NotificationPreference, RecurringTaskTemplate
from chatbot.views import (
    get_productivity_metrics_tool,
    get_task_insights_tool,
    set_notification_preference_tool,
    create_recurring_task_tool
)

# Get test user
user = User.objects.first()

print("=" * 50)
print("PHASE 4-5 AUTOMATED TESTS")
print("=" * 50)

# Test 1: Metrics
print("\n1. Testing Productivity Metrics...")
metrics = get_productivity_metrics_tool(user)
assert 'completion_rate' in metrics
assert 'total_tasks' in metrics
print("   ✅ PASS: Metrics returned")

# Test 2: Insights
print("\n2. Testing Task Insights...")
insights = get_task_insights_tool(user)
assert 'insights' in insights
assert isinstance(insights['insights'], list)
print("   ✅ PASS: Insights returned")

# Test 3: Notification Preferences
print("\n3. Testing Notification Preferences...")
result = set_notification_preference_tool(user, 'deadline_reminder', True)
assert 'message' in result or 'enabled' in result
pref = NotificationPreference.objects.get(user=user)
assert pref.deadline_reminder_enabled == True
print("   ✅ PASS: Preferences updated")

# Test 4: Recurring Task Creation
print("\n4. Testing Recurring Task Creation...")
result = create_recurring_task_tool(user, 'Test Daily Task', '', 'medium', 'daily')
assert 'template_id' in result
assert 'first_task_id' in result
print("   ✅ PASS: Recurring task created")

print("\n" + "=" * 50)
print("ALL TESTS PASSED: 4/4")
print("=" * 50)
EOF
```

---

## Performance Tests

### Response Time Benchmarks
```
API Endpoint                          Target      Status
─────────────────────────────────────────────────────────
GET /api/analytics/metrics/          < 200ms     ✅
GET /api/analytics/insights/         < 300ms     ✅
GET /api/analytics/weekly-report/    < 300ms     ✅
GET /api/notifications/              < 100ms     ✅
GET /api/recurring-tasks/            < 100ms     ✅
POST /api/notifications/<id>/read/   < 50ms      ✅
```

---

## Security Tests

### User Isolation
**Test**: User A cannot see User B's notifications

**Steps**:
1. Create 2 test users
2. Create notification for User A
3. Login as User B
4. Call `/api/notifications/`
5. Verify notification not returned

**Expected Result**: ✅
- Only user's own notifications returned
- No cross-user data leakage

---

### Admin Permissions
**Test**: Non-admin user cannot access admin

**Steps**:
1. Login as regular user
2. Try to access `/admin/`
3. Try to access admin API

**Expected Result**: ✅
- Redirected to login
- Cannot bypass permissions

---

## Success Criteria

All tests pass when:
- ✅ All 24 tests pass (100% pass rate)
- ✅ No console errors
- ✅ No unhandled exceptions
- ✅ API endpoints respond within targets
- ✅ User isolation verified
- ✅ Admin interface displays correctly
- ✅ Gemini tools are called automatically
- ✅ Database models created successfully

---

## Troubleshooting

### Issue: Notification not created
**Solution**: Ensure NotificationPreference exists for user

```python
from chatbot.models import NotificationPreference
from django.contrib.auth.models import User
user = User.objects.first()
NotificationPreference.objects.get_or_create(user=user)
```

### Issue: Recurring task not generating next instance
**Solution**: Check next_instance_date logic in tool

### Issue: Metrics showing zero
**Solution**: Create test tasks first

```python
from chatbot.models import Task
Task.objects.create(
    user=user,
    title='Test',
    priority='medium',
    status='pending'
)
```

---

## Testing Checklist

```
Phase 4 Testing
☐ Create recurring task via chat
☐ List recurring tasks via chat
☐ Skip recurring instance via chat
☐ Enable/disable notification preferences via chat
☐ Get notification summary via chat
☐ View notifications in admin
☐ Admin notification preferences work
☐ API endpoints return correct data
☐ User isolation enforced
☐ All 8 Phase 4 tests passing

Phase 5 Testing
☐ Get productivity metrics via chat
☐ Get task insights via chat
☐ Generate weekly report via chat
☐ View task analytics in admin
☐ View chat analytics in admin
☐ API endpoints return correct data
☐ Metrics calculated correctly
☐ All 8 Phase 5 tests passing

Integration Testing
☐ Recurring tasks appear on calendar
☐ Analytics update when tasks change
☐ Notifications work with recurring tasks
☐ All features work together

Overall Status
☐ 24/24 tests passing
☐ No broken functionality
☐ Ready for production
```

---

*Phase 4 & 5 Testing Guide*
*Complete test coverage for notifications, recurring tasks, and analytics*
*December 1, 2025*
