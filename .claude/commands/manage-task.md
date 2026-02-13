# Task Management with Selection

When a user wants to update, edit, remove, or change the status of a task but doesn't provide a specific task ID, you should:

1. **List all pending tasks** immediately using TodoWrite to show available options
2. **Ask the user to select** which task they want to modify
3. **Do NOT ask "what is the task ID"** - instead provide a visual list
4. Once selected, proceed with the requested action

## Command Examples

When user says:
- "update a task" → Show task list for selection
- "change the due date" → Show task list for selection
- "remove a task" → Show task list for selection
- "update status" → Show task list for selection
- "edit go pets world" → Since task name is given, search for it and modify directly

## Implementation

Always use TodoWrite to display current tasks before asking user to select. This gives context and makes it easy for the user to identify which task they want to modify.
