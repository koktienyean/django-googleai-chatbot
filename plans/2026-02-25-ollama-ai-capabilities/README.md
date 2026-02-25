# Plan: Ollama Integration + AI Capabilities Enhancement

**Date**: 2026-02-25
**Status**: Planning
**Scope**: 3 features across multiple phases

## Overview

Integrate Ollama as a local LLM backend alongside existing Claude/Gemini APIs, then extend the AI chatbot with two major capabilities:
1. **Data Query & Reporting** - AI can query Django data and generate structured reports
2. **Skill & Flow Engine** - Define reusable AI skills and chain them into sequential workflows

## Plan Documents

| # | Document | Feature | Status |
|---|----------|---------|--------|
| 1 | [01-ollama-integration.md](01-ollama-integration.md) | Ollama as local LLM backend | Planning |
| 2 | [02-data-query-reporting.md](02-data-query-reporting.md) | AI data query & report generation | Planning |
| 3 | [03-skill-flow-engine.md](03-skill-flow-engine.md) | Skill definition & sequential flow execution | Planning |

## Current Architecture (Summary)

```
chatbot/views.py  ->  ask_ai()  ->  routes by model prefix
                                     ├── claude-*  -> ask_claude()   (Anthropic API)
                                     └── gemini-*  -> ask_gemini_api() (Google GenAI)

Both APIs support function calling (tool use) for:
- Chat history search/query
- Task CRUD operations
- Recurring tasks, notifications
- Analytics/productivity metrics
```

**Key files**:
- `chatbot/views.py` (84KB) - All views + AI integration + tool functions
- `chatbot/models.py` - Chat, ChatSession, Task, Notification, Analytics models
- `chatbot/urls.py` - API endpoints
- `django_chatbot/settings.py` - Django config (SQLite, single chatbot app)

## Dependencies

- Current: Django 4.2.3, anthropic, google-generativeai, markdown
- New: `ollama` Python library (or raw HTTP to Ollama API)
