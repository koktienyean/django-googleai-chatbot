# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Django-based chatbot application that integrates with Google's Generative AI (Gemini) API. The application provides user authentication and a chat interface where users can interact with the Gemini AI model.

## Architecture

- **Django Project**: `django_chatbot/` - Main Django project directory
- **Chatbot App**: `chatbot/` - Single Django app containing all chatbot functionality
- **Database**: SQLite (`db.sqlite3`) - Default development database
- **Templates**: `templates/` - HTML templates for all views
- **Static Files**: `images/` - Contains demo screenshots and admin interface images

### Key Components

- **Models**: `chatbot/models.py` - Single `Chat` model that stores user messages, AI responses, and timestamps
- **Views**: `chatbot/views.py` - Contains authentication views and main chatbot functionality using Google Generative AI
- **AI Integration**: Uses `google.generativeai` library with Gemini Pro model instead of OpenAI

## Development Commands

### Environment Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Apply database migrations
python manage.py migrate

# Create superuser for admin
python manage.py createsuperuser

# Run development server
python manage.py runserver
```

### Environment Configuration
- Create `.env` file with `API_SECRET_KEY` for Google Generative AI
- The application uses `python-dotenv` to load environment variables

### Database Operations
```bash
# Create migrations after model changes
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Access Django shell
python manage.py shell
```

## Key Technical Details

### AI Integration
- Originally designed for OpenAI (commented out code remains)
- Currently uses Google Generative AI with `gemini-pro` model
- API key stored in environment variable `API_SECRET_KEY`
- Chat responses are processed through markdown rendering

### Authentication Flow
- Custom login/register views in `chatbot/views.py`
- Uses Django's built-in authentication system
- Login required for chatbot access (`LOGIN_URL = '/login/'`)
- User sessions maintain chat history

### URL Structure
- Root URL (`/`) → Chatbot interface
- `/login/` → User login
- `/register/` → User registration  
- `/logout/` → User logout
- `/admin/` → Django admin interface

### Frontend Integration
- AJAX-based chat interface
- Markdown rendering for AI responses using `markdown` library
- Bootstrap-based responsive design (templates use base template structure)

## Dependencies
- Django 4.2.3
- google-generativeai (Gemini API)
- python-dotenv (environment variables)
- markdown (response formatting)
- OpenAI library present but unused (legacy code)