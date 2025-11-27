import os
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.core.cache import cache

from django.contrib import auth
from django.contrib.auth.models import User
from .models import Chat, ChatSession
from .message_queue import message_processor

from django.utils import timezone
from django.contrib.auth.decorators import login_required
from dotenv import load_dotenv
load_dotenv()

import google.generativeai as genai

# Load environment variables from .env file
API_SECRET_KEY = os.getenv('API_SECRET_KEY')

genai.configure(api_key=API_SECRET_KEY)


def ask_gemini(message, model='gemini-1.5-flash'):
    """Call Gemini API and return response text"""
    try:
        model_obj = genai.GenerativeModel(model)
        chat = model_obj.start_chat()
        response = chat.send_message(message)
        return response.text
    except Exception as e:
        return f"Error: {str(e)}"


def ask_openai(request, message, model='gemini-1.5-flash'):
    """Legacy function for backward compatibility"""
    text = request.POST.get("message")
    return ask_gemini(text, model)

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
        response = ask_gemini(message, session.model)

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
    sessions = ChatSession.objects.filter(user=request.user, is_active=True)
    return JsonResponse({
        'sessions': [{
            'id': s.id,
            'name': s.name,
            'model': s.model,
            'message_count': s.messages.count(),
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
    model = request.POST.get('model', 'gemini-1.5-flash')

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
    """Fetch available Gemini models with caching"""
    cache_key = 'gemini_models_list'
    models_data = cache.get(cache_key)

    if not models_data:
        try:
            models = genai.list_models()
            # Filter for generateContent capable models
            models = [m for m in models if 'generateContent' in m.supported_generation_methods]
            models_data = [{
                'name': m.name.replace('models/', ''),
                'display': m.display_name
            } for m in models]
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
            return redirect('chatbot')
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
                return redirect('chatbot')
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