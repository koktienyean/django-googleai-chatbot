from django.urls import path
from . import views

urlpatterns = [
    # Authentication
    path('login/', views.login, name='login'),
    path('register/', views.register, name='register'),
    path('logout/', views.logout, name='logout'),

    # Chat views
    path('', views.chatbot_home, name='chatbot_home'),
    path('chat/<int:session_id>/', views.chatbot_session, name='chatbot_session'),

    # Settings
    path('settings/', views.settings_page, name='settings'),

    # Session API endpoints
    path('api/sessions/', views.api_session_list, name='api_session_list'),
    path('api/sessions/create/', views.api_session_create, name='api_session_create'),
    path('api/sessions/<int:session_id>/', views.api_session_detail, name='api_session_detail'),
    path('api/sessions/<int:session_id>/update/', views.api_session_update, name='api_session_update'),
    path('api/sessions/<int:session_id>/delete/', views.api_session_delete, name='api_session_delete'),

    # Model API endpoints
    path('api/models/', views.api_list_models, name='api_models'),
    path('api/settings/save/', views.api_save_settings, name='api_settings_save'),

    # Async message endpoints
    path('api/sessions/<int:session_id>/send/', views.api_send_message_async, name='api_send_message_async'),
    path('api/message/<str:request_id>/status/', views.api_check_response, name='api_check_response'),

    # Calendar endpoints (Phase 3)
    path('api/tasks/calendar/', views.api_tasks_calendar, name='api_tasks_calendar'),
    path('api/tasks/<int:task_id>/update_due_date/', views.api_task_update_due_date, name='api_task_update_due_date'),
    path('calendar/', views.calendar_view, name='calendar_view'),

    # Notification endpoints (Phase 4)
    path('api/notifications/', views.api_notifications_list, name='api_notifications_list'),
    path('api/notifications/<int:notification_id>/read/', views.api_notification_mark_read, name='api_notification_mark_read'),

    # Recurring tasks endpoints (Phase 4)
    path('api/recurring-tasks/', views.api_recurring_tasks_list, name='api_recurring_tasks_list'),

    # Analytics endpoints (Phase 5)
    path('api/analytics/metrics/', views.api_productivity_metrics, name='api_productivity_metrics'),
    path('api/analytics/insights/', views.api_task_insights, name='api_task_insights'),
    path('api/analytics/weekly-report/', views.api_weekly_report, name='api_weekly_report'),

    # Claude Terminal endpoints (Phase 1)
    path('claude-terminal/', views.claude_terminal, name='claude_terminal'),
    path('api/terminal/start/', views.api_terminal_start, name='api_terminal_start'),
    path('api/terminal/stop/', views.api_terminal_stop, name='api_terminal_stop'),
    path('api/terminal/status/', views.api_terminal_status, name='api_terminal_status'),
    path('api/terminal/message/', views.api_terminal_message, name='api_terminal_message'),
]