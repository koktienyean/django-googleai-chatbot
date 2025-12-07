import os
from datetime import datetime, timedelta, date
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.core.cache import cache

from django.contrib import auth
from django.contrib.auth.models import User
from .models import (
    Chat, ChatSession, Task,
    Notification, NotificationPreference,
    RecurringTaskTemplate, RecurringTaskInstance,
    TaskAnalytics, ChatAnalytics
)
from .message_queue import message_processor

from django.utils import timezone
from django.contrib.auth.decorators import login_required
from dotenv import load_dotenv
load_dotenv()

import anthropic
import google.generativeai as genai

# Load environment variables from .env file
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
API_SECRET_KEY = os.getenv('API_SECRET_KEY')

# Initialize Anthropic client
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# Initialize Gemini (Generative AI)
if API_SECRET_KEY:
    genai.configure(api_key=API_SECRET_KEY)


def ask_ai(message, model='claude-3-5-sonnet-20241022', user=None):
    """Smart router that uses Claude API or Gemini API based on model parameter

    Claude models: claude-3-5-sonnet-20241022, claude-3-opus-20250219, etc.
    Gemini models: gemini-2.0-flash, gemini-1.5-flash, gemini-pro, etc.
    """
    # Determine which API to use based on model name
    if model.startswith('claude'):
        return ask_claude(message, model, user)
    elif model.startswith('gemini') or model.startswith('gpt'):
        return ask_gemini_api(message, model, user)
    else:
        # Default to Claude for unknown models
        return ask_claude(message, model, user)


def ask_claude(message, model='claude-3-5-sonnet-20241022', user=None):
    """Call Claude API and return response text

    Supports function calling to query user's Django data via:
    - search_my_chats(keyword, limit)
    - get_chat_statistics()
    - get_recent_conversations(limit)
    - search_by_date_range(start_date, end_date)
    - get_session_summary(session_id)
    - list_my_sessions(limit)
    """
    try:
        # Define tools that expose Django data to Claude
        tools = []
        if user:
            # Chat history tools
            tools.extend([
                {
                    "name": "search_chats_tool",
                    "description": "Search through user's chat history by keyword",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "keyword": {"type": "string"},
                            "limit": {"type": "integer", "default": 5}
                        },
                        "required": ["keyword"]
                    }
                },
                {
                    "name": "get_stats_tool",
                    "description": "Get user's chat usage statistics",
                    "input_schema": {
                        "type": "object",
                        "properties": {}
                    }
                },
                {
                    "name": "get_recent_tool",
                    "description": "Get user's recent conversations",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "limit": {"type": "integer", "default": 5}
                        }
                    }
                },
                {
                    "name": "search_dates_tool",
                    "description": "Search chats within a date range (YYYY-MM-DD format)",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "start_date": {"type": "string"},
                            "end_date": {"type": "string"}
                        },
                        "required": ["start_date", "end_date"]
                    }
                },
                {
                    "name": "get_session_tool",
                    "description": "Get detailed summary of a specific chat session",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "session_id": {"type": "integer"}
                        },
                        "required": ["session_id"]
                    }
                },
                {
                    "name": "list_sessions_tool",
                    "description": "List all user's chat sessions",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "limit": {"type": "integer", "default": 10}
                        }
                    }
                },
                # Task management tools
                {
                    "name": "create_task_tool",
                    "description": "Create a new task for the user",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "description": {"type": "string", "default": ""},
                            "priority": {"type": "string", "enum": ["low", "medium", "high", "urgent"], "default": "medium"},
                            "due_date_str": {"type": "string"}
                        },
                        "required": ["title"]
                    }
                },
                {
                    "name": "list_tasks_tool",
                    "description": "List user's tasks",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "status": {"type": "string", "enum": ["all", "pending", "in_progress", "completed", "cancelled"], "default": "all"},
                            "limit": {"type": "integer", "default": 10}
                        }
                    }
                },
                {
                    "name": "get_task_details_tool",
                    "description": "Get complete details of a specific task by task ID",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "task_id": {"type": "integer"}
                        },
                        "required": ["task_id"]
                    }
                },
                {
                    "name": "update_task_status_tool",
                    "description": "Change task status",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "task_id": {"type": "integer"},
                            "status": {"type": "string", "enum": ["pending", "in_progress", "completed", "cancelled"]}
                        },
                        "required": ["task_id", "status"]
                    }
                },
                {
                    "name": "update_task_priority_tool",
                    "description": "Change task priority",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "task_id": {"type": "integer"},
                            "priority": {"type": "string", "enum": ["low", "medium", "high", "urgent"]}
                        },
                        "required": ["task_id", "priority"]
                    }
                },
                {
                    "name": "delete_task_tool",
                    "description": "Delete a task permanently from the system",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "task_id": {"type": "integer"}
                        },
                        "required": ["task_id"]
                    }
                },
                {
                    "name": "get_pending_tasks_tool",
                    "description": "Get user's urgent and high priority pending tasks",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "limit": {"type": "integer", "default": 5}
                        }
                    }
                },
                {
                    "name": "get_task_summary_tool",
                    "description": "Get summary counts of all tasks grouped by status",
                    "input_schema": {
                        "type": "object",
                        "properties": {}
                    }
                },
                # Recurring tasks and notifications
                {
                    "name": "create_recurring_task_tool_wrapper",
                    "description": "Create a recurring task",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "description": {"type": "string", "default": ""},
                            "priority": {"type": "string", "enum": ["low", "medium", "high", "urgent"], "default": "medium"},
                            "frequency": {"type": "string", "enum": ["daily", "weekly", "biweekly", "monthly", "quarterly", "yearly"], "default": "weekly"}
                        },
                        "required": ["title", "frequency"]
                    }
                },
                {
                    "name": "list_recurring_tasks_tool_wrapper",
                    "description": "List all recurring task templates",
                    "input_schema": {
                        "type": "object",
                        "properties": {}
                    }
                },
                {
                    "name": "skip_recurring_instance_tool_wrapper",
                    "description": "Skip next instance of a recurring task",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "template_id": {"type": "integer"}
                        },
                        "required": ["template_id"]
                    }
                },
                {
                    "name": "get_notification_summary_tool_wrapper",
                    "description": "Get notification summary and recent notifications",
                    "input_schema": {
                        "type": "object",
                        "properties": {}
                    }
                },
                {
                    "name": "set_notification_preference_tool_wrapper",
                    "description": "Update notification preferences",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "preference_type": {"type": "string", "enum": ["deadline_reminder", "overdue_reminder", "daily_digest"]},
                            "enabled": {"type": "boolean"}
                        },
                        "required": ["preference_type", "enabled"]
                    }
                },
                # Analytics
                {
                    "name": "get_productivity_metrics_tool_wrapper",
                    "description": "Get productivity metrics",
                    "input_schema": {
                        "type": "object",
                        "properties": {}
                    }
                },
                {
                    "name": "get_task_insights_tool_wrapper",
                    "description": "Get AI-powered insights about task performance",
                    "input_schema": {
                        "type": "object",
                        "properties": {}
                    }
                },
                {
                    "name": "generate_weekly_report_tool_wrapper",
                    "description": "Generate a weekly productivity report",
                    "input_schema": {
                        "type": "object",
                        "properties": {}
                    }
                }
            ])

        system_instruction = """You are a helpful AI assistant with access to tools for managing tasks and querying chat history.

When the user asks you to:
- Create a task: Use create_task_tool directly without asking for confirmation
- List/show tasks: Use list_tasks_tool or get_task_summary_tool directly
- Update task status/priority: Use the respective update tools directly
- Search chats: Use search_chats_tool directly
- Get statistics: Use get_stats_tool directly

IMPORTANT: Call the appropriate tool IMMEDIATELY when the user requests these actions. Do not ask for confirmation - just call the function and show the result.

For task priorities, accept any reasonable input and normalize to: low, medium, high, or urgent
For task status, accept any reasonable input and normalize to: pending, in_progress, completed, or cancelled

Always call the tool first, then provide a friendly response about what was done."""

        messages = [{"role": "user", "content": message}]

        # Call Claude API with tools
        response = client.messages.create(
            model=model,
            max_tokens=2048,
            system=system_instruction,
            tools=tools if tools else None,
            messages=messages
        )

        # Handle tool use in responses
        while response.stop_reason == "tool_use":
            # Find the tool use block
            tool_use_block = None
            for block in response.content:
                if block.type == "tool_use":
                    tool_use_block = block
                    break

            if not tool_use_block:
                break

            function_name = tool_use_block.name
            function_args = tool_use_block.input

            # Call the appropriate function
            result = None
            if function_name == 'search_chats_tool':
                result = search_my_chats(user, function_args.get('keyword'), function_args.get('limit', 5))
            elif function_name == 'get_stats_tool':
                result = get_chat_statistics(user)
            elif function_name == 'get_recent_tool':
                result = get_recent_conversations(user, function_args.get('limit', 5))
            elif function_name == 'search_dates_tool':
                result = search_by_date_range(user, function_args.get('start_date'), function_args.get('end_date'))
            elif function_name == 'get_session_tool':
                result = get_session_summary(user, function_args.get('session_id'))
            elif function_name == 'list_sessions_tool':
                result = list_my_sessions(user, function_args.get('limit', 10))
            elif function_name == 'create_task_tool':
                result = create_task(user, function_args.get('title'), function_args.get('description', ''),
                                   function_args.get('priority', 'medium'), function_args.get('due_date_str'))
            elif function_name == 'list_tasks_tool':
                result = list_my_tasks(user, function_args.get('status', 'all'), function_args.get('limit', 10))
            elif function_name == 'get_task_details_tool':
                result = get_task_details(user, function_args.get('task_id'))
            elif function_name == 'update_task_status_tool':
                result = update_task_status(user, function_args.get('task_id'), function_args.get('status'))
            elif function_name == 'update_task_priority_tool':
                result = update_task_priority(user, function_args.get('task_id'), function_args.get('priority'))
            elif function_name == 'delete_task_tool':
                result = delete_task(user, function_args.get('task_id'))
            elif function_name == 'get_pending_tasks_tool':
                result = get_pending_tasks(user, function_args.get('limit', 5))
            elif function_name == 'get_task_summary_tool':
                result = get_task_summary(user)
            elif function_name == 'create_recurring_task_tool_wrapper':
                result = create_recurring_task_tool(user, function_args.get('title'), function_args.get('description', ''),
                                                  function_args.get('priority', 'medium'), function_args.get('frequency', 'weekly'),
                                                  function_args.get('start_date_str'), function_args.get('end_date_str'))
            elif function_name == 'list_recurring_tasks_tool_wrapper':
                result = list_recurring_tasks_tool(user)
            elif function_name == 'skip_recurring_instance_tool_wrapper':
                result = skip_recurring_instance_tool(user, function_args.get('template_id'))
            elif function_name == 'get_notification_summary_tool_wrapper':
                result = get_notification_summary_tool(user)
            elif function_name == 'set_notification_preference_tool_wrapper':
                result = set_notification_preference_tool(user, function_args.get('preference_type'), function_args.get('enabled'))
            elif function_name == 'get_productivity_metrics_tool_wrapper':
                result = get_productivity_metrics_tool(user)
            elif function_name == 'get_task_insights_tool_wrapper':
                result = get_task_insights_tool(user)
            elif function_name == 'generate_weekly_report_tool_wrapper':
                result = generate_weekly_report_tool(user)
            else:
                result = {'error': f'Unknown function: {function_name}'}

            # Continue the conversation with the tool result
            messages.append({"role": "assistant", "content": response.content})
            messages.append({
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": tool_use_block.id,
                        "content": str(result)
                    }
                ]
            })

            # Get next response
            response = client.messages.create(
                model=model,
                max_tokens=2048,
                system=system_instruction,
                tools=tools if tools else None,
                messages=messages
            )

        # Extract text from response
        text_content = ""
        for block in response.content:
            if hasattr(block, 'text'):
                text_content += block.text

        return text_content if text_content else "No response generated"

    except Exception as e:
        return f"Error: {str(e)}"


def ask_gemini_api(message, model='gemini-2.0-flash', user=None):
    """Call Gemini (Google Generative AI) API and return response text

    Supports function calling to query user's Django data via:
    - search_my_chats(keyword, limit)
    - get_chat_statistics()
    - get_recent_conversations(limit)
    - search_by_date_range(start_date, end_date)
    - get_session_summary(session_id)
    - list_my_sessions(limit)
    """
    try:
        # Define tools that expose Django data to Gemini
        tools = None
        if user:
            # Create wrapper functions that bind the user context
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
                """List user's tasks. Status can be: all, pending, in_progress, completed, or cancelled. Returns task title, description, priority, status, and due date"""
                return list_my_tasks(user, status, limit)

            def get_task_details_tool(task_id: int):
                """Get complete details of a specific task by task ID including title, description, priority, status, due date, and when it was created"""
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
                """Get summary counts of all tasks grouped by status: total, pending, in_progress, completed, cancelled, and overdue"""
                return get_task_summary(user)

            # Phase 4: Recurring tasks and notifications
            def create_recurring_task_tool_wrapper(title: str, description: str = '', priority: str = 'medium', frequency: str = 'weekly', start_date_str: str = None, end_date_str: str = None):
                """Create a recurring task. Frequency: daily, weekly, biweekly, monthly, quarterly, yearly"""
                return create_recurring_task_tool(user, title, description, priority, frequency, start_date_str, end_date_str)

            def list_recurring_tasks_tool_wrapper():
                """List all recurring task templates"""
                return list_recurring_tasks_tool(user)

            def skip_recurring_instance_tool_wrapper(template_id: int):
                """Skip next instance of a recurring task"""
                return skip_recurring_instance_tool(user, template_id)

            def get_notification_summary_tool_wrapper():
                """Get notification summary and recent notifications"""
                return get_notification_summary_tool(user)

            def set_notification_preference_tool_wrapper(preference_type: str, enabled: bool):
                """Update notification preferences. Types: deadline_reminder, overdue_reminder, daily_digest"""
                return set_notification_preference_tool(user, preference_type, enabled)

            # Phase 5: Analytics
            def get_productivity_metrics_tool_wrapper():
                """Get productivity metrics: completion rate, task counts, average completion time"""
                return get_productivity_metrics_tool(user)

            def get_task_insights_tool_wrapper():
                """Get AI-powered insights about task performance and productivity"""
                return get_task_insights_tool(user)

            def generate_weekly_report_tool_wrapper():
                """Generate a weekly productivity report"""
                return generate_weekly_report_tool(user)

            tools = [
                # Chat history and statistics
                search_chats_tool,
                get_stats_tool,
                get_recent_tool,
                search_dates_tool,
                get_session_tool,
                list_sessions_tool,
                # Task management
                create_task_tool,
                list_tasks_tool,
                get_task_details_tool,
                update_task_status_tool,
                update_task_priority_tool,
                delete_task_tool,
                get_pending_tasks_tool,
                get_task_summary_tool,
                # Phase 4: Recurring tasks
                create_recurring_task_tool_wrapper,
                list_recurring_tasks_tool_wrapper,
                skip_recurring_instance_tool_wrapper,
                # Phase 4: Notifications
                get_notification_summary_tool_wrapper,
                set_notification_preference_tool_wrapper,
                # Phase 5: Analytics
                get_productivity_metrics_tool_wrapper,
                get_task_insights_tool_wrapper,
                generate_weekly_report_tool_wrapper,
            ]

        # Create model with tools if user is provided
        system_instruction = None
        if tools:
            system_instruction = """You are a helpful AI assistant with access to tools for managing tasks and querying chat history.

When the user asks you to:
- Create a task: Use create_task_tool directly without asking for confirmation
- List/show tasks: Use list_tasks_tool or get_task_summary_tool directly
- Update task status/priority: Use the respective update tools directly
- Search chats: Use search_chats_tool directly
- Get statistics: Use get_stats_tool directly

IMPORTANT: Call the appropriate tool IMMEDIATELY when the user requests these actions. Do not ask for confirmation - just call the function and show the result.

For task priorities, accept any reasonable input and normalize to: low, medium, high, or urgent
For task status, accept any reasonable input and normalize to: pending, in_progress, completed, or cancelled

Always call the tool first, then provide a friendly response about what was done."""

            model_obj = genai.GenerativeModel(model, tools=tools, system_instruction=system_instruction)
        else:
            model_obj = genai.GenerativeModel(model)

        chat = model_obj.start_chat()
        response = chat.send_message(message)

        # Handle function calling responses
        while response.candidates and response.candidates[0].content.parts:
            last_part = response.candidates[0].content.parts[-1]

            # Check if this is a function call
            if not hasattr(last_part, 'function_call') or not last_part.function_call:
                break

            function_call = last_part.function_call
            function_name = function_call.name
            function_args = function_call.args

            # Call the appropriate function
            # Chat history functions
            if function_name == 'search_chats_tool':
                result = search_my_chats(user, function_args.get('keyword'), function_args.get('limit', 5))
            elif function_name == 'get_stats_tool':
                result = get_chat_statistics(user)
            elif function_name == 'get_recent_tool':
                result = get_recent_conversations(user, function_args.get('limit', 5))
            elif function_name == 'search_dates_tool':
                result = search_by_date_range(user, function_args.get('start_date'), function_args.get('end_date'))
            elif function_name == 'get_session_tool':
                result = get_session_summary(user, function_args.get('session_id'))
            elif function_name == 'list_sessions_tool':
                result = list_my_sessions(user, function_args.get('limit', 10))
            # Task management functions
            elif function_name == 'create_task_tool':
                result = create_task(user, function_args.get('title'), function_args.get('description', ''),
                                   function_args.get('priority', 'medium'), function_args.get('due_date_str'))
            elif function_name == 'list_tasks_tool':
                result = list_my_tasks(user, function_args.get('status', 'all'), function_args.get('limit', 10))
            elif function_name == 'get_task_details_tool':
                result = get_task_details(user, function_args.get('task_id'))
            elif function_name == 'update_task_status_tool':
                result = update_task_status(user, function_args.get('task_id'), function_args.get('status'))
            elif function_name == 'update_task_priority_tool':
                result = update_task_priority(user, function_args.get('task_id'), function_args.get('priority'))
            elif function_name == 'delete_task_tool':
                result = delete_task(user, function_args.get('task_id'))
            elif function_name == 'get_pending_tasks_tool':
                result = get_pending_tasks(user, function_args.get('limit', 5))
            elif function_name == 'get_task_summary_tool':
                result = get_task_summary(user)
            # Phase 4: Recurring tasks
            elif function_name == 'create_recurring_task_tool_wrapper':
                result = create_recurring_task_tool(user, function_args.get('title'), function_args.get('description', ''),
                                                  function_args.get('priority', 'medium'), function_args.get('frequency', 'weekly'),
                                                  function_args.get('start_date_str'), function_args.get('end_date_str'))
            elif function_name == 'list_recurring_tasks_tool_wrapper':
                result = list_recurring_tasks_tool(user)
            elif function_name == 'skip_recurring_instance_tool_wrapper':
                result = skip_recurring_instance_tool(user, function_args.get('template_id'))
            # Phase 4: Notifications
            elif function_name == 'get_notification_summary_tool_wrapper':
                result = get_notification_summary_tool(user)
            elif function_name == 'set_notification_preference_tool_wrapper':
                result = set_notification_preference_tool(user, function_args.get('preference_type'), function_args.get('enabled'))
            # Phase 5: Analytics
            elif function_name == 'get_productivity_metrics_tool_wrapper':
                result = get_productivity_metrics_tool(user)
            elif function_name == 'get_task_insights_tool_wrapper':
                result = get_task_insights_tool(user)
            elif function_name == 'generate_weekly_report_tool_wrapper':
                result = generate_weekly_report_tool(user)
            else:
                result = {'error': f'Unknown function: {function_name}'}

            # Send function result back to Gemini with proper format
            response = chat.send_message(
                genai.protos.Content(
                    parts=[
                        genai.protos.Part(
                            function_response=genai.protos.FunctionResponse(
                                name=function_name,
                                response=result
                            )
                        )
                    ]
                )
            )

        return response.text
    except Exception as e:
        return f"Error: {str(e)}"


def ask_gemini(message, model='claude-3-5-sonnet-20241022', user=None):
    """Legacy wrapper that now calls ask_ai() - supports both Claude and Gemini"""
    return ask_ai(message, model, user)


def ask_openai(request, message, model='gemini-1.5-flash'):
    """Legacy function for backward compatibility"""
    text = request.POST.get("message")
    return ask_gemini(text, model)


# ========== DATA INTEGRATION FUNCTIONS ==========
# These functions expose Django data to Gemini via function calling

def search_my_chats(user, keyword: str, limit: int = 5):
    """Search through user's chat history by keyword"""
    try:
        results = Chat.objects.filter(
            session__user=user,
            is_deleted=False
        ).filter(
            message__icontains=keyword
        ).order_by('-created_at')[:limit]

        return {
            'count': results.count(),
            'results': [
                {
                    'message': r.message,
                    'response_preview': r.response[:200] + '...' if len(r.response) > 200 else r.response,
                    'created_at': r.created_at.strftime('%Y-%m-%d %H:%M'),
                    'session': r.session.name
                }
                for r in results
            ]
        }
    except Exception as e:
        return {'error': str(e)}


def get_chat_statistics(user):
    """Get user's chat usage statistics"""
    try:
        total_chats = Chat.objects.filter(
            session__user=user,
            is_deleted=False
        ).count()

        total_sessions = ChatSession.objects.filter(
            user=user,
            is_active=True
        ).count()

        # Get most active session
        from django.db.models import Count
        most_active = ChatSession.objects.filter(
            user=user,
            is_active=True
        ).annotate(
            msg_count=Count('messages')
        ).order_by('-msg_count').first()

        # Get recent activity
        from django.utils import timezone
        from datetime import timedelta
        last_week = timezone.now() - timedelta(days=7)
        messages_this_week = Chat.objects.filter(
            session__user=user,
            is_deleted=False,
            created_at__gte=last_week
        ).count()

        return {
            'total_messages': total_chats,
            'total_sessions': total_sessions,
            'most_active_session': most_active.name if most_active else 'None',
            'messages_this_week': messages_this_week,
            'account_created': user.date_joined.strftime('%Y-%m-%d')
        }
    except Exception as e:
        return {'error': str(e)}


def get_recent_conversations(user, limit: int = 5):
    """Get recent chat conversations"""
    try:
        recent_chats = Chat.objects.filter(
            session__user=user,
            is_deleted=False
        ).order_by('-created_at')[:limit]

        return {
            'count': len(recent_chats),
            'conversations': [
                {
                    'message': r.message,
                    'response_preview': r.response[:150] + '...' if len(r.response) > 150 else r.response,
                    'created_at': r.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                    'session': r.session.name
                }
                for r in recent_chats
            ]
        }
    except Exception as e:
        return {'error': str(e)}


def search_by_date_range(user, start_date: str, end_date: str):
    """Search chats within a date range (YYYY-MM-DD format)"""
    try:
        from datetime import datetime
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')

        results = Chat.objects.filter(
            session__user=user,
            is_deleted=False,
            created_at__date__gte=start.date(),
            created_at__date__lte=end.date()
        ).order_by('-created_at')

        return {
            'count': results.count(),
            'date_range': f'{start_date} to {end_date}',
            'conversations': [
                {
                    'message': r.message,
                    'response_preview': r.response[:150] + '...' if len(r.response) > 150 else r.response,
                    'created_at': r.created_at.strftime('%Y-%m-%d %H:%M'),
                    'session': r.session.name
                }
                for r in results
            ]
        }
    except ValueError as e:
        return {'error': 'Invalid date format. Use YYYY-MM-DD'}
    except Exception as e:
        return {'error': str(e)}


def get_session_summary(user, session_id: int):
    """Get detailed summary of a specific session"""
    try:
        session = ChatSession.objects.get(id=session_id, user=user)
        messages = session.messages.filter(is_deleted=False).order_by('created_at')

        return {
            'session_name': session.name,
            'session_model': session.model,
            'created_at': session.created_at.strftime('%Y-%m-%d %H:%M'),
            'message_count': messages.count(),
            'last_message_at': messages.last().created_at.strftime('%Y-%m-%d %H:%M') if messages.exists() else 'No messages',
            'first_message_preview': messages.first().message if messages.exists() else 'None',
            'first_message_date': messages.first().created_at.strftime('%Y-%m-%d') if messages.exists() else 'N/A'
        }
    except ChatSession.DoesNotExist:
        return {'error': f'Session {session_id} not found'}
    except Exception as e:
        return {'error': str(e)}


def list_my_sessions(user, limit: int = 10):
    """List all user's chat sessions"""
    try:
        sessions = ChatSession.objects.filter(
            user=user,
            is_active=True
        ).order_by('-created_at')[:limit]

        from django.db.models import Count
        return {
            'count': sessions.count(),
            'sessions': [
                {
                    'id': s.id,
                    'name': s.name,
                    'model': s.model,
                    'message_count': s.messages.count(),
                    'created_at': s.created_at.strftime('%Y-%m-%d %H:%M'),
                    'last_updated': s.updated_at.strftime('%Y-%m-%d %H:%M')
                }
                for s in sessions
            ]
        }
    except Exception as e:
        return {'error': str(e)}


# ========== TASK MANAGEMENT FUNCTIONS ==========
# These functions expose Task operations to Gemini via function calling

def create_task(user, title: str, description: str = '', priority: str = 'medium', due_date_str: str = None):
    """Create a new task for user"""
    try:
        task_data = {
            'user': user,
            'title': title,
            'description': description,
            'priority': priority if priority in ['low', 'medium', 'high', 'urgent'] else 'medium',
        }

        if due_date_str:
            try:
                from dateutil import parser
                task_data['due_date'] = parser.parse(due_date_str)
            except:
                pass  # If date parsing fails, just skip due_date

        task = Task.objects.create(**task_data)

        return {
            'success': True,
            'task_id': task.id,
            'title': task.title,
            'priority': task.get_priority_display(),
            'status': task.get_status_display(),
            'created_at': task.created_at.strftime('%Y-%m-%d %H:%M')
        }
    except Exception as e:
        return {'error': str(e)}


def list_my_tasks(user, status: str = 'all', limit: int = 10):
    """List user's tasks filtered by status"""
    try:
        query = Task.objects.filter(user=user)

        if status != 'all':
            query = query.filter(status=status)

        tasks = query.order_by('-priority', '-created_at')[:limit]

        return {
            'count': tasks.count(),
            'tasks': [
                {
                    'id': t.id,
                    'title': t.title,
                    'description': t.description[:100] + '...' if len(t.description) > 100 else t.description,
                    'priority': t.get_priority_display(),
                    'status': t.get_status_display(),
                    'due_date': t.due_date.strftime('%Y-%m-%d %H:%M') if t.due_date else 'No due date',
                    'is_overdue': t.is_overdue(),
                    'created_at': t.created_at.strftime('%Y-%m-%d %H:%M')
                }
                for t in tasks
            ]
        }
    except Exception as e:
        return {'error': str(e)}


def get_task_details(user, task_id: int):
    """Get detailed information about a specific task"""
    try:
        task = Task.objects.get(id=task_id, user=user)

        return {
            'id': task.id,
            'title': task.title,
            'description': task.description,
            'priority': task.get_priority_display(),
            'status': task.get_status_display(),
            'due_date': task.due_date.strftime('%Y-%m-%d %H:%M') if task.due_date else 'No due date',
            'days_until_due': task.days_until_due(),
            'is_overdue': task.is_overdue(),
            'created_at': task.created_at.strftime('%Y-%m-%d %H:%M'),
            'updated_at': task.updated_at.strftime('%Y-%m-%d %H:%M'),
            'completed_at': task.completed_at.strftime('%Y-%m-%d %H:%M') if task.completed_at else None
        }
    except Task.DoesNotExist:
        return {'error': f'Task {task_id} not found'}
    except Exception as e:
        return {'error': str(e)}


def update_task_status(user, task_id: int, status: str):
    """Update task status (pending, in_progress, completed, cancelled)"""
    try:
        task = Task.objects.get(id=task_id, user=user)

        if status not in ['pending', 'in_progress', 'completed', 'cancelled']:
            return {'error': 'Invalid status. Use: pending, in_progress, completed, cancelled'}

        task.status = status

        # Set completed_at timestamp when marking as completed
        if status == 'completed' and not task.completed_at:
            task.completed_at = timezone.now()
        elif status != 'completed':
            task.completed_at = None

        task.save()

        return {
            'success': True,
            'task_id': task.id,
            'title': task.title,
            'status': task.get_status_display(),
            'updated_at': task.updated_at.strftime('%Y-%m-%d %H:%M')
        }
    except Task.DoesNotExist:
        return {'error': f'Task {task_id} not found'}
    except Exception as e:
        return {'error': str(e)}


def update_task_priority(user, task_id: int, priority: str):
    """Update task priority (low, medium, high, urgent)"""
    try:
        task = Task.objects.get(id=task_id, user=user)

        if priority not in ['low', 'medium', 'high', 'urgent']:
            return {'error': 'Invalid priority. Use: low, medium, high, urgent'}

        task.priority = priority
        task.save()

        return {
            'success': True,
            'task_id': task.id,
            'title': task.title,
            'priority': task.get_priority_display(),
            'updated_at': task.updated_at.strftime('%Y-%m-%d %H:%M')
        }
    except Task.DoesNotExist:
        return {'error': f'Task {task_id} not found'}
    except Exception as e:
        return {'error': str(e)}


def delete_task(user, task_id: int):
    """Delete a task (soft delete)"""
    try:
        task = Task.objects.get(id=task_id, user=user)
        task_title = task.title
        task.delete()

        return {
            'success': True,
            'message': f'Task "{task_title}" deleted successfully'
        }
    except Task.DoesNotExist:
        return {'error': f'Task {task_id} not found'}
    except Exception as e:
        return {'error': str(e)}


def get_pending_tasks(user, limit: int = 5):
    """Get urgent and high priority pending tasks"""
    try:
        tasks = Task.objects.filter(
            user=user,
            status__in=['pending', 'in_progress']
        ).filter(
            priority__in=['urgent', 'high']
        ).order_by('-priority', 'due_date')[:limit]

        return {
            'count': tasks.count(),
            'urgent_tasks': [
                {
                    'id': t.id,
                    'title': t.title,
                    'priority': t.get_priority_display(),
                    'due_date': t.due_date.strftime('%Y-%m-%d') if t.due_date else 'No due date',
                    'is_overdue': t.is_overdue()
                }
                for t in tasks
            ]
        }
    except Exception as e:
        return {'error': str(e)}


def get_task_summary(user):
    """Get summary of all tasks by status with full task details"""
    try:
        all_tasks = Task.objects.filter(user=user)

        # Build task summary with full details
        summary = {
            'total_tasks': all_tasks.count(),
            'status_counts': {
                'pending': all_tasks.filter(status='pending').count(),
                'in_progress': all_tasks.filter(status='in_progress').count(),
                'completed': all_tasks.filter(status='completed').count(),
                'cancelled': all_tasks.filter(status='cancelled').count(),
            },
            'overdue_count': sum(1 for t in all_tasks.filter(status__in=['pending', 'in_progress']) if t.is_overdue()),
            'tasks_by_status': {}
        }

        # Add detailed task list grouped by status
        for status in ['pending', 'in_progress', 'completed', 'cancelled']:
            tasks = all_tasks.filter(status=status).order_by('-priority', '-created_at')
            summary['tasks_by_status'][status] = [
                {
                    'id': t.id,
                    'title': t.title,
                    'description': t.description if t.description else 'No description',
                    'priority': t.get_priority_display(),
                    'due_date': t.due_date.strftime('%Y-%m-%d') if t.due_date else 'No deadline',
                    'is_overdue': t.is_overdue(),
                    'created_at': t.created_at.strftime('%Y-%m-%d')
                }
                for t in tasks
            ]

        return summary
    except Exception as e:
        return {'error': str(e)}


# ============================================================================
# PHASE 3: CALENDAR INTEGRATION ENDPOINTS
# ============================================================================

@login_required
def api_tasks_calendar(request):
    """Return user's tasks as calendar events (JSON format for FullCalendar)"""
    try:
        # Get filter parameters
        priority_filter = request.GET.get('priority', '')
        status_filter = request.GET.get('status', '')

        # Query tasks
        tasks = Task.objects.filter(user=request.user, due_date__isnull=False)

        # Apply filters
        if priority_filter:
            tasks = tasks.filter(priority=priority_filter)
        if status_filter:
            tasks = tasks.filter(status=status_filter)

        # Build calendar events
        events = []
        for task in tasks:
            # FullCalendar requires events with start/end dates
            start_date = task.due_date
            # End date is 1 hour after start (for timed events)
            end_date = start_date + timezone.timedelta(hours=1)

            events.append({
                'id': task.id,
                'title': task.title,
                'start': start_date.isoformat(),
                'end': end_date.isoformat(),
                'backgroundColor': task.get_priority_color(),
                'borderColor': task.get_priority_color(),
                'textColor': '#ffffff',
                'extendedProps': {
                    'taskId': task.id,
                    'priority': task.priority,
                    'status': task.status,
                    'description': task.description if task.description else 'No description',
                    'isOverdue': task.is_overdue(),
                    'daysUntilDue': task.days_until_due(),
                    'statusDisplay': task.get_status_display(),
                    'priorityDisplay': task.get_priority_display(),
                }
            })

        return JsonResponse({
            'success': True,
            'count': len(events),
            'events': events
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
def api_task_update_due_date(request, task_id):
    """Update task's due date via drag-and-drop on calendar"""
    try:
        task = get_object_or_404(Task, id=task_id, user=request.user)

        # Get new due date from POST or GET parameter
        new_date_str = request.POST.get('due_date') or request.GET.get('due_date')

        if not new_date_str:
            return JsonResponse({
                'success': False,
                'error': 'No due_date provided'
            }, status=400)

        # Parse ISO format date
        try:
            # Handle ISO format dates (with or without timezone)
            if new_date_str.endswith('Z'):
                new_date_str = new_date_str[:-1] + '+00:00'

            # fromisoformat already returns aware datetime if tzinfo is present
            parsed_date = datetime.fromisoformat(new_date_str)

            # Make sure it's timezone-aware
            if parsed_date.tzinfo is None:
                new_date = timezone.make_aware(parsed_date)
            else:
                new_date = parsed_date
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'Invalid date format: {str(e)}'
            }, status=400)

        # Update task
        task.due_date = new_date
        task.updated_at = timezone.now()
        task.save()

        return JsonResponse({
            'success': True,
            'taskId': task.id,
            'title': task.title,
            'newDueDate': new_date.isoformat(),
            'message': f'Task "{task.title}" rescheduled to {new_date.strftime("%Y-%m-%d %H:%M")}'
        })
    except Task.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Task not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
def calendar_view(request):
    """Render calendar page"""
    return render(request, 'calendar.html')


# ========== PHASE 4: NOTIFICATION & RECURRING TASK TOOLS ==========

def create_recurring_task_tool(user, title: str, description: str = '', priority: str = 'medium', frequency: str = 'weekly', start_date_str: str = None, end_date_str: str = None):
    """Create a recurring task template. Frequency must be one of: daily, weekly, biweekly, monthly, quarterly, yearly"""
    try:
        # Parse dates
        if not start_date_str:
            start_date = timezone.now()
        else:
            # Handle various date formats
            try:
                start_date = datetime.fromisoformat(start_date_str.replace('Z', '+00:00'))
                if start_date.tzinfo is None:
                    start_date = timezone.make_aware(start_date)
            except:
                start_date = timezone.now()

        end_date = None
        if end_date_str:
            try:
                end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
                if end_date.tzinfo is None:
                    end_date = timezone.make_aware(end_date)
            except:
                pass

        # Validate frequency
        valid_frequencies = ['daily', 'weekly', 'biweekly', 'monthly', 'quarterly', 'yearly']
        if frequency not in valid_frequencies:
            return {'error': f'Invalid frequency. Must be one of: {", ".join(valid_frequencies)}'}

        # Calculate next instance date based on frequency
        next_instance = start_date
        if frequency == 'daily':
            next_instance = start_date + timedelta(days=1)
        elif frequency == 'weekly':
            next_instance = start_date + timedelta(weeks=1)
        elif frequency == 'biweekly':
            next_instance = start_date + timedelta(weeks=2)
        elif frequency == 'monthly':
            next_instance = start_date + timedelta(days=30)
        elif frequency == 'quarterly':
            next_instance = start_date + timedelta(days=90)
        elif frequency == 'yearly':
            next_instance = start_date + timedelta(days=365)

        # Create template
        template = RecurringTaskTemplate.objects.create(
            user=user,
            title=title,
            description=description,
            priority=priority,
            frequency=frequency,
            start_date=start_date,
            end_date=end_date,
            next_instance_date=next_instance,
            is_active=True
        )

        # Create first instance
        first_task = Task.objects.create(
            user=user,
            title=title,
            description=description,
            priority=priority,
            due_date=start_date
        )

        RecurringTaskInstance.objects.create(
            template=template,
            task=first_task,
            instance_number=1
        )

        return {
            'template_id': template.id,
            'title': title,
            'frequency': frequency,
            'start_date': start_date.isoformat(),
            'first_task_id': first_task.id,
            'message': f'Recurring task "{title}" created with {frequency} frequency'
        }
    except Exception as e:
        return {'error': str(e)}


def list_recurring_tasks_tool(user):
    """List all recurring task templates for user"""
    try:
        templates = RecurringTaskTemplate.objects.filter(user=user, is_active=True).order_by('-created_at')
        return {
            'total': templates.count(),
            'templates': [
                {
                    'id': t.id,
                    'title': t.title,
                    'frequency': t.frequency,
                    'priority': t.priority,
                    'next_instance': t.next_instance_date.isoformat(),
                    'is_active': t.is_active,
                }
                for t in templates
            ]
        }
    except Exception as e:
        return {'error': str(e)}


def skip_recurring_instance_tool(user, template_id: int):
    """Skip the next instance of a recurring task"""
    try:
        template = RecurringTaskTemplate.objects.get(id=template_id, user=user)

        # Calculate next instance date
        if template.frequency == 'daily':
            template.next_instance_date = template.next_instance_date + timedelta(days=1)
        elif template.frequency == 'weekly':
            template.next_instance_date = template.next_instance_date + timedelta(weeks=1)
        elif template.frequency == 'biweekly':
            template.next_instance_date = template.next_instance_date + timedelta(weeks=2)
        elif template.frequency == 'monthly':
            template.next_instance_date = template.next_instance_date + timedelta(days=30)
        elif template.frequency == 'quarterly':
            template.next_instance_date = template.next_instance_date + timedelta(days=90)
        elif template.frequency == 'yearly':
            template.next_instance_date = template.next_instance_date + timedelta(days=365)

        # Check if end date exceeded
        if template.end_date and template.next_instance_date > template.end_date:
            template.is_active = False

        template.save()

        return {
            'template_id': template.id,
            'title': template.title,
            'next_instance': template.next_instance_date.isoformat(),
            'message': f'Skipped next instance of "{template.title}"'
        }
    except RecurringTaskTemplate.DoesNotExist:
        return {'error': 'Recurring task template not found'}
    except Exception as e:
        return {'error': str(e)}


def get_notification_summary_tool(user):
    """Get notification summary for user"""
    try:
        unread = Notification.objects.filter(user=user, read_at__isnull=True).count()
        recent = Notification.objects.filter(user=user).order_by('-created_at')[:5]

        return {
            'unread_count': unread,
            'total_count': Notification.objects.filter(user=user).count(),
            'recent': [
                {
                    'id': n.id,
                    'type': n.notification_type,
                    'subject': n.subject,
                    'sent': n.is_sent,
                    'created_at': n.created_at.isoformat(),
                }
                for n in recent
            ]
        }
    except Exception as e:
        return {'error': str(e)}


def set_notification_preference_tool(user, preference_type: str, enabled: bool):
    """Update notification preferences. Types: deadline_reminder, overdue_reminder, daily_digest"""
    try:
        prefs, created = NotificationPreference.objects.get_or_create(user=user)

        if preference_type == 'deadline_reminder':
            prefs.deadline_reminder_enabled = enabled
        elif preference_type == 'overdue_reminder':
            prefs.overdue_reminder_enabled = enabled
        elif preference_type == 'daily_digest':
            prefs.daily_digest_enabled = enabled
        else:
            return {'error': f'Unknown preference type: {preference_type}'}

        prefs.save()

        return {
            'preference': preference_type,
            'enabled': enabled,
            'message': f'{preference_type} notifications are now {"enabled" if enabled else "disabled"}'
        }
    except Exception as e:
        return {'error': str(e)}


# ========== PHASE 5: ANALYTICS TOOLS ==========

def get_productivity_metrics_tool(user):
    """Get user's productivity metrics"""
    try:
        tasks = Task.objects.filter(user=user)
        completed_tasks = tasks.filter(status='completed')
        overdue_tasks = tasks.filter(status__in=['pending', 'in_progress']).filter(
            due_date__lt=timezone.now()
        ).count()

        # Calculate completion rate
        total = tasks.count()
        completion_rate = (completed_tasks.count() / total * 100) if total > 0 else 0

        # Calculate average time to complete
        completed_with_dates = completed_tasks.filter(completed_at__isnull=False).filter(created_at__isnull=False)
        if completed_with_dates.exists():
            total_duration = sum((t.completed_at - t.created_at).total_seconds() for t in completed_with_dates)
            avg_duration_days = total_duration / (completed_with_dates.count() * 86400)
        else:
            avg_duration_days = 0

        return {
            'total_tasks': total,
            'completed_tasks': completed_tasks.count(),
            'pending_tasks': tasks.filter(status='pending').count(),
            'in_progress_tasks': tasks.filter(status='in_progress').count(),
            'overdue_tasks': overdue_tasks,
            'completion_rate': round(completion_rate, 1),
            'avg_days_to_complete': round(avg_duration_days, 1),
        }
    except Exception as e:
        return {'error': str(e)}


def get_task_insights_tool(user):
    """Get AI-powered task insights"""
    try:
        insights = []
        metrics = get_productivity_metrics_tool(user)

        if 'error' not in metrics:
            # Insight 1: High completion rate
            if metrics['completion_rate'] >= 80:
                insights.append({
                    'type': 'positive',
                    'title': 'Excellent Progress!',
                    'message': f'You\'re completing {metrics["completion_rate"]:.0f}% of your tasks. Keep it up!'
                })
            elif metrics['completion_rate'] < 30 and metrics['total_tasks'] > 5:
                insights.append({
                    'type': 'warning',
                    'title': 'Low Completion Rate',
                    'message': f'Only {metrics["completion_rate"]:.0f}% of tasks are completed. Try breaking down larger tasks.'
                })

            # Insight 2: Overdue tasks
            if metrics['overdue_tasks'] > 0:
                insights.append({
                    'type': 'warning',
                    'title': 'Overdue Tasks',
                    'message': f'You have {metrics["overdue_tasks"]} overdue tasks. Prioritize completing them.'
                })

            # Insight 3: Task velocity
            if metrics['avg_days_to_complete'] > 0:
                insights.append({
                    'type': 'info',
                    'title': 'Average Task Duration',
                    'message': f'Your tasks take an average of {metrics["avg_days_to_complete"]:.0f} days to complete.'
                })

        return {'insights': insights}
    except Exception as e:
        return {'error': str(e)}


def generate_weekly_report_tool(user):
    """Generate weekly productivity report"""
    try:
        # Get last 7 days of analytics
        today = timezone.now().date()
        week_ago = today - timedelta(days=7)

        analytics = TaskAnalytics.objects.filter(
            user=user,
            date__gte=week_ago
        ).order_by('-date')

        if not analytics.exists():
            return {'message': 'No analytics data available for this week'}

        total_completed = sum(a.completed_today for a in analytics)
        avg_completion_rate = sum(a.completion_rate for a in analytics) / analytics.count() if analytics.count() > 0 else 0

        return {
            'week_of': week_ago.isoformat(),
            'days_tracked': analytics.count(),
            'total_completed': total_completed,
            'avg_completion_rate': round(avg_completion_rate, 1),
            'highest_completion_day': max((a.date, a.completed_today) for a in analytics)[0].isoformat() if analytics.exists() else None,
            'message': f'Weekly report: {total_completed} tasks completed with {avg_completion_rate:.0f}% average completion rate'
        }
    except Exception as e:
        return {'error': str(e)}


# ========== PHASE 4-5 API ENDPOINTS ==========

@login_required
def api_notifications_list(request):
    """Get user's notifications"""
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')[:20]
    return JsonResponse({
        'notifications': [
            {
                'id': n.id,
                'type': n.get_notification_type_display(),
                'subject': n.subject,
                'message': n.message,
                'is_sent': n.is_sent,
                'is_read': n.read_at is not None,
                'sent_at': n.sent_at.isoformat() if n.sent_at else None,
                'created_at': n.created_at.isoformat(),
            }
            for n in notifications
        ]
    })


@login_required
def api_notification_mark_read(request, notification_id):
    """Mark notification as read"""
    try:
        notification = Notification.objects.get(id=notification_id, user=request.user)
        notification.mark_as_read()
        return JsonResponse({'success': True})
    except Notification.DoesNotExist:
        return JsonResponse({'error': 'Notification not found'}, status=404)


@login_required
def api_recurring_tasks_list(request):
    """List recurring task templates"""
    templates = RecurringTaskTemplate.objects.filter(user=request.user, is_active=True)
    return JsonResponse({
        'total': templates.count(),
        'templates': [
            {
                'id': t.id,
                'title': t.title,
                'description': t.description,
                'frequency': t.get_frequency_display(),
                'priority': t.get_priority_display(),
                'next_instance': t.next_instance_date.isoformat(),
                'instances_count': t.instances.count(),
            }
            for t in templates
        ]
    })


@login_required
def api_productivity_metrics(request):
    """Get productivity metrics"""
    return JsonResponse(get_productivity_metrics_tool(request.user))


@login_required
def api_task_insights(request):
    """Get task insights"""
    return JsonResponse(get_task_insights_tool(request.user))


@login_required
def api_weekly_report(request):
    """Get weekly report"""
    return JsonResponse(generate_weekly_report_tool(request.user))


@login_required
def chatbot_home(request):
    """Redirect to latest active session or create one"""
    latest = ChatSession.objects.filter(
        user=request.user,
        is_active=True
    ).first()

    if latest:
        return redirect('chatbot_session', session_id=latest.id)

    # Create default session
    session = ChatSession.objects.create(
        user=request.user,
        name='Chat'
    )
    return redirect('chatbot_session', session_id=session.id)


@login_required
def chatbot_session(request, session_id):
    """Main chat view for specific session"""
    session = get_object_or_404(ChatSession, id=session_id, user=request.user)

    if request.method == 'POST':
        message = request.POST.get('message')
        # Use model from request if provided, otherwise use session's default model
        model = request.POST.get('model', session.model)
        response = ask_ai(message, model, user=request.user)

        chat = Chat.objects.create(
            session=session,
            message=message,
            response=response
        )

        return JsonResponse({
            'message': message,
            'response': chat.response_md(),
            'id': chat.id
        })

    messages = session.messages.filter(is_deleted=False)
    return render(request, 'chatbot.html', {
        'session': session,
        'messages': messages
    })


@login_required
def api_session_list(request):
    """Get all sessions for user"""
    sessions = ChatSession.objects.filter(user=request.user, is_active=True).order_by('-created_at')
    return JsonResponse({
        'sessions': [{
            'id': s.id,
            'name': s.name,
            'model': s.model,
            'message_count': s.messages.filter(is_deleted=False).count(),
            'created_at': s.created_at.isoformat(),
            'last_updated': s.updated_at.isoformat(),
        } for s in sessions]
    })


@login_required
def api_session_create(request):
    """Create new chat session"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=400)

    name = request.POST.get('name', 'New Chat')
    model = request.POST.get('model', 'claude-3-5-sonnet-20241022')

    session = ChatSession.objects.create(
        user=request.user,
        name=name,
        model=model
    )

    return JsonResponse({
        'id': session.id,
        'name': session.name,
        'model': session.model,
        'created_at': session.created_at.isoformat()
    })


@login_required
def api_session_detail(request, session_id):
    """Get single session with all messages"""
    session = get_object_or_404(ChatSession, id=session_id, user=request.user)
    messages = session.messages.filter(is_deleted=False).order_by('created_at')

    return JsonResponse({
        'session': {
            'id': session.id,
            'name': session.name,
            'model': session.model,
        },
        'messages': [{
            'id': m.id,
            'message': m.message,
            'response': m.response_md(),
            'created_at': m.created_at.isoformat(),
        } for m in messages]
    })


@login_required
def api_session_update(request, session_id):
    """Update session"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=400)

    session = get_object_or_404(ChatSession, id=session_id, user=request.user)

    name = request.POST.get('name')
    model = request.POST.get('model')

    if name:
        session.name = name
    if model:
        session.model = model

    session.save()
    return JsonResponse({'success': True})


@login_required
def api_session_delete(request, session_id):
    """Delete session"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=400)

    session = get_object_or_404(ChatSession, id=session_id, user=request.user)
    hard_delete = request.POST.get('hard_delete', False) == 'true'

    if hard_delete:
        session.delete()
    else:
        session.is_active = False
        session.save()

    return JsonResponse({'success': True})


@login_required
def settings_page(request):
    """Display user settings page"""
    return render(request, 'settings.html', {
        'user': request.user
    })


@login_required
def api_list_models(request):
    """Fetch available free tier Gemini models with caching"""
    cache_key = 'gemini_models_list'
    models_data = cache.get(cache_key)

    if not models_data:
        try:
            # Free tier models that support generateContent
            free_tier_models = [
                'gemini-2.0-flash',
                'gemini-1.5-flash',
                'gemini-1.5-flash-8b',
            ]

            models = genai.list_models()
            # Filter for generateContent capable models AND free tier only
            available_models = [m for m in models if 'generateContent' in m.supported_generation_methods]

            models_data = [{
                'name': m.name.replace('models/', ''),
                'display': m.display_name
            } for m in available_models if m.name.replace('models/', '') in free_tier_models]

            # If no free tier models found, provide defaults
            if not models_data:
                models_data = [
                    {'name': 'gemini-2.0-flash', 'display': 'Gemini 2.0 Flash (Free)'},
                    {'name': 'gemini-1.5-flash', 'display': 'Gemini 1.5 Flash (Free)'},
                    {'name': 'gemini-1.5-flash-8b', 'display': 'Gemini 1.5 Flash 8B (Free)'},
                ]

            cache.set(cache_key, models_data, timeout=3600)  # 1 hour
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'models': models_data})


@login_required
def api_save_settings(request):
    """Save user model preference"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=400)

    model_name = request.POST.get('model')

    if not model_name:
        return JsonResponse({'error': 'Model name required'}, status=400)

    # Validate model - support both Claude and Gemini
    valid_models = [
        # Claude models
        'claude-3-5-sonnet-20241022',
        'claude-3-opus-20250219',
        'claude-3-haiku-20240307',
        # Gemini models
        'gemini-2.0-flash',
        'gemini-1.5-flash',
        'gemini-1.5-pro',
        'gemini-pro',
    ]

    if model_name not in valid_models:
        return JsonResponse({'error': f'Invalid model: {model_name}'}, status=400)

    # Get or create current session and update model
    session = ChatSession.objects.filter(
        user=request.user,
        is_active=True
    ).first()

    if session:
        session.model = model_name
        session.save()

    return JsonResponse({'success': True, 'message': 'Settings saved'})


@login_required
def api_send_message_async(request, session_id):
    """Queue message for async processing and return request ID immediately"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=400)

    session = get_object_or_404(ChatSession, id=session_id, user=request.user)
    message = request.POST.get('message', '').strip()

    if not message:
        return JsonResponse({'error': 'Empty message'}, status=400)

    # Queue the message
    request_id = message_processor.queue_message(session_id, message)

    return JsonResponse({
        'request_id': request_id,
        'status': 'queued'
    })


@login_required
def api_check_response(request, request_id):
    """Check if response is ready (polling endpoint)"""
    response = message_processor.get_response(request_id)
    return JsonResponse(response)


def generate_model(request):
    if request.method == 'POST':
        model_name = request.POST.get('model_name')
        try:
            model = genai.GenerativeModel(model_name)
            return JsonResponse({'status': 'success', 'message': f'Model {model_name} generated successfully.'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    return render(request, 'generate_model.html')


def login(request):
    if request.method=='POST':
        username = request.POST['username']
        password = request.POST['password']
        user = auth.authenticate(request, username=username, password=password)
        if user is not None:
            auth.login(request, user)
            return redirect('chatbot_home')
        else:
            error_message = 'Invalid username or password'
            return render(request, 'login.html', {'error_message': error_message})
    else:
        return render(request, 'login.html')

def register(request):
    if request.method == 'POST':
        username = request.POST['username']
        email = request.POST['email']
        password1 = request.POST['password1']
        password2 = request.POST['password2']

        if password1==password2:
            try:
                user = User.objects.create_user(username, email, password1)
                user.save()
                auth.login(request, user)
                return redirect('chatbot_home')
            except:
                error_message = 'Error creating account'
            return render(request, 'register.html', {'error_message': error_message})
        else:
            error_message = "Password don't match"
            return render(request, 'register.html', {'error_message': error_message})
    return render(request, 'register.html')

def logout(request):
    auth.logout(request)
    return redirect('login')