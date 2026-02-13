# Phase 3: Calendar Integration - Testing Guide

**Date**: December 1, 2025
**Status**: Ready for Testing
**Test Environment**: Django Development Server

---

## Pre-Test Checklist

✅ Calendar API endpoints created
✅ Calendar template built
✅ Drag-and-drop functionality implemented
✅ Event modal created
✅ Color coding implemented
✅ Filters configured
✅ Date parsing fixed and tested
✅ Database ready with test tasks

---

## Test Setup

### 1. Start Django Server

```bash
python manage.py runserver
```

Server runs on: http://localhost:8000

### 2. Access Calendar

Navigate to: **http://localhost:8000/calendar/**

Login if needed with test credentials.

---

## Test Cases

### Test 1: Page Load & Basic Display
**Expected Result**: Calendar page loads with:
- Dark terminal theme matching chatbot UI
- Sidebar with filters and legend
- FullCalendar.js calendar view
- Tasks displayed as events

**Steps**:
1. Navigate to http://localhost:8000/calendar/
2. Verify page loads without errors
3. Check browser console for JavaScript errors
4. Verify dark theme is applied

**Verification**:
- ✅ Page loads
- ✅ No console errors
- ✅ CSS styling applied correctly
- ✅ Calendar grid visible

---

### Test 2: Event Display
**Expected Result**: All tasks with due dates appear as events

**Steps**:
1. Look at calendar
2. Check for 4 events (based on test data):
   - "Fix critical bug" (Red - Urgent) - Dec 2
   - "Implement new API" (Blue - Medium or Orange - High) - Dec 13 (rescheduled)
   - "Code review" (Blue - Medium) - Dec 4
   - "Update documentation" (Green - Low, Overdue) - Nov 29

**Verification**:
- ✅ All 4 tasks appear as events
- ✅ Events are color-coded by priority
- ✅ Event titles are readable
- ✅ Overdue event has different styling

---

### Test 3: Color Coding
**Expected Result**: Events colored correctly by priority

**Colors to Verify**:
- 🔴 Urgent = Red (#F44336)
- 🟠 High = Orange (#FF9800)
- 🔵 Medium = Blue (#2196F3)
- 🟢 Low = Green (#4CAF50)

**Steps**:
1. View calendar
2. Compare event colors to legend (shown in sidebar)
3. Verify color legend matches actual events

**Verification**:
- ✅ "Fix critical bug" is Red (Urgent)
- ✅ Color legend matches actual colors
- ✅ Multiple colors visible on calendar

---

### Test 4: Sidebar Filters
**Expected Result**: Filters work and update calendar

**Steps**:

**Priority Filter Test**:
1. Open priority dropdown
2. Select "Urgent"
3. Verify only red "Fix critical bug" event shows
4. Select "All Priorities"
5. Verify all events return

**Status Filter Test**:
1. Open status dropdown
2. Select "In Progress"
3. Verify only "Implement new API" event shows (it's in_progress)
4. Select "All Status"
5. Verify all events return

**Combined Filter Test**:
1. Set Priority = "Medium"
2. Set Status = "Pending"
3. Verify only "Code review" event shows
4. Clear both filters
5. Verify all 4 events return

**Verification**:
- ✅ Priority filter works
- ✅ Status filter works
- ✅ Combined filters work
- ✅ Calendar refreshes on filter change

---

### Test 5: Click Event → View Modal
**Expected Result**: Clicking event opens modal with task details

**Steps**:
1. Click on "Fix critical bug" event (red)
2. Modal should appear with:
   - Title: "Fix critical bug"
   - Priority: "Urgent" (red badge)
   - Status: "Pending" (amber badge)
   - Due Date: December 2, 2025
   - Days Left: X days
   - Description: "Crash on login page"
3. Verify all fields are visible
4. Verify close button (×) works

**Modal Elements to Verify**:
- ✅ Modal title shows event name
- ✅ Priority badge is colored correctly
- ✅ Status badge is colored correctly
- ✅ Due date is formatted properly
- ✅ Days calculation is correct
- ✅ Description displays
- ✅ Modal has "Mark Done" button
- ✅ Modal has "Delete" button
- ✅ Close button (×) works

---

### Test 6: Drag-and-Drop Reschedule
**Expected Result**: Dragging event updates due date in database

**Steps**:
1. View calendar in month view
2. Click and drag "Code review" event to a different date (e.g., Dec 10)
3. Release mouse
4. Toast notification should appear: "Task rescheduled to..."
5. Event should move to new date
6. Refresh page - event should stay at new date

**Verification**:
- ✅ Event can be dragged
- ✅ Event position updates visually
- ✅ Toast notification appears
- ✅ Database updated (check with Django admin or query)
- ✅ Date persists after page refresh

**Database Verification**:
```bash
python manage.py shell
>>> from chatbot.models import Task
>>> Task.objects.get(title='Code review').due_date
```

---

### Test 7: Mark Task as Completed
**Expected Result**: Complete task from modal

**Steps**:
1. Click on event to open modal
2. Click "Mark Done" button
3. Task status should change to "Completed"
4. Toast should appear: "Task marked as completed"
5. Modal should close
6. Calendar should refresh
7. Event should be removed from view (if "Completed" is filtered out)

**Verification**:
- ✅ Task marked as completed
- ✅ Toast notification appears
- ✅ Modal closes automatically
- ✅ Calendar updates
- ✅ Completed task no longer visible (depending on filters)

---

### Test 8: Delete Task
**Expected Result**: Delete task from modal

**Steps**:
1. Click on event to open modal
2. Click "Delete" button
3. Confirmation dialog appears
4. Click "OK" to confirm
5. Toast should appear: "Task deleted"
6. Modal should close
7. Event should disappear from calendar
8. Calendar refreshes

**Verification**:
- ✅ Confirmation dialog appears
- ✅ Toast notification appears on delete
- ✅ Modal closes
- ✅ Event removed from calendar
- ✅ Task is gone after page refresh

---

### Test 9: View Switching
**Expected Result**: Can switch between different calendar views

**Steps**:
1. Note current view (Month)
2. Click "Week" button in toolbar
3. View changes to week grid
4. Click "Day" (or similar) button
5. View changes to day view
6. Click "List" (or "Agenda") button
7. View shows events in list format
8. Return to "Month" view

**Verification**:
- ✅ Month view works
- ✅ Week view works
- ✅ Day view works (if available)
- ✅ List view works
- ✅ Can switch between views smoothly

---

### Test 10: Statistics Display
**Expected Result**: Task counts shown correctly

**Elements to Check**:
- Total tasks count (shown in header)
- Overdue tasks count

**Steps**:
1. View calendar header
2. Check "X tasks" statistic
3. Verify count matches visible events
4. Check "X overdue" statistic
5. Verify count matches overdue events (as of testing date)

**Verification**:
- ✅ Total tasks count is visible
- ✅ Total tasks count is accurate
- ✅ Overdue count is visible
- ✅ Overdue count is accurate

---

### Test 11: Responsive Design
**Expected Result**: Calendar works on mobile

**Steps**:
1. Open browser DevTools (F12)
2. Toggle device toolbar (Ctrl+Shift+M)
3. Set to mobile view (iPhone 12)
4. Navigate to calendar
5. Verify layout adapts:
   - Sidebar should be horizontal or hidden
   - Calendar should fill screen width
   - Events should be readable
   - Modal should fit on screen
6. Test on different screen sizes (tablet, desktop)

**Verification**:
- ✅ Mobile layout works
- ✅ Calendar readable on small screens
- ✅ Filters accessible
- ✅ Modal fits on mobile

---

### Test 12: Error Handling
**Expected Result**: Errors handled gracefully

**Steps**:

**Test Missing Due Date**:
1. Create task without due date (via chat)
2. Event should not appear on calendar
3. No errors in console

**Test Network Error**:
1. Open DevTools Network tab
2. Right-click on /api/tasks/calendar/ request
3. Throttle to "Offline"
4. Try to interact with calendar
5. Should show error toast
6. Re-enable network

**Verification**:
- ✅ No due date = no event (correct)
- ✅ Network errors shown to user
- ✅ No JavaScript crashes
- ✅ App recovers from errors

---

### Test 13: Integration with Chat
**Expected Result**: Tasks created via chat appear on calendar

**Steps**:
1. Go to chat (/chat/X)
2. Say: "Create task: Prepare presentation with high priority due Dec 20"
3. Task created via chat
4. Go to calendar (/calendar/)
5. Verify new task appears as event on Dec 20
6. Verify it's colored orange (high priority)

**Verification**:
- ✅ Chat-created tasks appear on calendar
- ✅ Due date is correct
- ✅ Priority color is correct
- ✅ Task details are visible in modal

---

### Test 14: Performance
**Expected Result**: Calendar loads quickly, no lag

**Measurements to Take**:
1. Time to load calendar page (should be < 2 seconds)
2. Time to toggle filter (should be < 500ms)
3. Time to drag event (should be smooth, no jank)
4. Check DevTools Performance tab for issues

**Verification**:
- ✅ Page load < 2 seconds
- ✅ Filters responsive (< 500ms)
- ✅ Drag-drop smooth and responsive
- ✅ No memory leaks in console

---

## Quick Test Checklist

```
Core Functionality:
☐ Calendar page loads
☐ Events display correctly
☐ Color coding works
☐ Can view event details
☐ Can drag events
☐ Can filter tasks
☐ Can delete tasks
☐ Can mark complete

API Integration:
☐ GET /api/tasks/calendar/ returns events
☐ POST /api/tasks/<id>/update_due_date/ updates date
☐ Filter parameters work
☐ Database updates persist

UX/UI:
☐ Dark theme applied
☐ Responsive on mobile
☐ Smooth animations
☐ Clear status badges
☐ Toast notifications work

Errors:
☐ No console errors
☐ Handles missing dates
☐ Handles network errors
☐ Validates input
```

---

## Test Data Summary

Your calendar has been populated with test data:

| Task | Priority | Status | Due Date | Color |
|------|----------|--------|----------|-------|
| Fix critical bug | Urgent | Pending | Dec 2 | 🔴 Red |
| Implement new API | High | In Progress | Dec 13 | 🟠 Orange |
| Code review | Medium | Pending | Dec 4 | 🔵 Blue |
| Update documentation | Low | Pending | Nov 29 | 🟢 Green (Overdue) |

---

## Known Limitations (Phase 3)

- No all-day events yet (events show 1-hour duration)
- No recurring tasks
- No event editing from modal (use chat to update)
- No calendar export
- No external calendar sync
- No real-time updates (requires page refresh)

---

## Reporting Issues

If you find issues during testing:

1. **Note the steps to reproduce**
2. **Check browser console** (F12 > Console) for errors
3. **Check Django logs** for server errors
4. **Test in incognito mode** to rule out cache issues
5. **Try hard refresh** (Ctrl+Shift+R) to clear cache

---

## Success Criteria

Phase 3 testing is complete when:

- ✅ All 14 test cases pass
- ✅ No console errors
- ✅ No unhandled exceptions
- ✅ Calendar usable on desktop and mobile
- ✅ Drag-drop works smoothly
- ✅ Filters work correctly
- ✅ Modal displays proper information
- ✅ Performance is acceptable
- ✅ Chat integration works

---

## Post-Testing

Once all tests pass:

1. Create final summary document
2. Commit working code
3. Update README with calendar feature
4. Prepare for Phase 4 (optional) or production deployment

---

*Phase 3 Calendar Integration - Testing Guide*
*Comprehensive test cases for all features*
*Ready to validate production-ready calendar*
