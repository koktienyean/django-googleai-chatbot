# Implementation Tasks - Ollama + AI Capabilities

**Date**: 2026-02-25
**Based on**: Plans 01, 02, 03

---

## Structure Overview: What Changes Where

### Current File Structure
```
django-googleai-chatbot/
├── chatbot/
│   ├── __init__.py
│   ├── admin.py              (633 lines - 9 model admins registered)
│   ├── apps.py
│   ├── claude_terminal.py
│   ├── message_queue.py
│   ├── models.py             (384 lines - 8 models)
│   ├── tests.py              (empty)
│   ├── urls.py               (55 lines - 30 URL patterns)
│   └── views.py              (2151 lines - 57 functions, needs refactor!)
├── django_chatbot/
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── templates/
│   ├── base.html             (base layout, Bootstrap 4, dark theme)
│   ├── chatbot.html          (main chat UI, sidebar, model selector)
│   ├── settings.html         (model selection, save/test)
│   ├── calendar.html         (FullCalendar, task CRUD)
│   ├── claude_terminal.html  (terminal session mgmt)
│   ├── login.html
│   └── register.html
├── requirements.txt
└── .env
```

### Target File Structure (After All Tasks)
```
django-googleai-chatbot/
├── chatbot/
│   ├── __init__.py
│   ├── admin.py              ENHANCE  (+4 model admins: Skill, Flow, FlowStep, FlowExecution)
│   ├── apps.py
│   ├── claude_terminal.py
│   ├── message_queue.py
│   ├── models.py             ENHANCE  (+4 models: Skill, Flow, FlowStep, FlowExecution)
│   ├── urls.py               ENHANCE  (+12 new URL patterns)
│   ├── views.py              REFACTOR (extract tools, add Ollama, add new views)
│   ├── tools/                NEW PACKAGE (extracted from views.py)
│   │   ├── __init__.py       NEW
│   │   ├── definitions.py    NEW  (shared tool schemas)
│   │   ├── executors.py      NEW  (tool function dispatch)
│   │   ├── formatters.py     NEW  (Claude/Gemini/Ollama format converters)
│   │   ├── query_engine.py   NEW  (flexible data query)
│   │   └── report_builder.py NEW  (report generation)
│   ├── skills/               NEW PACKAGE
│   │   ├── __init__.py       NEW
│   │   ├── builtin_skills.py NEW  (9 system-provided skills)
│   │   ├── executor.py       NEW  (skill executor)
│   │   └── flow_engine.py    NEW  (flow executor)
│   ├── management/           NEW
│   │   └── commands/
│   │       ├── __init__.py   NEW
│   │       ├── setup_builtin_skills.py  NEW  (management command)
│   │       └── run_scheduled_flows.py   NEW  (optional, Phase 4)
│   └── migrations/           AUTO-GENERATED
├── templates/
│   ├── base.html             (no change)
│   ├── chatbot.html          ENHANCE  (model selector adds Ollama group)
│   ├── settings.html         ENHANCE  (Ollama section, connection test)
│   ├── calendar.html         (no change)
│   ├── claude_terminal.html  (no change)
│   ├── login.html            (no change)
│   ├── register.html         (no change)
│   ├── reports.html          NEW  (report viewer page)
│   ├── skills.html           NEW  (skill/flow management page)
│   └── flow_run.html         NEW  (flow execution progress page)
├── requirements.txt          ENHANCE  (+ollama)
└── .env                      ENHANCE  (+OLLAMA_BASE_URL, OLLAMA_DEFAULT_MODEL)
```

---

## File Change Summary Table

| File | Action | What Changes | Plan |
|------|--------|-------------|------|
| `requirements.txt` | EDIT | Add `ollama>=0.4.0` | 01 |
| `.env` | EDIT | Add `OLLAMA_BASE_URL`, `OLLAMA_DEFAULT_MODEL` | 01 |
| `chatbot/views.py` | REFACTOR | Extract tools to `chatbot/tools/`, add `ask_ollama()`, update `ask_ai()` router, update `api_list_models()`, add 8 new view functions | 01,02,03 |
| `chatbot/models.py` | ENHANCE | Add 4 new models: `Skill`, `Flow`, `FlowStep`, `FlowExecution` | 03 |
| `chatbot/urls.py` | ENHANCE | Add ~12 new URL patterns for Ollama, reports, skills, flows | 01,02,03 |
| `chatbot/admin.py` | ENHANCE | Register 4 new models with admin classes | 03 |
| `chatbot/tools/__init__.py` | NEW | Package init | 01 |
| `chatbot/tools/definitions.py` | NEW | All tool schemas (API-agnostic), ~20 tools | 01 |
| `chatbot/tools/executors.py` | NEW | Tool dispatch - routes tool name to function | 01 |
| `chatbot/tools/formatters.py` | NEW | Convert schemas to Claude/Gemini/Ollama formats | 01 |
| `chatbot/tools/query_engine.py` | NEW | Flexible query executor with filters & aggregation | 02 |
| `chatbot/tools/report_builder.py` | NEW | ReportBuilder class for formatted reports | 02 |
| `chatbot/skills/__init__.py` | NEW | Package init | 03 |
| `chatbot/skills/builtin_skills.py` | NEW | 9 system-provided skill definitions | 03 |
| `chatbot/skills/executor.py` | NEW | SkillExecutor class | 03 |
| `chatbot/skills/flow_engine.py` | NEW | FlowEngine class | 03 |
| `chatbot/management/commands/setup_builtin_skills.py` | NEW | Management command to seed built-in skills | 03 |
| `templates/chatbot.html` | ENHANCE | Add Ollama model group in dropdown, add "run flow" quick action | 01,03 |
| `templates/settings.html` | ENHANCE | Add Ollama config section, connection test button | 01 |
| `templates/reports.html` | NEW | Report viewer with tables/charts | 02 |
| `templates/skills.html` | NEW | Skill & flow management UI | 03 |
| `templates/flow_run.html` | NEW | Flow execution progress display | 03 |

---

## Page Summary: New vs Enhanced

### NEW Pages (3 new templates)

| Page | URL | Template | Purpose |
|------|-----|----------|---------|
| Reports | `/reports/` | `reports.html` | View generated reports with tables, charts, export buttons |
| Skills & Flows | `/skills/` | `skills.html` | List/create/edit skills and flows, visual flow builder |
| Flow Execution | `/flows/<id>/run/` | `flow_run.html` | Real-time flow execution progress with step-by-step output |

### ENHANCED Pages (2 existing templates)

| Page | Template | What Changes |
|------|----------|-------------|
| Chat | `chatbot.html` | Model selector dropdown: add "Ollama (Local)" optgroup with dynamic models. Add "Run Flow" button in sidebar if user has flows. |
| Settings | `settings.html` | Add "Ollama Configuration" card: base URL input, test connection button, model pull interface, status indicator (connected/disconnected). |

### UNCHANGED Pages (5 templates)

| Page | Template | Why No Change |
|------|----------|---------------|
| Base layout | `base.html` | No structural changes needed |
| Calendar | `calendar.html` | Task calendar unaffected |
| Claude Terminal | `claude_terminal.html` | Separate feature |
| Login | `login.html` | Auth unaffected |
| Register | `register.html` | Auth unaffected |

---

## New URL Patterns (+12)

```python
# Plan 01: Ollama
path('api/ollama/status/', views.api_ollama_status, name='api_ollama_status'),
path('api/ollama/models/', views.api_ollama_models, name='api_ollama_models'),

# Plan 02: Reports
path('reports/', views.reports_page, name='reports_page'),
path('api/reports/generate/', views.api_generate_report, name='api_generate_report'),
path('api/reports/export/', views.api_export_report, name='api_export_report'),
path('api/query/', views.api_query_data, name='api_query_data'),

# Plan 03: Skills & Flows
path('skills/', views.skills_page, name='skills_page'),
path('api/skills/', views.api_skills_list, name='api_skills_list'),
path('api/skills/create/', views.api_skill_create, name='api_skill_create'),
path('api/flows/', views.api_flows_list, name='api_flows_list'),
path('api/flows/create/', views.api_flow_create, name='api_flow_create'),
path('api/flows/<int:flow_id>/run/', views.api_flow_run, name='api_flow_run'),
```

---

## New Django Models (+4)

| Model | Fields | Related To | Purpose |
|-------|--------|-----------|---------|
| `Skill` | name, description, skill_type, config (JSON), input_schema (JSON), output_schema (JSON), is_system | User | Reusable AI action definition |
| `Flow` | name, description, is_active, trigger (JSON) | User | Sequential pipeline of skills |
| `FlowStep` | order, input_mapping (JSON), config_override (JSON), condition (JSON) | Flow, Skill | Single step in a flow |
| `FlowExecution` | status, current_step, total_steps, step_results (JSON), triggered_by, error_message | Flow, User, ChatSession | Tracks one execution run |

---

## New View Functions (+8)

| View Function | Method | Returns | URL | Plan |
|---------------|--------|---------|-----|------|
| `api_ollama_status` | GET | JsonResponse | `/api/ollama/status/` | 01 |
| `api_ollama_models` | GET | JsonResponse | `/api/ollama/models/` | 01 |
| `reports_page` | GET | render template | `/reports/` | 02 |
| `api_generate_report` | POST | JsonResponse | `/api/reports/generate/` | 02 |
| `api_export_report` | GET | FileResponse | `/api/reports/export/` | 02 |
| `api_query_data` | POST | JsonResponse | `/api/query/` | 02 |
| `skills_page` | GET | render template | `/skills/` | 03 |
| `api_skills_list` | GET | JsonResponse | `/api/skills/` | 03 |
| `api_skill_create` | POST | JsonResponse | `/api/skills/create/` | 03 |
| `api_flows_list` | GET | JsonResponse | `/api/flows/` | 03 |
| `api_flow_create` | POST | JsonResponse | `/api/flows/create/` | 03 |
| `api_flow_run` | POST | JsonResponse | `/api/flows/<id>/run/` | 03 |

---

## Setup Changes (How to Use)

### Step 1: Install Ollama (one-time, outside Django)
```bash
# Download from https://ollama.com
# Then pull a model:
ollama pull llama3.2
```

### Step 2: Update .env
```env
# Existing
API_SECRET_KEY=your-google-ai-key
ANTHROPIC_API_KEY=your-anthropic-key

# New
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_DEFAULT_MODEL=llama3.2
```

### Step 3: Install new dependencies
```bash
pip install ollama>=0.4.0
pip freeze > requirements.txt
```

### Step 4: Run migrations (for Skill, Flow, FlowStep, FlowExecution models)
```bash
python manage.py makemigrations chatbot
python manage.py migrate
```

### Step 5: Seed built-in skills
```bash
python manage.py setup_builtin_skills
```

### Step 6: Run server
```bash
python manage.py runserver
```

---

## Implementation Task List (Ordered)

### PHASE A: Tool Refactor (prerequisite for everything)
> Extract the duplicated tool code from the 2151-line views.py into a clean package

| # | Task | Files | Est. Lines |
|---|------|-------|-----------|
| A1 | Create `chatbot/tools/__init__.py` | NEW | 5 |
| A2 | Create `chatbot/tools/definitions.py` - extract all 20 tool schemas from `ask_claude()` (lines 69-301) into API-agnostic format | NEW (from views.py) | ~250 |
| A3 | Create `chatbot/tools/executors.py` - extract tool dispatch logic from `ask_claude()` (lines 348-396) into shared `execute_tool(user, name, args)` | NEW (from views.py) | ~80 |
| A4 | Create `chatbot/tools/formatters.py` - functions to convert tool schemas to Claude format, Gemini format, Ollama format | NEW | ~120 |
| A5 | Refactor `ask_claude()` in views.py to use `chatbot/tools/` instead of inline definitions | EDIT views.py | net -400 |
| A6 | Refactor `ask_gemini_api()` in views.py to use `chatbot/tools/` instead of inline definitions | EDIT views.py | net -250 |

### PHASE B: Ollama Integration (Plan 01)

| # | Task | Files | Est. Lines |
|---|------|-------|-----------|
| B1 | Add `ollama>=0.4.0` to requirements.txt | EDIT | 1 |
| B2 | Add env vars to `.env` | EDIT | 2 |
| B3 | Add `ask_ollama()` function in views.py | EDIT views.py | ~60 |
| B4 | Update `ask_ai()` router to detect Ollama models | EDIT views.py | ~10 |
| B5 | Add `get_ollama_models()` helper | EDIT views.py | ~15 |
| B6 | Update `api_list_models()` to include Ollama models | EDIT views.py | ~20 |
| B7 | Add `api_ollama_status()` view | EDIT views.py | ~15 |
| B8 | Add `api_ollama_models()` view | EDIT views.py | ~15 |
| B9 | Add Ollama URL patterns to urls.py | EDIT urls.py | 2 |
| B10 | Enhance `chatbot.html` - add Ollama optgroup in model selector | EDIT chatbot.html | ~15 |
| B11 | Enhance `settings.html` - add Ollama config section | EDIT settings.html | ~80 |

### PHASE C: Data Query & Reporting (Plan 02)

| # | Task | Files | Est. Lines |
|---|------|-------|-----------|
| C1 | Create `chatbot/tools/query_engine.py` - flexible query executor | NEW | ~120 |
| C2 | Create `chatbot/tools/report_builder.py` - ReportBuilder class | NEW | ~150 |
| C3 | Add `query_data_tool` and `generate_report_tool` to definitions.py | EDIT definitions.py | ~50 |
| C4 | Wire new tools in executors.py | EDIT executors.py | ~20 |
| C5 | Add `reports_page()` view | EDIT views.py | ~10 |
| C6 | Add `api_generate_report()` view | EDIT views.py | ~30 |
| C7 | Add `api_export_report()` view | EDIT views.py | ~40 |
| C8 | Add `api_query_data()` view | EDIT views.py | ~20 |
| C9 | Add report URL patterns to urls.py | EDIT urls.py | 4 |
| C10 | Create `templates/reports.html` - report viewer page | NEW | ~200 |

### PHASE D: Skill & Flow Engine (Plan 03)

| # | Task | Files | Est. Lines |
|---|------|-------|-----------|
| D1 | Add Skill, Flow, FlowStep, FlowExecution models to models.py | EDIT models.py | ~130 |
| D2 | Run `makemigrations` + `migrate` | CLI | — |
| D3 | Create `chatbot/skills/__init__.py` | NEW | 5 |
| D4 | Create `chatbot/skills/builtin_skills.py` - 9 system skills | NEW | ~100 |
| D5 | Create `chatbot/skills/executor.py` - SkillExecutor class | NEW | ~80 |
| D6 | Create `chatbot/skills/flow_engine.py` - FlowEngine class | NEW | ~120 |
| D7 | Create `chatbot/management/commands/setup_builtin_skills.py` | NEW | ~60 |
| D8 | Add skill/flow tools to definitions.py (create_skill, create_flow, run_flow, list_skills, list_flows) | EDIT definitions.py | ~80 |
| D9 | Wire skill/flow tools in executors.py | EDIT executors.py | ~30 |
| D10 | Add `skills_page()` view | EDIT views.py | ~10 |
| D11 | Add skill/flow API views (api_skills_list, api_skill_create, api_flows_list, api_flow_create, api_flow_run) | EDIT views.py | ~100 |
| D12 | Add skill/flow URL patterns to urls.py | EDIT urls.py | 6 |
| D13 | Create `templates/skills.html` - skill/flow management page | NEW | ~300 |
| D14 | Create `templates/flow_run.html` - flow execution display | NEW | ~150 |
| D15 | Register Skill, Flow, FlowStep, FlowExecution in admin.py | EDIT admin.py | ~120 |
| D16 | Enhance `chatbot.html` - add "Run Flow" quick action in sidebar | EDIT chatbot.html | ~20 |

---

## Summary Counts

| Category | Count |
|----------|-------|
| New Python files | 12 |
| New template files | 3 |
| Enhanced existing files | 8 |
| New Django models | 4 |
| New URL patterns | 12 |
| New view functions | 12 |
| New AI tools (for LLM function calling) | 7 |
| Total tasks | 43 |
| New pages (web) | 3 (reports, skills, flow_run) |
| Enhanced pages (web) | 2 (chatbot, settings) |
| Unchanged pages | 5 |

---

## Dependency Graph

```
PHASE A: Tool Refactor ──────────────────────────┐
  (A1-A6)                                        │
                                                  ▼
PHASE B: Ollama Integration ───► PHASE C: Data Query & Reports
  (B1-B11)                         (C1-C10)
       │                               │
       └──────────┐   ┌────────────────┘
                  ▼   ▼
            PHASE D: Skill & Flow Engine
              (D1-D16)
```

**Phase A must be done first** - it unblocks everything by extracting the duplicated tool code.
**Phases B and C can run in parallel** after Phase A.
**Phase D depends on both B and C** (needs Ollama for local execution, needs query engine for data skills).
