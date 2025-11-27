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
]