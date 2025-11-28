import os
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.core.cache import cache

from django.contrib import auth
from django.contrib.auth.models import User
from .models import Chat, ChatSession, Task
from .message_queue import message_processor

from django.utils import timezone
from django.contrib.auth.decorators import login_required
from dotenv import load_dotenv
load_dotenv()

import google.generativeai as genai

# Load environment variables from .env file
API_SECRET_KEY = os.getenv('API_SECRET_KEY')

genai.configure(api_key=API_SECRET_KEY)


def ask_gemini(message, model='gemini-2.0-flash', user=None):
    """Call Gemini API and return response text

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
                """Create a new task for the user"""
                return create_task(user, title, description, priority, due_date_str)

            def list_tasks_tool(status: str = 'all', limit: int = 10):
                """List user's tasks filtered by status (all, pending, in_progress, completed, cancelled)"""
                return list_my_tasks(user, status, limit)

            def get_task_details_tool(task_id: int):
                """Get detailed information about a specific task"""
                return get_task_details(user, task_id)

            def update_task_status_tool(task_id: int, status: str):
                """Update task status (pending, in_progress, completed, cancelled)"""
                return update_task_status(user, task_id, status)

            def update_task_priority_tool(task_id: int, priority: str):
                """Update task priority (low, medium, high, urgent)"""
                return update_task_priority(user, task_id, priority)

            def delete_task_tool(task_id: int):
                """Delete a task"""
                return delete_task(user, task_id)

            def get_pending_tasks_tool(limit: int = 5):
                """Get urgent and high priority pending tasks"""
                return get_pending_tasks(user, limit)

            def get_task_summary_tool():
                """Get summary of all tasks by status"""
                return get_task_summary(user)

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
                get_task_summary_tool
            ]

        # Create model with tools if user is provided
        if tools:
            model_obj = genai.GenerativeModel(model, tools=tools)
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
    """Get summary of all tasks by status"""
    try:
        return {
            'total_tasks': Task.objects.filter(user=user).count(),
            'pending': Task.objects.filter(user=user, status='pending').count(),
            'in_progress': Task.objects.filter(user=user, status='in_progress').count(),
            'completed': Task.objects.filter(user=user, status='completed').count(),
            'cancelled': Task.objects.filter(user=user, status='cancelled').count(),
            'overdue': sum(1 for t in Task.objects.filter(user=user, status__in=['pending', 'in_progress']) if t.is_overdue())
        }
    except Exception as e:
        return {'error': str(e)}

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
        response = ask_gemini(message, session.model, user=request.user)

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
    model = request.POST.get('model', 'gemini-2.0-flash')

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

    # Validate model exists
    try:
        genai.GenerativeModel(model_name)
    except Exception as e:
        return JsonResponse({'error': f'Invalid model: {str(e)}'}, status=400)

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