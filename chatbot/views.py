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
    TaskAnalytics, ChatAnalytics, ClaudeTerminalSession
)
from .message_queue import message_processor

from django.utils import timezone
from django.contrib.auth.decorators import login_required
from dotenv import load_dotenv
load_dotenv()

import anthropic
import google.generativeai as genai

try:
    import ollama as ollama_client
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False

# Load environment variables from .env file
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
API_SECRET_KEY = os.getenv('API_SECRET_KEY')
OLLAMA_BASE_URL = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
OLLAMA_DEFAULT_MODEL = os.getenv('OLLAMA_DEFAULT_MODEL', 'llama3.2')

# Initialize Anthropic client
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# Initialize Gemini (Generative AI)
if API_SECRET_KEY:
    genai.configure(api_key=API_SECRET_KEY)


def get_ollama_models():
    """Fetch available models from local Ollama instance."""
    if not OLLAMA_AVAILABLE:
        return []
    try:
        oc = ollama_client.Client(host=OLLAMA_BASE_URL)
        response = oc.list()
        return [m.get('name', m.get('model', '')) for m in response.get('models', [])]
    except Exception:
        return []


def ask_ai(message, model='claude-3-5-sonnet-20241022', user=None, tools_enabled=True):
    """Smart router that uses Claude, Gemini, or Ollama based on model parameter

    Claude models: claude-3-5-sonnet-20241022, claude-3-opus-20250219, etc.
    Gemini models: gemini-2.0-flash, gemini-1.5-flash, gemini-pro, etc.
    Ollama models: ollama:llama3.2, ollama:mistral, or any locally installed model
    """
    # When tools are disabled, don't pass user so tool definitions are skipped
    effective_user = user if tools_enabled else None

    # Determine which API to use based on model name
    if model.startswith('claude'):
        return ask_claude(message, model, effective_user)
    elif model.startswith('gemini') or model.startswith('gpt'):
        return ask_gemini_api(message, model, effective_user)
    elif model.startswith('ollama:'):
        actual_model = model[len('ollama:'):]
        return ask_ollama(message, actual_model, effective_user)
    else:
        # Check if it's a locally installed Ollama model
        ollama_models = get_ollama_models()
        if ollama_models and model in ollama_models:
            return ask_ollama(message, model, effective_user)
        # Default to Claude for unknown models
        return ask_claude(message, model, effective_user)


def ask_claude(message, model='claude-3-5-sonnet-20241022', user=None):
    """Call Claude API and return response text.
    Uses shared tool definitions from chatbot.tools package.
    """
    from chatbot.tools import format_tools_for_claude, execute_tool, SYSTEM_INSTRUCTION

    try:
        tools = format_tools_for_claude(user) if user else []

        messages = [{"role": "user", "content": message}]

        # Call Claude API with tools
        response = client.messages.create(
            model=model,
            max_tokens=2048,
            system=SYSTEM_INSTRUCTION if tools else None,
            tools=tools if tools else None,
            messages=messages
        )

        # Handle tool use in responses
        while response.stop_reason == "tool_use":
            tool_use_block = None
            for block in response.content:
                if block.type == "tool_use":
                    tool_use_block = block
                    break

            if not tool_use_block:
                break

            # Dispatch through shared executor
            result = execute_tool(user, tool_use_block.name, tool_use_block.input)

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
                system=SYSTEM_INSTRUCTION if tools else None,
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


def ask_gemini_api(message, model='gemini-2.5-flash', user=None):
    """Call Gemini (Google Generative AI) API and return response text.
    Uses shared tool definitions from chatbot.tools package.
    """
    from chatbot.tools import format_tools_for_gemini, execute_tool, SYSTEM_INSTRUCTION

    try:
        model_obj = genai.GenerativeModel(model)
        chat = model_obj.start_chat()

        # Prepend system instruction to the user message
        full_message = f"{SYSTEM_INSTRUCTION}\n\n{message}" if SYSTEM_INSTRUCTION else message

        # Check if this version supports tools/function calling
        import inspect
        model_init_params = inspect.signature(genai.GenerativeModel.__init__).parameters
        supports_tools = 'tools' in model_init_params

        if supports_tools:
            tools = format_tools_for_gemini(user) if user else None
            if tools:
                # Re-create model with tools for newer versions
                model_obj = genai.GenerativeModel(model, tools=tools, system_instruction=SYSTEM_INSTRUCTION)
                chat = model_obj.start_chat()
                full_message = message  # system_instruction already set

            response = chat.send_message(full_message)

            # Handle function calling responses
            while response.candidates and response.candidates[0].content.parts:
                last_part = response.candidates[0].content.parts[-1]

                if not hasattr(last_part, 'function_call') or not last_part.function_call:
                    break

                function_call = last_part.function_call
                function_name = function_call.name
                function_args = function_call.args

                result = execute_tool(user, function_name, dict(function_args))

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
        else:
            # Older google-generativeai (<=0.3.x): no tools/function calling support
            response = chat.send_message(full_message)

        return response.text
    except Exception as e:
        return f"Error: {str(e)}"


def ask_gemini(message, model='claude-3-5-sonnet-20241022', user=None):
    """Legacy wrapper that now calls ask_ai() - supports both Claude and Gemini"""
    return ask_ai(message, model, user)


def ask_ollama(message, model=None, user=None):
    """Call local Ollama API and return response text.
    Uses shared tool definitions from chatbot.tools package.
    Supports tool/function calling for compatible models.
    """
    if not OLLAMA_AVAILABLE:
        return "Error: Ollama library not installed. Run: pip install ollama"

    from chatbot.tools import format_tools_for_ollama, execute_tool, SYSTEM_INSTRUCTION

    model = model or OLLAMA_DEFAULT_MODEL

    try:
        oc = ollama_client.Client(host=OLLAMA_BASE_URL)

        tools = format_tools_for_ollama(user) if user else []
        messages = [{"role": "user", "content": message}]

        # Add system instruction when tools are available
        if tools:
            messages.insert(0, {"role": "system", "content": SYSTEM_INSTRUCTION})

        # Call Ollama with tools
        response = oc.chat(
            model=model,
            messages=messages,
            tools=tools if tools else None
        )

        # Handle tool calls in response
        while response.get('message', {}).get('tool_calls'):
            # Append assistant message with tool calls
            messages.append(response['message'])

            for tool_call in response['message']['tool_calls']:
                func_name = tool_call['function']['name']
                func_args = tool_call['function']['arguments']
                result = execute_tool(user, func_name, func_args)

                # Append tool result
                messages.append({
                    "role": "tool",
                    "content": str(result)
                })

            # Get next response
            response = oc.chat(
                model=model,
                messages=messages,
                tools=tools if tools else None
            )

        return response.get('message', {}).get('content', 'No response generated')

    except Exception as e:
        error_msg = str(e)
        if 'connection' in error_msg.lower() or 'refused' in error_msg.lower():
            return "Error: Cannot connect to Ollama. Make sure Ollama is running (ollama serve)"
        return f"Ollama Error: {error_msg}"


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


# ========== SKILL & FLOW VIEWS (PHASE D) ==========

@login_required
def skills_page(request):
    """Display the 3-panel skills & flows dashboard"""
    return render(request, 'skills.html', {'user': request.user})


@login_required
def flow_run_page(request, execution_id):
    """Display flow execution progress page"""
    from .models import FlowExecution
    execution = get_object_or_404(FlowExecution, id=execution_id, user=request.user)
    return render(request, 'flow_run.html', {
        'execution': execution,
        'flow': execution.flow,
    })


@login_required
def api_skills_list(request):
    """List all skills for the current user"""
    from .models import Skill
    skill_type = request.GET.get('type', 'all')
    qs = Skill.objects.filter(user=request.user)
    if skill_type != 'all':
        qs = qs.filter(skill_type=skill_type)
    skills = list(qs.values(
        'id', 'name', 'description', 'skill_type', 'is_system',
        'version', 'avg_rating', 'total_executions', 'success_rate',
        'created_at', 'updated_at'
    ))
    for s in skills:
        for key in ('created_at', 'updated_at'):
            if s.get(key):
                s[key] = s[key].isoformat()
    return JsonResponse({'skills': skills})


@login_required
def api_skill_create(request):
    """Create a new skill"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=400)
    import json
    from .models import Skill
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        data = request.POST

    skill, created = Skill.objects.get_or_create(
        user=request.user,
        name=data.get('name', ''),
        defaults={
            'description': data.get('description', ''),
            'skill_type': data.get('skill_type', 'generate'),
            'config': data.get('config', {}),
        }
    )
    if not created:
        return JsonResponse({'error': f'Skill "{skill.name}" already exists'}, status=400)
    return JsonResponse({'status': 'created', 'skill_id': skill.id, 'name': skill.name})


@login_required
def api_skill_detail(request, skill_id):
    """Get, update, or delete a skill"""
    from .models import Skill
    skill = get_object_or_404(Skill, id=skill_id, user=request.user)

    if request.method == 'GET':
        return JsonResponse({
            'id': skill.id, 'name': skill.name, 'description': skill.description,
            'skill_type': skill.skill_type, 'config': skill.config,
            'input_schema': skill.input_schema, 'output_schema': skill.output_schema,
            'is_system': skill.is_system, 'version': skill.version,
            'avg_rating': skill.avg_rating, 'total_executions': skill.total_executions,
            'success_rate': skill.success_rate,
        })
    elif request.method == 'POST':
        import json
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            data = request.POST
        if 'description' in data:
            skill.description = data['description']
        if 'config' in data:
            skill.config = data['config']
        if 'skill_type' in data:
            skill.skill_type = data['skill_type']
        skill.save()
        return JsonResponse({'status': 'updated', 'skill_id': skill.id})
    elif request.method == 'DELETE':
        skill.delete()
        return JsonResponse({'status': 'deleted'})
    return JsonResponse({'error': 'Method not allowed'}, status=405)


@login_required
def api_skill_test(request, skill_id):
    """Test-run a skill with sample input"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=400)
    import json
    from .models import Skill
    from chatbot.skills.executor import SkillExecutor

    skill = get_object_or_404(Skill, id=skill_id, user=request.user)
    try:
        input_data = json.loads(request.body)
    except json.JSONDecodeError:
        input_data = {}

    executor = SkillExecutor(request.user)
    try:
        result = executor.execute(skill, input_data)
        return JsonResponse({'status': 'success', 'result': result})
    except Exception as e:
        return JsonResponse({'status': 'error', 'error': str(e)})


@login_required
def api_flows_list(request):
    """List all flows"""
    from .models import Flow
    flows = Flow.objects.filter(user=request.user, is_active=True)
    result = []
    for f in flows:
        steps = list(f.steps.order_by('order').values('order', 'skill__name', 'skill__skill_type'))
        result.append({
            'id': f.id, 'name': f.name, 'description': f.description,
            'step_count': len(steps),
            'steps': [{'order': s['order'], 'skill': s['skill__name'], 'type': s['skill__skill_type']} for s in steps],
            'created_at': f.created_at.isoformat(),
        })
    return JsonResponse({'flows': result})


@login_required
def api_flow_create(request):
    """Create a new flow"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=400)
    import json
    from .models import Flow, FlowStep, Skill
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    flow = Flow.objects.create(
        user=request.user,
        name=data.get('name', 'Untitled Flow'),
        description=data.get('description', ''),
    )
    for i, step_def in enumerate(data.get('steps', [])):
        skill_name = step_def.get('skill_name', step_def.get('skill', ''))
        try:
            skill = Skill.objects.get(user=request.user, name=skill_name)
        except Skill.DoesNotExist:
            continue
        FlowStep.objects.create(
            flow=flow, skill=skill, order=i + 1,
            input_mapping=step_def.get('input_mapping', {}),
            config_override=step_def.get('config_override', {}),
            condition=step_def.get('condition', {}),
        )
    return JsonResponse({'status': 'created', 'flow_id': flow.id, 'name': flow.name})


@login_required
def api_flow_run(request, flow_id):
    """Execute a flow"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=400)
    import json
    from .models import Flow
    from chatbot.skills.flow_engine import FlowEngine

    flow = get_object_or_404(Flow, id=flow_id, user=request.user, is_active=True)
    try:
        context = json.loads(request.body) if request.body else {}
    except json.JSONDecodeError:
        context = {}

    engine = FlowEngine(request.user)
    execution = engine.execute_flow(flow, trigger_context=context)
    return JsonResponse({
        'execution_id': execution.id,
        'status': execution.status,
        'total_steps': execution.total_steps,
        'step_results': execution.step_results,
        'error': execution.error_message or None,
    })


@login_required
def api_flow_execution_detail(request, execution_id):
    """Get execution details (for polling progress)"""
    from .models import FlowExecution
    execution = get_object_or_404(FlowExecution, id=execution_id, user=request.user)
    return JsonResponse({
        'execution_id': execution.id,
        'flow_name': execution.flow.name,
        'status': execution.status,
        'current_step': execution.current_step,
        'total_steps': execution.total_steps,
        'step_results': execution.step_results,
        'started_at': execution.started_at.isoformat(),
        'completed_at': execution.completed_at.isoformat() if execution.completed_at else None,
        'error': execution.error_message or None,
    })


@login_required
def api_skill_logs(request, skill_id):
    """Get execution logs for a skill"""
    from .models import SkillExecutionLog
    logs = SkillExecutionLog.objects.filter(
        skill_id=skill_id, user=request.user
    ).order_by('-executed_at')[:50]
    result = []
    for log in logs:
        entry = {
            'id': log.id,
            'status': log.status,
            'input_data': log.input_data,
            'output_data': log.output_data,
            'duration_ms': log.duration_ms,
            'error_message': log.error_message,
            'model_used': log.model_used,
            'executed_at': log.executed_at.isoformat(),
            'has_feedback': hasattr(log, 'feedback') and log.feedback is not None,
        }
        try:
            fb = log.feedback
            entry['feedback'] = {'rating': fb.rating, 'comment': fb.comment}
        except Exception:
            entry['feedback'] = None
        result.append(entry)
    return JsonResponse({'logs': result})


@login_required
def api_skill_feedback(request):
    """Submit feedback on a skill execution"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=400)
    import json
    from .models import SkillExecutionLog, SkillFeedback
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    try:
        log = SkillExecutionLog.objects.get(id=data.get('execution_log_id'), user=request.user)
    except SkillExecutionLog.DoesNotExist:
        return JsonResponse({'error': 'Log not found'}, status=404)

    feedback, created = SkillFeedback.objects.get_or_create(
        user=request.user, execution_log=log,
        defaults={
            'skill': log.skill,
            'rating': data.get('rating', 3),
            'comment': data.get('comment', ''),
            'expected_output': data.get('expected_output', ''),
        }
    )
    if not created:
        feedback.rating = data.get('rating', feedback.rating)
        feedback.comment = data.get('comment', feedback.comment)
        feedback.save()
    log.skill.update_stats()
    return JsonResponse({'status': 'ok', 'feedback_id': feedback.id})


@login_required
def api_skill_improve(request, skill_id):
    """Get AI-suggested improvements for a skill"""
    from .models import Skill
    from chatbot.skills.improver import SkillImprover
    skill = get_object_or_404(Skill, id=skill_id, user=request.user)
    improver = SkillImprover(request.user)
    result = improver.suggest_improvement(skill)
    return JsonResponse(result)


@login_required
def api_skill_apply_improvement(request, skill_id):
    """Apply an improvement to a skill config"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=400)
    import json
    from .models import Skill
    from chatbot.skills.improver import SkillImprover
    skill = get_object_or_404(Skill, id=skill_id, user=request.user)
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    new_config = data.get('config', {})
    if not new_config:
        return JsonResponse({'error': 'No config provided'}, status=400)
    improver = SkillImprover(request.user)
    result = improver.apply_improvement(skill, new_config)
    return JsonResponse(result)


@login_required
def reports_page(request):
    """Display the reports dashboard"""
    return render(request, 'reports.html', {
        'user': request.user
    })


@login_required
def api_generate_report(request):
    """API endpoint to generate reports on demand"""
    from chatbot.tools.report_builder import ReportBuilder

    report_type = request.GET.get('report_type', 'summary')
    data_type = request.GET.get('data_type', 'tasks')
    time_range = request.GET.get('time_range', 'last_30_days')
    output_format = request.GET.get('format', 'markdown')

    builder = ReportBuilder(request.user)
    result = builder.generate_report(report_type, data_type, time_range, output_format)
    return JsonResponse(result)


@login_required
def api_query_data(request):
    """API endpoint for flexible data queries"""
    import json
    from chatbot.tools.query_engine import execute_query

    data_type = request.GET.get('data_type', 'tasks')
    aggregation = request.GET.get('aggregation', 'none')
    order_by = request.GET.get('order_by', '-created_at')
    limit = int(request.GET.get('limit', 20))

    # Parse filters from JSON query param
    filters_str = request.GET.get('filters', '{}')
    try:
        filters = json.loads(filters_str) if filters_str else {}
    except json.JSONDecodeError:
        filters = {}

    result = execute_query(request.user, data_type, filters=filters,
                          aggregation=aggregation, order_by=order_by, limit=limit)
    return JsonResponse(result)


@login_required
def api_export_report(request):
    """Export report data as CSV"""
    import csv
    from django.http import HttpResponse
    from chatbot.tools.query_engine import execute_query

    data_type = request.GET.get('data_type', 'tasks')
    export_format = request.GET.get('format', 'csv')

    data = execute_query(request.user, data_type, limit=100)
    results = data.get('results', [])

    if export_format == 'csv' and results:
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{data_type}_export.csv"'
        writer = csv.DictWriter(response, fieldnames=results[0].keys())
        writer.writeheader()
        for row in results:
            writer.writerow(row)
        return response

    return JsonResponse(data)


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
        response = ask_ai(message, model, user=request.user, tools_enabled=session.tools_enabled)

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
    session = ChatSession.objects.filter(
        user=request.user, is_active=True
    ).first()
    return render(request, 'settings.html', {
        'user': request.user,
        'tools_enabled': session.tools_enabled if session else True,
    })


@login_required
def api_list_models(request):
    """Fetch available models from all backends (Gemini, Claude, Ollama) with caching"""
    cache_key = 'all_models_list'
    # Allow cache bypass with ?refresh=1 (e.g. after Ollama start/stop)
    if request.GET.get('refresh'):
        cache.delete(cache_key)
    models_data = cache.get(cache_key)

    if not models_data:
        models_data = []

        # Claude models (static list - subscription required)
        models_data.extend([
            {'name': 'claude-3-5-sonnet-20241022', 'display': 'Claude 3.5 Sonnet', 'provider': 'claude'},
            {'name': 'claude-3-opus-20250219', 'display': 'Claude 3 Opus', 'provider': 'claude'},
            {'name': 'claude-3-haiku-20240307', 'display': 'Claude 3 Haiku', 'provider': 'claude'},
        ])

        # Gemini models
        try:
            free_tier_models = [
                'gemini-2.5-pro',
                'gemini-2.5-flash',
                'gemini-2.5-flash-lite',
                'gemini-2.0-flash',
                'gemini-1.5-flash',
            ]

            models = genai.list_models()
            available_models = [m for m in models if 'generateContent' in m.supported_generation_methods]

            gemini_models = [{
                'name': m.name.replace('models/', ''),
                'display': m.display_name,
                'provider': 'gemini'
            } for m in available_models if m.name.replace('models/', '') in free_tier_models]

            if gemini_models:
                models_data.extend(gemini_models)
            else:
                models_data.extend([
                    {'name': 'gemini-2.5-flash', 'display': 'Gemini 2.5 Flash', 'provider': 'gemini'},
                    {'name': 'gemini-2.5-flash-lite', 'display': 'Gemini 2.5 Flash Lite', 'provider': 'gemini'},
                    {'name': 'gemini-2.5-pro', 'display': 'Gemini 2.5 Pro', 'provider': 'gemini'},
                ])
        except Exception:
            models_data.extend([
                {'name': 'gemini-2.5-flash', 'display': 'Gemini 2.5 Flash', 'provider': 'gemini'},
                {'name': 'gemini-2.5-flash-lite', 'display': 'Gemini 2.5 Flash Lite', 'provider': 'gemini'},
                {'name': 'gemini-2.5-pro', 'display': 'Gemini 2.5 Pro', 'provider': 'gemini'},
            ])

        # Ollama models (local)
        ollama_models = get_ollama_models()
        for m in ollama_models:
            models_data.append({
                'name': f'ollama:{m}',
                'display': f'{m}',
                'provider': 'ollama'
            })

        cache.set(cache_key, models_data, timeout=300)  # 5 min cache (Ollama models can change)

    return JsonResponse({'models': models_data})


@login_required
def api_ollama_status(request):
    """Check if Ollama is running and return available models"""
    if not OLLAMA_AVAILABLE:
        return JsonResponse({
            'status': 'unavailable',
            'message': 'Ollama library not installed',
            'models': []
        })

    try:
        # Test connection directly (get_ollama_models swallows exceptions)
        oc = ollama_client.Client(host=OLLAMA_BASE_URL)
        response = oc.list()
        ollama_models = [m.get('name', m.get('model', '')) for m in response.get('models', [])]

        if ollama_models:
            return JsonResponse({
                'status': 'connected',
                'base_url': OLLAMA_BASE_URL,
                'models': ollama_models
            })
        else:
            return JsonResponse({
                'status': 'connected',
                'base_url': OLLAMA_BASE_URL,
                'models': [],
                'message': 'No models installed. Run: ollama pull llama3.2'
            })
    except Exception as e:
        return JsonResponse({
            'status': 'disconnected',
            'message': str(e),
            'models': []
        })


@login_required
def api_ollama_start(request):
    """Start the local Ollama server process."""
    import subprocess, shutil, time

    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=400)

    if not OLLAMA_AVAILABLE:
        return JsonResponse({'error': 'Ollama library not installed.'}, status=400)

    # Check if already running
    try:
        oc = ollama_client.Client(host=OLLAMA_BASE_URL)
        oc.list()
        return JsonResponse({'status': 'already_running', 'message': 'Ollama is already running.'})
    except Exception:
        pass

    # On Windows, try starting the service first
    if os.name == 'nt':
        svc = subprocess.run(['net', 'start', 'OllamaService'], capture_output=True, timeout=10)
        if svc.returncode == 0:
            time.sleep(2)
            try:
                oc = ollama_client.Client(host=OLLAMA_BASE_URL)
                oc.list()
                return JsonResponse({'status': 'started', 'message': 'Ollama service started successfully.'})
            except Exception:
                pass

    # Fallback: start ollama serve directly
    ollama_path = shutil.which('ollama')
    if not ollama_path:
        return JsonResponse({
            'error': 'Ollama executable not found on PATH. Install from ollama.com',
        }, status=400)

    try:
        subprocess.Popen(
            [ollama_path, 'serve'],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0) | getattr(subprocess, 'DETACHED_PROCESS', 0),
        )
        time.sleep(2)

        # Verify it started
        try:
            oc = ollama_client.Client(host=OLLAMA_BASE_URL)
            oc.list()
            return JsonResponse({'status': 'started', 'message': 'Ollama server started successfully.'})
        except Exception:
            return JsonResponse({'status': 'starting', 'message': 'Ollama is starting up, please refresh in a few seconds.'})
    except Exception as e:
        return JsonResponse({'error': f'Failed to start Ollama: {str(e)}'}, status=500)


@login_required
def api_ollama_stop(request):
    """Stop the local Ollama server process."""
    import subprocess, shutil, time

    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=400)

    # Check if it's actually running using ollama client (consistent with status endpoint)
    if OLLAMA_AVAILABLE:
        try:
            oc = ollama_client.Client(host=OLLAMA_BASE_URL)
            oc.list()
        except Exception:
            return JsonResponse({'status': 'already_stopped', 'message': 'Ollama is not running.'})
    else:
        return JsonResponse({'error': 'Ollama library not installed.'}, status=400)

    try:
        if os.name == 'nt':
            # Stop the Windows service first (prevents auto-restart)
            subprocess.run(['net', 'stop', 'OllamaService'], capture_output=True, timeout=10)
            subprocess.run(['sc', 'stop', 'ollama'], capture_output=True, timeout=5)
            time.sleep(0.5)
            # Then kill any remaining processes
            subprocess.run(['taskkill', '/f', '/im', 'ollama.exe'], capture_output=True, timeout=5)
            subprocess.run(['taskkill', '/f', '/im', 'ollama_llama_server.exe'], capture_output=True, timeout=5)
            subprocess.run(['taskkill', '/f', '/im', 'ollama app.exe'], capture_output=True, timeout=5)
        else:
            subprocess.run(['systemctl', 'stop', 'ollama'], capture_output=True, timeout=5)
            subprocess.run(['pkill', '-f', 'ollama'], capture_output=True, timeout=5)

        time.sleep(1.5)

        # Verify it stopped
        try:
            oc = ollama_client.Client(host=OLLAMA_BASE_URL)
            oc.list()
            return JsonResponse({
                'status': 'error',
                'message': 'Ollama is still running. It may be managed by a system service. Try stopping it manually from the system tray.'
            }, status=500)
        except Exception:
            return JsonResponse({'status': 'stopped', 'message': 'Ollama server stopped.'})
    except Exception as e:
        return JsonResponse({'error': f'Failed to stop Ollama: {str(e)}'}, status=500)


@login_required
def api_save_ollama_config(request):
    """Test and save a new Ollama connection URL.

    POST body: { "base_url": "http://host:11434" }
    - Validates the URL format
    - Tests the connection by calling list()
    - On success, updates the in-memory OLLAMA_BASE_URL for this process
      and persists it to .env so it survives restarts
    """
    import re
    import chatbot.views as _self   # reference to this module's globals

    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=400)

    if not OLLAMA_AVAILABLE:
        return JsonResponse({'error': 'Ollama library not installed. Run: pip install ollama'}, status=400)

    import json
    try:
        body = json.loads(request.body)
        new_url = body.get('base_url', '').strip().rstrip('/')
    except (json.JSONDecodeError, AttributeError):
        return JsonResponse({'error': 'Invalid JSON body'}, status=400)

    if not new_url:
        return JsonResponse({'error': 'base_url is required'}, status=400)

    # Basic URL validation
    if not re.match(r'^https?://.+', new_url):
        return JsonResponse({'error': 'base_url must start with http:// or https://'}, status=400)

    # Test the connection
    try:
        oc = ollama_client.Client(host=new_url)
        response = oc.list()
        models = [m.get('name', m.get('model', '')) for m in response.get('models', [])]
    except Exception as e:
        return JsonResponse({
            'error': f'Cannot connect to Ollama at {new_url}: {str(e)}',
            'tip': 'Make sure Ollama is running (ollama serve) and the URL is reachable.'
        }, status=400)

    # Connection succeeded — update in-memory global for this process
    _self.OLLAMA_BASE_URL = new_url

    # Persist to .env so it survives server restarts
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
    try:
        if os.path.exists(env_path):
            with open(env_path, 'r') as f:
                env_content = f.read()
            if 'OLLAMA_BASE_URL' in env_content:
                import re as _re
                env_content = _re.sub(
                    r'^OLLAMA_BASE_URL\s*=.*$',
                    f'OLLAMA_BASE_URL = {new_url}',
                    env_content,
                    flags=_re.MULTILINE
                )
            else:
                env_content += f'\nOLLAMA_BASE_URL = {new_url}\n'
            with open(env_path, 'w') as f:
                f.write(env_content)
    except Exception:
        pass  # .env update is best-effort, connection is already working

    return JsonResponse({
        'success': True,
        'base_url': new_url,
        'models': models,
        'message': f'Connected to Ollama at {new_url}. {len(models)} model(s) found.'
    })


@login_required
def api_save_settings(request):
    """Save user model preference"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=400)

    model_name = request.POST.get('model')

    if not model_name:
        return JsonResponse({'error': 'Model name required'}, status=400)

    # Validate model - support Claude, Gemini, and Ollama
    valid_models = [
        # Claude models
        'claude-3-5-sonnet-20241022',
        'claude-3-opus-20250219',
        'claude-3-haiku-20240307',
        # Gemini models (free tier)
        'gemini-2.5-pro',
        'gemini-2.5-flash',
        'gemini-2.5-flash-lite',
        'gemini-2.0-flash',
        'gemini-1.5-flash',
        'gemini-1.5-pro',
        'gemini-pro',
    ]

    # Also accept any ollama: prefixed model
    is_ollama_model = model_name.startswith('ollama:')
    if model_name not in valid_models and not is_ollama_model:
        return JsonResponse({'error': f'Invalid model: {model_name}'}, status=400)

    # Get or create current session and update model
    session = ChatSession.objects.filter(
        user=request.user,
        is_active=True
    ).first()

    # Handle tools_enabled toggle
    tools_enabled = request.POST.get('tools_enabled')

    if session:
        session.model = model_name
        if tools_enabled is not None:
            session.tools_enabled = tools_enabled.lower() in ('true', '1', 'on')
        session.save()

    return JsonResponse({'success': True, 'message': 'Settings saved'})


@login_required
def api_toggle_tools(request):
    """Toggle AI tools (function calling) on/off"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=400)

    import json
    try:
        data = json.loads(request.body)
        enabled = data.get('enabled', True)
    except (json.JSONDecodeError, AttributeError):
        enabled = request.POST.get('enabled', 'true').lower() in ('true', '1', 'on')

    # Update all active sessions for this user
    sessions = ChatSession.objects.filter(user=request.user, is_active=True)
    sessions.update(tools_enabled=enabled)

    return JsonResponse({
        'success': True,
        'tools_enabled': enabled,
        'message': f'AI tools {"enabled" if enabled else "disabled"}'
    })


@login_required
def api_tools_status(request):
    """Get current tools enabled/disabled status"""
    session = ChatSession.objects.filter(
        user=request.user, is_active=True
    ).first()
    enabled = session.tools_enabled if session else True
    return JsonResponse({'tools_enabled': enabled})


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


# ========== CLAUDE TERMINAL VIEWS (PHASE 1) ==========

@login_required
def claude_terminal(request):
    """Display Claude terminal management page"""
    user = request.user

    try:
        # Get or create terminal session for current user
        terminal_session, created = ClaudeTerminalSession.objects.get_or_create(
            user=user,
            defaults={
                'connection_method': 'http',
                'connection_config': {'port': 5000}
            }
        )
    except Exception as e:
        terminal_session = None
        error = str(e)

    # Get list of chat sessions for linking
    chat_sessions = ChatSession.objects.filter(user=user).order_by('-created_at')[:10]

    context = {
        'terminal_session': terminal_session,
        'chat_sessions': chat_sessions,
    }

    return render(request, 'claude_terminal.html', context)


@login_required
def api_terminal_start(request):
    """API endpoint to start Claude terminal process"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST required'}, status=400)

    user = request.user

    try:
        terminal_session = ClaudeTerminalSession.objects.get(user=user)
    except ClaudeTerminalSession.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Terminal session not found'}, status=404)

    try:
        # Import here to avoid circular imports
        from .claude_terminal import get_connector

        # Get connection method from request or use default
        connection_method = request.POST.get('connection_method', 'http')

        # Validate connection method
        valid_methods = ['http', 'ipc', 'file']
        if connection_method not in valid_methods:
            return JsonResponse({'success': False, 'error': f'Invalid method: {connection_method}'}, status=400)

        # Get connection config
        config_port = request.POST.get('port', '5000')
        connection_config = {
            'port': int(config_port) if connection_method == 'http' else None
        }

        # Try to connect using the connector
        connector = get_connector(
            config={connection_method: connection_config},
            timeout=10
        )

        if connector.connect():
            # Update terminal session
            terminal_session.is_active = True
            terminal_session.is_enabled = True
            terminal_session.connection_method = connection_method
            terminal_session.connection_config = connection_config
            terminal_session.started_at = timezone.now()
            terminal_session.last_message_at = timezone.now()
            terminal_session.clear_error()
            terminal_session.save()

            return JsonResponse({
                'success': True,
                'message': f'Connected via {connection_method}',
                'method': connector.get_method(),
                'is_active': True,
            })
        else:
            return JsonResponse({
                'success': False,
                'error': f'Failed to connect via {connection_method}. Is Claude terminal running?'
            }, status=503)

    except Exception as e:
        logger.error(f'Terminal start error: {e}')
        return JsonResponse({'success': False, 'error': f'Error: {str(e)}'}, status=500)


@login_required
def api_terminal_stop(request):
    """API endpoint to stop Claude terminal process"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST required'}, status=400)

    user = request.user

    try:
        terminal_session = ClaudeTerminalSession.objects.get(user=user)
    except ClaudeTerminalSession.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Terminal session not found'}, status=404)

    try:
        # Stop the terminal
        terminal_session.is_active = False
        terminal_session.is_enabled = False
        terminal_session.save()

        return JsonResponse({
            'success': True,
            'message': 'Terminal stopped',
            'is_active': False,
        })

    except Exception as e:
        logger.error(f'Terminal stop error: {e}')
        return JsonResponse({'success': False, 'error': f'Error: {str(e)}'}, status=500)


@login_required
def api_terminal_status(request):
    """API endpoint to check Claude terminal status"""
    user = request.user

    try:
        terminal_session = ClaudeTerminalSession.objects.get(user=user)
    except ClaudeTerminalSession.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Terminal session not found'
        }, status=404)

    try:
        # Import connector
        from .claude_terminal import get_connector

        # Check if terminal is healthy
        connector = get_connector(
            config={terminal_session.connection_method: terminal_session.connection_config},
            timeout=5
        )

        is_healthy = connector.is_healthy() if terminal_session.is_active else False

        uptime = None
        if terminal_session.started_at:
            uptime = int((timezone.now() - terminal_session.started_at).total_seconds())

        return JsonResponse({
            'success': True,
            'is_active': terminal_session.is_active,
            'is_enabled': terminal_session.is_enabled,
            'is_healthy': is_healthy,
            'is_connected': terminal_session.is_connected,
            'connection_method': terminal_session.connection_method,
            'uptime_seconds': uptime,
            'last_error': terminal_session.last_error,
            'error_count': terminal_session.error_count,
        })

    except Exception as e:
        logger.error(f'Terminal status check error: {e}')
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
def api_terminal_message(request):
    """API endpoint to send message to Claude terminal and get response"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST required'}, status=400)

    user = request.user
    message = request.POST.get('message', '').strip()
    session_id = request.POST.get('session_id', None)

    if not message:
        return JsonResponse({'success': False, 'error': 'Message required'}, status=400)

    try:
        terminal_session = ClaudeTerminalSession.objects.get(user=user)
    except ClaudeTerminalSession.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Terminal session not found'}, status=404)

    if not terminal_session.is_active:
        return JsonResponse({
            'success': False,
            'error': 'Terminal is not active. Start it first.'
        }, status=503)

    try:
        # Import connector
        from .claude_terminal import get_connector

        # Create connector
        connector = get_connector(
            config={terminal_session.connection_method: terminal_session.connection_config},
            timeout=30
        )

        # Try to send message
        response_text = connector.send_message(message, session_id)

        if response_text is None:
            terminal_session.mark_error('Failed to get response from terminal')
            return JsonResponse({
                'success': False,
                'error': 'No response from terminal'
            }, status=503)

        # Update last message time
        terminal_session.last_message_at = timezone.now()
        terminal_session.clear_error()
        terminal_session.save()

        return JsonResponse({
            'success': True,
            'response': response_text,
            'method': terminal_session.connection_method,
        })

    except Exception as e:
        logger.error(f'Terminal message error: {e}')
        terminal_session.mark_error(str(e))

        return JsonResponse({
            'success': False,
            'error': f'Error: {str(e)}'
        }, status=500)


# Import logging at module level if not already imported
import logging
logger = logging.getLogger(__name__)