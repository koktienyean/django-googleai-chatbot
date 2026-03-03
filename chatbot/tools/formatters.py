"""
Convert API-agnostic tool definitions to the format required by each AI backend.
"""
from .definitions import get_tool_definitions


def format_tools_for_claude(user=None):
    """Convert tool definitions to Anthropic Claude format.

    Claude format:
    {
        "name": "tool_name",
        "description": "...",
        "input_schema": {
            "type": "object",
            "properties": {...},
            "required": [...]
        }
    }
    """
    if not user:
        return []

    tools = get_tool_definitions()
    claude_tools = []

    for tool in tools:
        properties = {}
        for param_name, param_def in tool["parameters"].items():
            prop = {"type": param_def["type"]}
            if "enum" in param_def:
                prop["enum"] = param_def["enum"]
            if "default" in param_def:
                prop["default"] = param_def["default"]
            if "description" in param_def:
                prop["description"] = param_def["description"]
            properties[param_name] = prop

        claude_tools.append({
            "name": tool["name"],
            "description": tool["description"],
            "input_schema": {
                "type": "object",
                "properties": properties,
                "required": tool["required"],
            }
        })

    return claude_tools


def format_tools_for_gemini(user=None):
    """Convert tool definitions to Google Gemini format.

    Gemini uses Python callable functions with type hints and docstrings.
    Returns a list of wrapper functions that bind the user context.
    """
    if not user:
        return None

    from chatbot.views import (
        search_my_chats, get_chat_statistics, get_recent_conversations,
        search_by_date_range, get_session_summary, list_my_sessions,
        create_task, list_my_tasks, get_task_details,
        update_task_status, update_task_priority, delete_task,
        get_pending_tasks, get_task_summary,
        create_recurring_task_tool, list_recurring_tasks_tool,
        skip_recurring_instance_tool,
        get_notification_summary_tool, set_notification_preference_tool,
        get_productivity_metrics_tool, get_task_insights_tool,
        generate_weekly_report_tool,
    )

    # Chat history tools
    def search_chats_tool(keyword: str, limit: int = 5):
        """Search through user's chat history by keyword"""
        return search_my_chats(user, keyword, limit)

    def get_stats_tool():
        """Get user's chat usage statistics"""
        return get_chat_statistics(user)

    def get_recent_tool(limit: int = 5):
        """Get user's recent conversations"""
        return get_recent_conversations(user, limit)

    def search_dates_tool(start_date: str, end_date: str):
        """Search chats within a date range (YYYY-MM-DD format)"""
        return search_by_date_range(user, start_date, end_date)

    def get_session_tool(session_id: int):
        """Get detailed summary of a specific chat session"""
        return get_session_summary(user, session_id)

    def list_sessions_tool(limit: int = 10):
        """List all user's chat sessions"""
        return list_my_sessions(user, limit)

    # Task management tools
    def create_task_tool(title: str, description: str = '', priority: str = 'medium', due_date_str: str = None):
        """Create a new task for the user. Priority must be one of: low, medium, high, urgent. Due date format: YYYY-MM-DD or natural language like 'tomorrow' or 'next Friday'"""
        return create_task(user, title, description, priority, due_date_str)

    def list_tasks_tool(status: str = 'all', limit: int = 10):
        """List user's tasks. Status can be: all, pending, in_progress, completed, or cancelled"""
        return list_my_tasks(user, status, limit)

    def get_task_details_tool(task_id: int):
        """Get complete details of a specific task by task ID"""
        return get_task_details(user, task_id)

    def update_task_status_tool(task_id: int, status: str):
        """Change task status. Status must be one of: pending, in_progress, completed, or cancelled"""
        return update_task_status(user, task_id, status)

    def update_task_priority_tool(task_id: int, priority: str):
        """Change task priority. Priority must be one of: low, medium, high, or urgent"""
        return update_task_priority(user, task_id, priority)

    def delete_task_tool(task_id: int):
        """Delete a task permanently from the system"""
        return delete_task(user, task_id)

    def get_pending_tasks_tool(limit: int = 5):
        """Get user's urgent and high priority pending tasks that need attention"""
        return get_pending_tasks(user, limit)

    def get_task_summary_tool():
        """Get summary counts of all tasks grouped by status"""
        return get_task_summary(user)

    # Recurring tasks (Phase 4)
    def create_recurring_task_tool_wrapper(title: str, description: str = '', priority: str = 'medium', frequency: str = 'weekly', start_date_str: str = None, end_date_str: str = None):
        """Create a recurring task. Frequency: daily, weekly, biweekly, monthly, quarterly, yearly"""
        return create_recurring_task_tool(user, title, description, priority, frequency, start_date_str, end_date_str)

    def list_recurring_tasks_tool_wrapper():
        """List all recurring task templates"""
        return list_recurring_tasks_tool(user)

    def skip_recurring_instance_tool_wrapper(template_id: int):
        """Skip next instance of a recurring task"""
        return skip_recurring_instance_tool(user, template_id)

    # Notifications (Phase 4)
    def get_notification_summary_tool_wrapper():
        """Get notification summary and recent notifications"""
        return get_notification_summary_tool(user)

    def set_notification_preference_tool_wrapper(preference_type: str, enabled: bool):
        """Update notification preferences. Types: deadline_reminder, overdue_reminder, daily_digest"""
        return set_notification_preference_tool(user, preference_type, enabled)

    # Analytics (Phase 5)
    def get_productivity_metrics_tool_wrapper():
        """Get productivity metrics: completion rate, task counts, average completion time"""
        return get_productivity_metrics_tool(user)

    def get_task_insights_tool_wrapper():
        """Get AI-powered insights about task performance and productivity"""
        return get_task_insights_tool(user)

    def generate_weekly_report_tool_wrapper():
        """Generate a weekly productivity report"""
        return generate_weekly_report_tool(user)

    # Data Query & Reporting (Phase C)
    def query_data_tool(data_type: str, filters: dict = None, aggregation: str = 'none', order_by: str = '-created_at', limit: int = 20):
        """Query Django data with flexible filters. Supports: tasks, chats, sessions, task_analytics, chat_analytics. Aggregation options: none, count, group_by_status, group_by_priority, group_by_date, trend. Dates can be YYYY-MM-DD or: today, yesterday, this_week, last_week, this_month, last_30_days"""
        from chatbot.tools.query_engine import execute_query
        return execute_query(user, data_type, filters=filters, aggregation=aggregation, order_by=order_by, limit=limit)

    def generate_report_tool(report_type: str, data_type: str, time_range: str = 'last_30_days', format: str = 'markdown'):
        """Generate a formatted report. report_type: summary, detailed, trend, comparison. data_type: tasks, chats, sessions. time_range: today, this_week, this_month, last_30_days, last_7_days. format: markdown, table, chart_data"""
        from chatbot.tools.report_builder import ReportBuilder
        builder = ReportBuilder(user)
        return builder.generate_report(report_type, data_type, time_range, format)

    # Skill & Flow Engine (Phase D)
    def list_skills_tool(skill_type: str = 'all'):
        """List all available skills. Filter by type: all, query, transform, generate, action, condition"""
        from chatbot.tools.executors import execute_tool
        return execute_tool(user, 'list_skills_tool', {'skill_type': skill_type})

    def create_skill_tool(name: str, skill_type: str, config: dict, description: str = ''):
        """Create a new reusable AI skill. skill_type: query, transform, generate, action, condition"""
        from chatbot.tools.executors import execute_tool
        return execute_tool(user, 'create_skill_tool', {'name': name, 'skill_type': skill_type, 'config': config, 'description': description})

    def list_flows_tool():
        """List all user's flows (sequential skill pipelines)"""
        from chatbot.tools.executors import execute_tool
        return execute_tool(user, 'list_flows_tool', {})

    def create_flow_tool(name: str, steps: list, description: str = ''):
        """Create a sequential flow from existing skills. Steps: [{skill_name, input_mapping, config_override}]"""
        from chatbot.tools.executors import execute_tool
        return execute_tool(user, 'create_flow_tool', {'name': name, 'steps': steps, 'description': description})

    def run_flow_tool(flow_name: str, context: dict = None):
        """Execute a named flow and return step-by-step results"""
        from chatbot.tools.executors import execute_tool
        return execute_tool(user, 'run_flow_tool', {'flow_name': flow_name, 'context': context or {}})

    def submit_skill_feedback_tool(execution_log_id: int, rating: int, comment: str = '', expected_output: str = ''):
        """Submit feedback on a skill execution result. Rating 1-5 (1=poor, 5=excellent)"""
        from chatbot.tools.executors import execute_tool
        return execute_tool(user, 'submit_skill_feedback_tool', {'execution_log_id': execution_log_id, 'rating': rating, 'comment': comment, 'expected_output': expected_output})

    def get_skill_stats_tool(skill_name: str):
        """Get execution stats and feedback summary for a skill"""
        from chatbot.tools.executors import execute_tool
        return execute_tool(user, 'get_skill_stats_tool', {'skill_name': skill_name})

    def improve_skill_tool(skill_name: str):
        """Analyze negative feedback and suggest improvements for a skill"""
        from chatbot.tools.executors import execute_tool
        return execute_tool(user, 'improve_skill_tool', {'skill_name': skill_name})

    return [
        # Chat history
        search_chats_tool, get_stats_tool, get_recent_tool,
        search_dates_tool, get_session_tool, list_sessions_tool,
        # Task management
        create_task_tool, list_tasks_tool, get_task_details_tool,
        update_task_status_tool, update_task_priority_tool, delete_task_tool,
        get_pending_tasks_tool, get_task_summary_tool,
        # Recurring tasks
        create_recurring_task_tool_wrapper, list_recurring_tasks_tool_wrapper,
        skip_recurring_instance_tool_wrapper,
        # Notifications
        get_notification_summary_tool_wrapper, set_notification_preference_tool_wrapper,
        # Analytics
        get_productivity_metrics_tool_wrapper, get_task_insights_tool_wrapper,
        generate_weekly_report_tool_wrapper,
        # Data Query & Reporting
        query_data_tool, generate_report_tool,
        # Skill & Flow Engine
        list_skills_tool, create_skill_tool, list_flows_tool, create_flow_tool,
        run_flow_tool, submit_skill_feedback_tool, get_skill_stats_tool, improve_skill_tool,
    ]


def format_tools_for_ollama(user=None):
    """Convert tool definitions to Ollama (OpenAI-compatible) format.

    Ollama format:
    {
        "type": "function",
        "function": {
            "name": "tool_name",
            "description": "...",
            "parameters": {
                "type": "object",
                "properties": {...},
                "required": [...]
            }
        }
    }
    """
    if not user:
        return []

    tools = get_tool_definitions()
    ollama_tools = []

    for tool in tools:
        properties = {}
        for param_name, param_def in tool["parameters"].items():
            prop = {"type": param_def["type"]}
            if "enum" in param_def:
                prop["enum"] = param_def["enum"]
            if "description" in param_def:
                prop["description"] = param_def["description"]
            properties[param_name] = prop

        ollama_tools.append({
            "type": "function",
            "function": {
                "name": tool["name"],
                "description": tool["description"],
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": tool["required"],
                }
            }
        })

    return ollama_tools
