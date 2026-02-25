# Plan 02: AI Data Query & Report Generation

**Status**: Planning
**Priority**: High
**Depends on**: 01-ollama-integration (shared tool refactor)

---

## Goal

Enhance the AI chatbot so it can **query any Django model data** and **generate structured reports** (tables, charts, summaries) through natural language conversation. The user says "show me task completion trend this month" and the AI queries the database, formats the result, and presents it.

## What Already Exists

The codebase already has basic data querying via tool/function calling:

```
Current tools in ask_claude() / ask_gemini_api():
- search_chats_tool        -> search_my_chats()
- get_stats_tool           -> get_chat_statistics()
- get_recent_tool          -> get_recent_conversations()
- search_dates_tool        -> search_by_date_range()
- list_tasks_tool          -> list_my_tasks()
- get_task_summary_tool    -> get_task_summary()
- get_productivity_metrics -> get_productivity_metrics_tool()
- get_task_insights        -> get_task_insights_tool()
- generate_weekly_report   -> generate_weekly_report_tool()
```

**Gaps**:
- No generic/flexible query capability (each query is a hardcoded tool)
- No report formatting (just returns raw dicts)
- No chart/visualization generation
- No export (PDF, CSV, Excel)
- No cross-model queries (e.g., "tasks linked to chats about X")

## Implementation Plan

### Phase 1: Flexible Data Query Tools

**1.1 Generic query builder tool**

Instead of one tool per query, add a flexible query tool that accepts natural-language-described filters:

```python
# New tool: query_data_tool
{
    "name": "query_data_tool",
    "description": "Query Django data with flexible filters. Supports: tasks, chats, sessions, analytics.",
    "input_schema": {
        "type": "object",
        "properties": {
            "data_type": {
                "type": "string",
                "enum": ["tasks", "chats", "sessions", "task_analytics", "chat_analytics"]
            },
            "filters": {
                "type": "object",
                "description": "Filter criteria (status, priority, date_from, date_to, keyword, etc.)"
            },
            "aggregation": {
                "type": "string",
                "enum": ["none", "count", "group_by_status", "group_by_priority", "group_by_date", "trend"],
                "default": "none"
            },
            "order_by": {"type": "string", "default": "-created_at"},
            "limit": {"type": "integer", "default": 20}
        },
        "required": ["data_type"]
    }
}
```

**1.2 Query executor**

```python
# chatbot/tools/query_engine.py
def execute_query(user, data_type, filters=None, aggregation='none', order_by='-created_at', limit=20):
    """Execute a flexible query against Django models"""

    model_map = {
        'tasks': Task,
        'chats': Chat,
        'sessions': ChatSession,
        'task_analytics': TaskAnalytics,
        'chat_analytics': ChatAnalytics,
    }

    queryset = model_map[data_type].objects.filter(user=user)  # or session__user

    # Apply filters dynamically
    if filters:
        if 'status' in filters:
            queryset = queryset.filter(status=filters['status'])
        if 'priority' in filters:
            queryset = queryset.filter(priority=filters['priority'])
        if 'date_from' in filters:
            queryset = queryset.filter(created_at__gte=parse_date(filters['date_from']))
        if 'date_to' in filters:
            queryset = queryset.filter(created_at__lte=parse_date(filters['date_to']))
        if 'keyword' in filters:
            queryset = queryset.filter(
                Q(title__icontains=filters['keyword']) |
                Q(description__icontains=filters['keyword'])
            )

    # Apply aggregation
    if aggregation == 'count':
        return {'count': queryset.count()}
    elif aggregation == 'group_by_status':
        return list(queryset.values('status').annotate(count=Count('id')))
    elif aggregation == 'group_by_priority':
        return list(queryset.values('priority').annotate(count=Count('id')))
    elif aggregation == 'group_by_date':
        return list(queryset.values('created_at__date').annotate(count=Count('id')).order_by('created_at__date'))
    elif aggregation == 'trend':
        return build_trend_data(queryset)

    # Return raw results
    return list(queryset.order_by(order_by)[:limit].values())
```

### Phase 2: Report Generation

**2.1 Report builder tool**

```python
# New tool: generate_report_tool
{
    "name": "generate_report_tool",
    "description": "Generate a formatted report from queried data",
    "input_schema": {
        "type": "object",
        "properties": {
            "report_type": {
                "type": "string",
                "enum": ["summary", "detailed", "trend", "comparison"]
            },
            "data_type": {"type": "string"},
            "time_range": {
                "type": "string",
                "enum": ["today", "this_week", "this_month", "last_30_days", "custom"]
            },
            "format": {
                "type": "string",
                "enum": ["markdown", "table", "chart_data"],
                "default": "markdown"
            }
        },
        "required": ["report_type", "data_type"]
    }
}
```

**2.2 Report formatter**

```python
# chatbot/tools/report_builder.py
class ReportBuilder:
    def __init__(self, user):
        self.user = user

    def build_summary_report(self, data_type, time_range):
        """Build a summary report with key metrics"""
        data = execute_query(self.user, data_type, ...)
        return {
            'title': f'{data_type.title()} Summary - {time_range}',
            'metrics': self._compute_metrics(data),
            'table': self._format_table(data),
            'insights': self._generate_insights(data)
        }

    def build_trend_report(self, data_type, time_range):
        """Build a trend report showing changes over time"""
        trend_data = execute_query(self.user, data_type, aggregation='trend')
        return {
            'title': f'{data_type.title()} Trend',
            'chart_data': trend_data,  # Frontend renders as chart
            'summary': self._summarize_trend(trend_data)
        }
```

### Phase 3: Report Export (Optional)

**3.1 Export endpoints**
```
GET /api/reports/export/?type=tasks&format=csv
GET /api/reports/export/?type=tasks&format=pdf
```

**3.2 Export formats**
- CSV via Python `csv` module (no new dependency)
- PDF via `reportlab` or `weasyprint` (new dependency)
- Excel via `openpyxl` (new dependency)

---

## Example User Interactions

```
User: "How many tasks did I complete this week?"
AI: [calls query_data_tool(data_type='tasks', filters={status:'completed', date_from:'2026-02-19'}, aggregation='count')]
AI: "You completed 12 tasks this week! That's 3 more than last week."

User: "Show me a breakdown by priority"
AI: [calls query_data_tool(data_type='tasks', aggregation='group_by_priority')]
AI: "Here's your task breakdown:
| Priority | Count |
|----------|-------|
| Urgent   | 2     |
| High     | 5     |
| Medium   | 8     |
| Low      | 3     |"

User: "Generate a monthly productivity report"
AI: [calls generate_report_tool(report_type='summary', data_type='tasks', time_range='this_month')]
AI: Returns formatted report with metrics, tables, and insights
```

## File Changes Summary

| File | Change |
|------|--------|
| `chatbot/tools/query_engine.py` (new) | Flexible query executor |
| `chatbot/tools/report_builder.py` (new) | Report generation logic |
| `chatbot/tools/definitions.py` | Add `query_data_tool`, `generate_report_tool` |
| `chatbot/tools/executors.py` | Route new tools to query_engine/report_builder |
| `chatbot/urls.py` | Add `/api/reports/export/` (Phase 3) |
| `chatbot/views.py` | Wire up new tools in ask_ai flow |

## Risks & Considerations

1. **Security** - Must ensure users can only query their own data (filter by user always)
2. **Performance** - Large queries could be slow. Add pagination and query limits
3. **SQL injection** - Never pass raw user input to queries. Use Django ORM only
4. **Model compatibility** - Not all LLMs are good at structured tool calling. Test with each backend
5. **Date parsing** - Natural language dates ("last week", "yesterday") need robust parsing
