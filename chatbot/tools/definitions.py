"""
API-agnostic tool definitions for all AI backends.
Each tool is defined once here, then converted to Claude/Gemini/Ollama format by formatters.py.
"""

SYSTEM_INSTRUCTION = """You are a helpful AI assistant with access to tools for managing tasks, querying data, generating reports, and running skill-based workflows.

When the user asks you to:
- Create a task: Use create_task_tool directly without asking for confirmation
- List/show tasks: Use list_tasks_tool or get_task_summary_tool directly
- Update task status/priority: Use the respective update tools directly
- Search chats: Use search_chats_tool directly
- Get statistics: Use get_stats_tool directly
- Query data (count, filter, group): Use query_data_tool with appropriate filters and aggregation
- Generate a report or summary: Use generate_report_tool with the right report_type and data_type
- List skills: Use list_skills_tool
- Create a skill: Use create_skill_tool with name, type, and config
- List flows: Use list_flows_tool
- Create a flow: Use create_flow_tool with name and steps (each step references a skill)
- Run a flow: Use run_flow_tool with the flow name
- Give feedback on a skill result: Use submit_skill_feedback_tool
- Check skill performance: Use get_skill_stats_tool
- Improve a skill: Use improve_skill_tool to analyze feedback and suggest fixes

IMPORTANT: Call the appropriate tool IMMEDIATELY when the user requests these actions. Do not ask for confirmation - just call the function and show the result.

For task priorities, accept any reasonable input and normalize to: low, medium, high, or urgent
For task status, accept any reasonable input and normalize to: pending, in_progress, completed, or cancelled

For data queries, use query_data_tool for raw lookups and generate_report_tool for formatted reports with insights.

When the user asks about external database data (production, sales, machines, planning, packing, etc.):
- Query external database: First call get_db_schema_tool to learn the schema, optionally call get_sample_data_tool to see real data patterns, then call execute_sql_tool with a SELECT query
- Always use PostgreSQL syntax with double-quoted identifiers for table/column names (e.g., "Machine_Name", "PTS_PlanningHeader")
- Never use INSERT/UPDATE/DELETE - only SELECT queries are allowed
- Present query results in a clear formatted table or summary

Always call the tool first, then provide a friendly response about what was done."""


def get_tool_definitions():
    """Return all tool definitions in a common schema format.

    Each tool has:
      - name: unique identifier
      - description: what it does
      - parameters: dict of parameter definitions
      - required: list of required parameter names
    """
    return [
        # ========== CHAT HISTORY TOOLS ==========
        {
            "name": "search_chats_tool",
            "description": "Search through user's chat history by keyword",
            "parameters": {
                "keyword": {"type": "string", "description": "Search keyword"},
                "limit": {"type": "integer", "default": 5, "description": "Max results"},
            },
            "required": ["keyword"],
        },
        {
            "name": "get_stats_tool",
            "description": "Get user's chat usage statistics",
            "parameters": {},
            "required": [],
        },
        {
            "name": "get_recent_tool",
            "description": "Get user's recent conversations",
            "parameters": {
                "limit": {"type": "integer", "default": 5, "description": "Max results"},
            },
            "required": [],
        },
        {
            "name": "search_dates_tool",
            "description": "Search chats within a date range (YYYY-MM-DD format)",
            "parameters": {
                "start_date": {"type": "string", "description": "Start date YYYY-MM-DD"},
                "end_date": {"type": "string", "description": "End date YYYY-MM-DD"},
            },
            "required": ["start_date", "end_date"],
        },
        {
            "name": "get_session_tool",
            "description": "Get detailed summary of a specific chat session",
            "parameters": {
                "session_id": {"type": "integer", "description": "Session ID"},
            },
            "required": ["session_id"],
        },
        {
            "name": "list_sessions_tool",
            "description": "List all user's chat sessions",
            "parameters": {
                "limit": {"type": "integer", "default": 10, "description": "Max results"},
            },
            "required": [],
        },

        # ========== TASK MANAGEMENT TOOLS ==========
        {
            "name": "create_task_tool",
            "description": "Create a new task for the user",
            "parameters": {
                "title": {"type": "string", "description": "Task title"},
                "description": {"type": "string", "default": "", "description": "Task description"},
                "priority": {
                    "type": "string",
                    "enum": ["low", "medium", "high", "urgent"],
                    "default": "medium",
                    "description": "Task priority",
                },
                "due_date_str": {"type": "string", "description": "Due date string"},
            },
            "required": ["title"],
        },
        {
            "name": "list_tasks_tool",
            "description": "List user's tasks",
            "parameters": {
                "status": {
                    "type": "string",
                    "enum": ["all", "pending", "in_progress", "completed", "cancelled"],
                    "default": "all",
                    "description": "Filter by status",
                },
                "limit": {"type": "integer", "default": 10, "description": "Max results"},
            },
            "required": [],
        },
        {
            "name": "get_task_details_tool",
            "description": "Get complete details of a specific task by task ID",
            "parameters": {
                "task_id": {"type": "integer", "description": "Task ID"},
            },
            "required": ["task_id"],
        },
        {
            "name": "update_task_status_tool",
            "description": "Change task status",
            "parameters": {
                "task_id": {"type": "integer", "description": "Task ID"},
                "status": {
                    "type": "string",
                    "enum": ["pending", "in_progress", "completed", "cancelled"],
                    "description": "New status",
                },
            },
            "required": ["task_id", "status"],
        },
        {
            "name": "update_task_priority_tool",
            "description": "Change task priority",
            "parameters": {
                "task_id": {"type": "integer", "description": "Task ID"},
                "priority": {
                    "type": "string",
                    "enum": ["low", "medium", "high", "urgent"],
                    "description": "New priority",
                },
            },
            "required": ["task_id", "priority"],
        },
        {
            "name": "delete_task_tool",
            "description": "Delete a task permanently from the system",
            "parameters": {
                "task_id": {"type": "integer", "description": "Task ID"},
            },
            "required": ["task_id"],
        },
        {
            "name": "get_pending_tasks_tool",
            "description": "Get user's urgent and high priority pending tasks",
            "parameters": {
                "limit": {"type": "integer", "default": 5, "description": "Max results"},
            },
            "required": [],
        },
        {
            "name": "get_task_summary_tool",
            "description": "Get summary counts of all tasks grouped by status",
            "parameters": {},
            "required": [],
        },

        # ========== RECURRING TASKS (Phase 4) ==========
        {
            "name": "create_recurring_task_tool",
            "description": "Create a recurring task",
            "parameters": {
                "title": {"type": "string", "description": "Task title"},
                "description": {"type": "string", "default": "", "description": "Task description"},
                "priority": {
                    "type": "string",
                    "enum": ["low", "medium", "high", "urgent"],
                    "default": "medium",
                },
                "frequency": {
                    "type": "string",
                    "enum": ["daily", "weekly", "biweekly", "monthly", "quarterly", "yearly"],
                    "default": "weekly",
                },
            },
            "required": ["title", "frequency"],
        },
        {
            "name": "list_recurring_tasks_tool",
            "description": "List all recurring task templates",
            "parameters": {},
            "required": [],
        },
        {
            "name": "skip_recurring_instance_tool",
            "description": "Skip next instance of a recurring task",
            "parameters": {
                "template_id": {"type": "integer", "description": "Template ID"},
            },
            "required": ["template_id"],
        },

        # ========== NOTIFICATIONS (Phase 4) ==========
        {
            "name": "get_notification_summary_tool",
            "description": "Get notification summary and recent notifications",
            "parameters": {},
            "required": [],
        },
        {
            "name": "set_notification_preference_tool",
            "description": "Update notification preferences",
            "parameters": {
                "preference_type": {
                    "type": "string",
                    "enum": ["deadline_reminder", "overdue_reminder", "daily_digest"],
                    "description": "Which preference to change",
                },
                "enabled": {"type": "boolean", "description": "Enable or disable"},
            },
            "required": ["preference_type", "enabled"],
        },

        # ========== ANALYTICS (Phase 5) ==========
        {
            "name": "get_productivity_metrics_tool",
            "description": "Get productivity metrics",
            "parameters": {},
            "required": [],
        },
        {
            "name": "get_task_insights_tool",
            "description": "Get AI-powered insights about task performance",
            "parameters": {},
            "required": [],
        },
        {
            "name": "generate_weekly_report_tool",
            "description": "Generate a weekly productivity report",
            "parameters": {},
            "required": [],
        },

        # ========== DATA QUERY & REPORTING (Phase C) ==========
        {
            "name": "query_data_tool",
            "description": "Query Django data with flexible filters. Supports: tasks, chats, sessions, task_analytics, chat_analytics. Use this for any data lookup, counting, grouping, or trend analysis.",
            "parameters": {
                "data_type": {
                    "type": "string",
                    "enum": ["tasks", "chats", "sessions", "task_analytics", "chat_analytics"],
                    "description": "Which data to query",
                },
                "filters": {
                    "type": "object",
                    "description": "Filter criteria: status, priority, date_from, date_to, keyword, model. Dates can be YYYY-MM-DD or: today, yesterday, this_week, last_week, this_month, last_30_days",
                },
                "aggregation": {
                    "type": "string",
                    "enum": ["none", "count", "group_by_status", "group_by_priority", "group_by_date", "trend"],
                    "default": "none",
                    "description": "How to aggregate results",
                },
                "order_by": {
                    "type": "string",
                    "default": "-created_at",
                    "description": "Field to order by (prefix with - for descending)",
                },
                "limit": {
                    "type": "integer",
                    "default": 20,
                    "description": "Max results (1-100)",
                },
            },
            "required": ["data_type"],
        },
        {
            "name": "generate_report_tool",
            "description": "Generate a formatted report from data. Returns markdown tables, metrics, and chart data. Use this when the user asks for a report, summary, or analysis.",
            "parameters": {
                "report_type": {
                    "type": "string",
                    "enum": ["summary", "detailed", "trend", "comparison"],
                    "description": "Type of report to generate",
                },
                "data_type": {
                    "type": "string",
                    "enum": ["tasks", "chats", "sessions", "task_analytics", "chat_analytics"],
                    "description": "Which data to report on",
                },
                "time_range": {
                    "type": "string",
                    "enum": ["today", "this_week", "this_month", "last_30_days", "last_7_days"],
                    "default": "last_30_days",
                    "description": "Time period for the report",
                },
                "format": {
                    "type": "string",
                    "enum": ["markdown", "table", "chart_data"],
                    "default": "markdown",
                    "description": "Output format",
                },
            },
            "required": ["report_type", "data_type"],
        },

        # ========== SKILL & FLOW ENGINE (Phase D) ==========
        {
            "name": "list_skills_tool",
            "description": "List all available skills (system + user-created)",
            "parameters": {
                "skill_type": {
                    "type": "string",
                    "enum": ["all", "query", "transform", "generate", "action", "condition"],
                    "default": "all",
                    "description": "Filter by skill type",
                },
            },
            "required": [],
        },
        {
            "name": "create_skill_tool",
            "description": "Create a new reusable AI skill",
            "parameters": {
                "name": {"type": "string", "description": "Unique skill name"},
                "description": {"type": "string", "description": "What the skill does"},
                "skill_type": {
                    "type": "string",
                    "enum": ["query", "transform", "generate", "action", "condition"],
                    "description": "Type of skill",
                },
                "config": {"type": "object", "description": "Skill configuration (prompt_template, data_type, etc.)"},
            },
            "required": ["name", "skill_type", "config"],
        },
        {
            "name": "list_flows_tool",
            "description": "List all user's flows (sequential skill pipelines)",
            "parameters": {},
            "required": [],
        },
        {
            "name": "create_flow_tool",
            "description": "Create a sequential flow from existing skills. Each step runs in order, passing output to the next.",
            "parameters": {
                "name": {"type": "string", "description": "Flow name"},
                "description": {"type": "string", "description": "What the flow does"},
                "steps": {
                    "type": "array",
                    "description": "List of steps: [{skill_name, input_mapping, config_override, condition}]",
                },
            },
            "required": ["name", "steps"],
        },
        {
            "name": "run_flow_tool",
            "description": "Execute a named flow. Returns step-by-step results.",
            "parameters": {
                "flow_name": {"type": "string", "description": "Name of the flow to run"},
                "context": {"type": "object", "description": "Initial context/input for the flow"},
            },
            "required": ["flow_name"],
        },
        {
            "name": "submit_skill_feedback_tool",
            "description": "Submit feedback on a skill execution result (rating 1-5 + comment)",
            "parameters": {
                "execution_log_id": {"type": "integer", "description": "ID of the execution log entry"},
                "rating": {"type": "integer", "description": "Rating 1-5 (1=poor, 5=excellent)"},
                "comment": {"type": "string", "description": "What was wrong or could be better"},
                "expected_output": {"type": "string", "description": "What the output should have been"},
            },
            "required": ["execution_log_id", "rating"],
        },
        {
            "name": "get_skill_stats_tool",
            "description": "Get execution stats and feedback summary for a skill",
            "parameters": {
                "skill_name": {"type": "string", "description": "Name of the skill"},
            },
            "required": ["skill_name"],
        },
        {
            "name": "improve_skill_tool",
            "description": "Analyze negative feedback and suggest improvements for a skill",
            "parameters": {
                "skill_name": {"type": "string", "description": "Name of the skill to improve"},
            },
            "required": ["skill_name"],
        },
        # ========== EXTERNAL DB QUERY (SIG_Chart) ==========
        {
            "name": "get_db_schema_tool",
            "description": "Get full database schema: all tables, columns with descriptions, join relationships, and module groupings. Call this first before writing any SQL query. Returns PostgreSQL database structure.",
            "parameters": {},
            "required": [],
        },
        {
            "name": "get_sample_data_tool",
            "description": "Get top N sample rows from a database table to understand data patterns and actual values. Use this to inspect a table before writing queries.",
            "parameters": {
                "table": {"type": "string", "description": "Table name (e.g., PTS_PlanningHeader, SetupPartNo)"},
                "limit": {"type": "integer", "default": 5, "description": "Number of sample rows (max 20)"},
            },
            "required": ["table"],
        },
        {
            "name": "execute_sql_tool",
            "description": "Execute a raw SELECT SQL query against the PostgreSQL database. Only SELECT queries allowed. Use double quotes for table/column names. Max 1000 rows, 10s timeout. Always call get_db_schema_tool first to learn the schema.",
            "parameters": {
                "sql": {"type": "string", "description": "SELECT SQL query (PostgreSQL syntax, double-quote identifiers)"},
                "limit": {"type": "integer", "default": 100, "description": "Max rows to return (max 1000)"},
            },
            "required": ["sql"],
        },
    ]
