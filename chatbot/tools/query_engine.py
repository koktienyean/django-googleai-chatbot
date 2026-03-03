"""
Flexible query engine for AI-driven data queries.
Allows AI to query Django models with dynamic filters, aggregations, and ordering.
All queries are scoped to the requesting user for security.
"""
from datetime import datetime, timedelta
from django.db.models import Count, Q
from django.utils import timezone


def parse_date(date_str):
    """Parse date string in YYYY-MM-DD format or relative terms."""
    if not date_str:
        return None

    # Handle relative dates
    today = timezone.now().date()
    relative = date_str.lower().strip()
    if relative == 'today':
        return timezone.make_aware(datetime.combine(today, datetime.min.time()))
    elif relative == 'yesterday':
        return timezone.make_aware(datetime.combine(today - timedelta(days=1), datetime.min.time()))
    elif relative in ('this_week', 'this week'):
        start = today - timedelta(days=today.weekday())
        return timezone.make_aware(datetime.combine(start, datetime.min.time()))
    elif relative in ('last_week', 'last week'):
        start = today - timedelta(days=today.weekday() + 7)
        return timezone.make_aware(datetime.combine(start, datetime.min.time()))
    elif relative in ('this_month', 'this month'):
        return timezone.make_aware(datetime.combine(today.replace(day=1), datetime.min.time()))
    elif relative in ('last_month', 'last month'):
        first_this_month = today.replace(day=1)
        last_month = first_this_month - timedelta(days=1)
        return timezone.make_aware(datetime.combine(last_month.replace(day=1), datetime.min.time()))
    elif relative in ('last_30_days', 'last 30 days'):
        return timezone.make_aware(datetime.combine(today - timedelta(days=30), datetime.min.time()))
    elif relative in ('last_7_days', 'last 7 days'):
        return timezone.make_aware(datetime.combine(today - timedelta(days=7), datetime.min.time()))

    # Parse YYYY-MM-DD
    try:
        parsed = datetime.strptime(date_str, '%Y-%m-%d')
        return timezone.make_aware(parsed)
    except ValueError:
        return None


def _get_model_class(data_type):
    """Lazy import and return the model class for a data type."""
    from chatbot.models import Task, Chat, ChatSession, TaskAnalytics, ChatAnalytics

    model_map = {
        'tasks': Task,
        'chats': Chat,
        'sessions': ChatSession,
        'task_analytics': TaskAnalytics,
        'chat_analytics': ChatAnalytics,
    }
    return model_map.get(data_type)


def _get_user_queryset(model_class, user, data_type):
    """Get a user-scoped queryset for a model."""
    if data_type == 'chats':
        return model_class.objects.filter(session__user=user, is_deleted=False)
    elif data_type == 'sessions':
        return model_class.objects.filter(user=user, is_active=True)
    else:
        return model_class.objects.filter(user=user)


def _apply_filters(queryset, filters, data_type):
    """Apply dynamic filters to a queryset."""
    if not filters:
        return queryset

    if 'status' in filters and data_type in ('tasks',):
        queryset = queryset.filter(status=filters['status'])

    if 'priority' in filters and data_type in ('tasks',):
        queryset = queryset.filter(priority=filters['priority'])

    if 'date_from' in filters:
        dt = parse_date(filters['date_from'])
        if dt:
            queryset = queryset.filter(created_at__gte=dt)

    if 'date_to' in filters:
        dt = parse_date(filters['date_to'])
        if dt:
            queryset = queryset.filter(created_at__lte=dt)

    if 'keyword' in filters:
        keyword = filters['keyword']
        if data_type == 'tasks':
            queryset = queryset.filter(
                Q(title__icontains=keyword) | Q(description__icontains=keyword)
            )
        elif data_type == 'chats':
            queryset = queryset.filter(
                Q(message__icontains=keyword) | Q(response__icontains=keyword)
            )
        elif data_type == 'sessions':
            queryset = queryset.filter(name__icontains=keyword)

    if 'model' in filters and data_type == 'sessions':
        queryset = queryset.filter(model=filters['model'])

    return queryset


def _build_trend_data(queryset, days=30):
    """Build daily count trend data."""
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=days)

    daily = (
        queryset
        .filter(created_at__date__gte=start_date)
        .values('created_at__date')
        .annotate(count=Count('id'))
        .order_by('created_at__date')
    )

    # Fill in missing days with 0
    trend = {}
    current = start_date
    while current <= end_date:
        trend[str(current)] = 0
        current += timedelta(days=1)

    for entry in daily:
        date_key = str(entry['created_at__date'])
        trend[date_key] = entry['count']

    return [{'date': k, 'count': v} for k, v in trend.items()]


def _serialize_values(values_list, data_type):
    """Convert queryset values to JSON-serializable format."""
    result = []
    for item in values_list:
        row = {}
        for key, value in item.items():
            if hasattr(value, 'isoformat'):
                row[key] = value.isoformat()
            else:
                row[key] = value
        result.append(row)
    return result


def execute_query(user, data_type, filters=None, aggregation='none', order_by='-created_at', limit=20):
    """Execute a flexible query against Django models.

    Args:
        user: Django User instance
        data_type: One of 'tasks', 'chats', 'sessions', 'task_analytics', 'chat_analytics'
        filters: Dict of filter criteria (status, priority, date_from, date_to, keyword, model)
        aggregation: One of 'none', 'count', 'group_by_status', 'group_by_priority', 'group_by_date', 'trend'
        order_by: Field to order by (default: '-created_at')
        limit: Max results (default: 20, max: 100)

    Returns:
        dict with query results
    """
    model_class = _get_model_class(data_type)
    if not model_class:
        return {'error': f'Unknown data type: {data_type}. Valid: tasks, chats, sessions, task_analytics, chat_analytics'}

    try:
        queryset = _get_user_queryset(model_class, user, data_type)
        queryset = _apply_filters(queryset, filters, data_type)

        # Apply aggregation
        if aggregation == 'count':
            return {'data_type': data_type, 'aggregation': 'count', 'count': queryset.count()}

        elif aggregation == 'group_by_status':
            groups = list(queryset.values('status').annotate(count=Count('id')).order_by('status'))
            return {'data_type': data_type, 'aggregation': 'group_by_status', 'groups': groups}

        elif aggregation == 'group_by_priority':
            groups = list(queryset.values('priority').annotate(count=Count('id')).order_by('priority'))
            return {'data_type': data_type, 'aggregation': 'group_by_priority', 'groups': groups}

        elif aggregation == 'group_by_date':
            groups = list(
                queryset.values('created_at__date')
                .annotate(count=Count('id'))
                .order_by('created_at__date')
            )
            return {
                'data_type': data_type,
                'aggregation': 'group_by_date',
                'groups': [{'date': str(g['created_at__date']), 'count': g['count']} for g in groups]
            }

        elif aggregation == 'trend':
            trend = _build_trend_data(queryset)
            return {'data_type': data_type, 'aggregation': 'trend', 'trend': trend}

        # No aggregation - return raw results
        limit = min(int(limit), 100)
        values = queryset.order_by(order_by)[:limit].values()
        return {
            'data_type': data_type,
            'count': queryset.count(),
            'results': _serialize_values(list(values), data_type)
        }

    except Exception as e:
        return {'error': f'Query failed: {str(e)}'}
