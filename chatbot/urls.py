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
    path('api/settings/tools/toggle/', views.api_toggle_tools, name='api_toggle_tools'),
    path('api/settings/tools/status/', views.api_tools_status, name='api_tools_status'),
    path('api/settings/developer-mode/toggle/', views.api_toggle_developer_mode, name='api_toggle_developer_mode'),
    path('api/settings/history-limit/', views.api_set_history_limit, name='api_set_history_limit'),

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

    # Reports & Data Query endpoints (Phase C)
    path('reports/', views.reports_page, name='reports'),
    path('api/reports/generate/', views.api_generate_report, name='api_generate_report'),
    path('api/reports/export/', views.api_export_report, name='api_export_report'),
    path('api/data/query/', views.api_query_data, name='api_query_data'),

    # Skill & Flow Engine endpoints (Phase D)
    path('skills/', views.skills_page, name='skills'),
    path('flow/run/<int:execution_id>/', views.flow_run_page, name='flow_run'),
    path('api/skills/', views.api_skills_list, name='api_skills_list'),
    path('api/skills/create/', views.api_skill_create, name='api_skill_create'),
    path('api/skills/<int:skill_id>/', views.api_skill_detail, name='api_skill_detail'),
    path('api/skills/<int:skill_id>/test/', views.api_skill_test, name='api_skill_test'),
    path('api/skills/<int:skill_id>/logs/', views.api_skill_logs, name='api_skill_logs'),
    path('api/skills/<int:skill_id>/improve/', views.api_skill_improve, name='api_skill_improve'),
    path('api/skills/<int:skill_id>/apply-improvement/', views.api_skill_apply_improvement, name='api_skill_apply_improvement'),
    path('api/flows/', views.api_flows_list, name='api_flows_list'),
    path('api/flows/create/', views.api_flow_create, name='api_flow_create'),
    path('api/flows/<int:flow_id>/run/', views.api_flow_run, name='api_flow_run'),
    path('api/flow-executions/<int:execution_id>/', views.api_flow_execution_detail, name='api_flow_execution_detail'),
    path('api/skill-feedback/', views.api_skill_feedback, name='api_skill_feedback'),

    # Ollama endpoints
    path('api/ollama/status/', views.api_ollama_status, name='api_ollama_status'),
    path('api/ollama/connect/', views.api_save_ollama_config, name='api_ollama_connect'),
    path('api/ollama/start/', views.api_ollama_start, name='api_ollama_start'),
    path('api/ollama/stop/', views.api_ollama_stop, name='api_ollama_stop'),

    # Claude Terminal endpoints (Phase 1)
    path('claude-terminal/', views.claude_terminal, name='claude_terminal'),
    path('api/terminal/start/', views.api_terminal_start, name='api_terminal_start'),
    path('api/terminal/stop/', views.api_terminal_stop, name='api_terminal_stop'),
    path('api/terminal/status/', views.api_terminal_status, name='api_terminal_status'),
    path('api/terminal/message/', views.api_terminal_message, name='api_terminal_message'),
]