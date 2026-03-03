"""
System-provided skill definitions.
These are seeded into the database by the setup_builtin_skills management command.
"""

BUILTIN_SKILLS = [
    {
        "name": "query_tasks",
        "description": "Query tasks with flexible filters (status, priority, date range, keyword)",
        "skill_type": "query",
        "config": {
            "data_type": "tasks",
            "aggregation": "none",
        },
        "input_schema": {
            "filters": {"type": "object", "description": "Filter criteria"},
            "aggregation": {"type": "string", "default": "none"},
            "limit": {"type": "integer", "default": 20},
        },
        "output_schema": {"type": "object", "description": "Query results"},
    },
    {
        "name": "query_chats",
        "description": "Search chat history by keyword or date range",
        "skill_type": "query",
        "config": {
            "data_type": "chats",
            "aggregation": "none",
        },
        "input_schema": {
            "filters": {"type": "object"},
            "limit": {"type": "integer", "default": 20},
        },
        "output_schema": {"type": "object"},
    },
    {
        "name": "task_summary",
        "description": "Get task counts grouped by status",
        "skill_type": "query",
        "config": {
            "data_type": "tasks",
            "aggregation": "group_by_status",
        },
        "input_schema": {},
        "output_schema": {"type": "object"},
    },
    {
        "name": "summarize_text",
        "description": "Summarize given text using AI",
        "skill_type": "generate",
        "config": {
            "prompt_template": "Please summarize the following concisely:\n\n${text}",
        },
        "input_schema": {
            "text": {"type": "string", "description": "Text to summarize"},
        },
        "output_schema": {"type": "string"},
    },
    {
        "name": "classify_priority",
        "description": "Classify priority level from task description text",
        "skill_type": "generate",
        "config": {
            "prompt_template": "Given the following tasks, classify each by urgency (urgent/high/medium/low) and explain why:\n\n${text}",
        },
        "input_schema": {
            "text": {"type": "string"},
        },
        "output_schema": {"type": "string"},
    },
    {
        "name": "extract_dates",
        "description": "Extract dates and deadlines from text",
        "skill_type": "generate",
        "config": {
            "prompt_template": "Extract all dates, deadlines, and time references from this text. Return as a JSON list of {date, context}:\n\n${text}",
        },
        "input_schema": {
            "text": {"type": "string"},
        },
        "output_schema": {"type": "array"},
    },
    {
        "name": "create_task_skill",
        "description": "Create a new task from structured input",
        "skill_type": "action",
        "config": {
            "action_type": "create_task",
        },
        "input_schema": {
            "title": {"type": "string", "required": True},
            "description": {"type": "string"},
            "priority": {"type": "string", "default": "medium"},
        },
        "output_schema": {"type": "object"},
    },
    {
        "name": "update_task_skill",
        "description": "Update a task's status or priority",
        "skill_type": "action",
        "config": {
            "action_type": "update_task",
        },
        "input_schema": {
            "task_id": {"type": "integer", "required": True},
            "status": {"type": "string"},
            "priority": {"type": "string"},
        },
        "output_schema": {"type": "object"},
    },
    {
        "name": "check_count",
        "description": "Check if a count value meets a threshold condition",
        "skill_type": "condition",
        "config": {
            "field": "count",
            "operator": ">",
            "threshold": 0,
        },
        "input_schema": {
            "count": {"type": "integer"},
        },
        "output_schema": {"result": {"type": "boolean"}, "value": {"type": "integer"}},
    },
]
