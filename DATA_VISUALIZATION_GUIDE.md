# Data Visualization & Task Management Improvements

## Overview

This document describes two major improvements made to the Django Google AI Chatbot:

1. **Calendar and Table Visualization** - Automatic rendering of JSON task/event data in chat
2. **Task Selection UI** - Intelligent task selection when modifying tasks without specifying IDs

---

## Feature 1: Calendar & Table Visualization

### Purpose
When the Gemini AI returns task or event data in JSON format, it automatically renders in two beautiful formats:
- **Calendar View** - Visual month-based calendar grid
- **Table View** - Structured tabular format

### How It Works

#### Automatic Detection
The system detects calendar/event data by looking for:
- JSON objects with `events` array
- JSON objects with `tasks` array
- Arrays containing objects with `due_date` fields

#### Calendar View Features
- 📅 Month-based grid layout matching current date
- Color-coded events by priority:
  - 🔴 Urgent (red)
  - 🟠 High (orange)
  - 🔵 Medium (blue)
  - 🟢 Low (green)
- Shows up to 3 events per day
- "+X more" indicator for additional events
- Highlights today's date with special styling
- Grayed out days from other months

#### Table View Features
- 📊 Auto-detected columns from JSON data
- Formatted badge elements for priority and status
- Readable date formatting
- Hover effects for better interactivity
- Responsive design

#### Toggle Buttons
Users can switch between views using buttons at the top:
- **📅 Calendar** - Switch to calendar view
- **📊 Table** - Switch to table view

### Implementation Details

**Location**: [templates/chatbot.html](templates/chatbot.html)

**CSS Classes Added**:
- `.data-calendar` - Calendar container
- `.calendar-grid` - Grid layout container
- `.calendar-day` - Individual day cell
- `.calendar-event` - Event badge
- `.data-table` - Table container
- `.view-toggle` - Toggle buttons container
- `.badge-*` - Priority/status badges (urgent, high, medium, low, pending, in_progress, completed, cancelled)

**JavaScript Functions Added**:
- `isCalendarData(data)` - Detects if data is calendar/event data
- `renderCalendarView(data)` - Renders month calendar grid
- `renderTableView(data)` - Renders data table
- `processDataVisualization(responseHtml)` - Main processor that finds JSON and renders it
- `updateVisualization(container)` - Handles view switching

### Example Usage

**User asks**:
```
Show me my tasks for December 2025 in JSON format
```

**Gemini returns**:
```json
{
  "tasks": [
    {
      "id": 1,
      "title": "CK show scanning scanner process",
      "priority": "urgent",
      "status": "pending",
      "due_date": "2025-12-04"
    },
    {
      "id": 2,
      "title": "go pets world",
      "priority": "medium",
      "status": "pending",
      "due_date": "2025-12-05"
    }
  ]
}
```

**User sees**:
- Calendar view with events displayed on their due dates
- Toggle button to switch to table view
- Color-coded badges for priorities
- Full interactivity

### Styling
- Matches dark terminal theme
- Uses CSS variables for consistency: `--color-primary`, `--bg-primary`, etc.
- Responsive design for mobile devices
- Smooth transitions and hover effects

---

## Feature 2: Task Selection UI

### Purpose
When a user wants to modify a task (update, edit, remove, change status, etc.) but doesn't specify which task, the system now shows a visual list of available tasks instead of asking "What is the task ID?"

### How It Works

#### Rule-Based Behavior
1. **User provides task name/partial match** → Search and match directly
   ```
   User: "update go pets world with due date tomorrow"
   System: Finds matching task and asks for confirmation
   ```

2. **User doesn't specify task** → Show task list for selection
   ```
   User: "change the due date as tomorrow"
   System: [Shows list of pending tasks]
   User: Selects which task to update
   ```

3. **User provides task ID** → Process directly (no change)
   ```
   User: "update task 2 with status completed"
   System: Updates task 2 directly
   ```

### Implementation Details

**Location**: [.claude/](./claude/)

**Files Created**:
- `.claude/commands/manage-task.md` - Task management guidelines
- `.claude/claude.json` - Configuration and rules

**Configuration Rules**:
```json
{
  "rules": [
    {
      "trigger": "user asks to update/edit/remove/change task without providing task ID",
      "action": "Show list of available tasks using TodoWrite, ask user to select one"
    },
    {
      "trigger": "user provides task name or partial match",
      "action": "Search for matching task and proceed directly without asking for ID"
    }
  ]
}
```

### Supported Operations
The following operations trigger task selection:
- `update` - Modify task properties
- `edit` - Modify task content
- `remove` - Delete task
- `delete` - Delete task
- `change status` - Update status
- `change due date` - Update due date
- `change priority` - Update priority

### User Experience Flow

**Before** (Old Experience):
```
User: "update the go pets world with due date tomorrow"
Claude: "I need a task ID first. What is the task ID of 'go pets world'?"
User: [Has to find and provide ID]
```

**After** (New Experience):
```
User: "update the go pets world with due date tomorrow"
Claude: [Shows matching task with ID]
        "Found task: 'go pets world'. Updating due date to tomorrow..."
        ✓ Task updated successfully
```

**Or if ambiguous**:
```
User: "change due date as tomorrow"
Claude: [Shows list of all pending tasks with IDs]
        "Which task would you like to update?"
        1. CK show scanning scanner process
        2. go pets world
User: "Task 2"
Claude: ✓ Updated 'go pets world' due date to tomorrow
```

### Benefits
- ✅ Better UX - No need to search for task IDs
- ✅ Visual feedback - See all available tasks
- ✅ Smart matching - Recognizes task names
- ✅ Fewer back-and-forth messages
- ✅ More intuitive interaction

---

## Integration Points

### Chat Interface
- Data visualization automatically triggers when JSON is detected
- No manual configuration needed
- Works with existing chat flow

### Task Management System
- Task selection UI applies to all task modification operations
- Integrates with Claude's TodoWrite tool
- Works with task names, IDs, and partial matches

---

## File Changes Summary

### Modified Files
1. **templates/chatbot.html**
   - Added CSS classes for calendar and table visualization
   - Added JavaScript functions for data processing and rendering
   - Integrated visualization processor into message handling

### New Files
1. **.claude/commands/manage-task.md** - Task management guidelines
2. **.claude/claude.json** - Configuration file
3. **DATA_VISUALIZATION_GUIDE.md** - This documentation

---

## Testing Checklist

- [ ] Calendar renders correctly with multiple events
- [ ] Table view displays all columns properly
- [ ] Toggle buttons switch between views smoothly
- [ ] Priority badges show correct colors
- [ ] Task selection shows available tasks
- [ ] Task selection works with partial matches
- [ ] Mobile responsive layout works
- [ ] All dates format correctly

---

## Future Enhancements

Potential improvements for future versions:
1. Custom date range selection in calendar view
2. Filtering in table view (by priority, status, etc.)
3. Drag-and-drop events on calendar to reschedule
4. Event creation directly from calendar
5. Recurring task visualization
6. Analytics dashboard integration

---

## Support

For questions or issues with these features, refer to:
- Calendar/Table Visualization: See `processDataVisualization()` in chatbot.html
- Task Selection: See `.claude/claude.json` rules
- Task Management: See `CLAUDE.md` for project context

---

**Last Updated**: December 3, 2025
**Version**: 1.0
