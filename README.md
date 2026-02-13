# Django Gemini Chatbot

A Django chatbot with Google Gemini AI integration, multi-session support, task management, calendar view, and a dark terminal UI.

## Quick Start

```bash
pip install -r requirements.txt
cp .env.example .env  # Add your API_SECRET_KEY
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## Features

- Multi-session chat with Gemini AI (function calling for data queries)
- Task management via natural language (create, list, update, delete tasks)
- Calendar view with FullCalendar.js (drag-to-reschedule)
- Async message processing (non-blocking)
- Dark terminal aesthetic with glass morphism UI
- Django admin with custom interfaces for all 9 models

## Project Status

See [PROJECT_STATUS.md](PROJECT_STATUS.md) for what's built, what's missing, and suggested next steps.

## Documentation

- [docs/](docs/) - Guides, references, testing docs
- [plans/](plans/) - Implementation plans and feature analysis
- [docs/status/](docs/status/) - Archived phase completion summaries
