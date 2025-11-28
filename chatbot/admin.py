from django.contrib import admin
from django.utils.html import format_html
from .models import Chat, ChatSession, Task


# ========== CHAT SESSION ADMIN ==========

@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    """Admin interface for Chat Sessions"""

    list_display = ('name', 'user_link', 'model', 'message_count', 'created_at', 'is_active_badge')
    list_filter = ('is_active', 'model', 'created_at', 'user')
    search_fields = ('name', 'user__username', 'user__email')
    readonly_fields = ('created_at', 'updated_at', 'message_count', 'user_info')
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Session Information', {
            'fields': ('name', 'model', 'is_active'),
            'description': 'Basic session details'
        }),
        ('User Association', {
            'fields': ('user', 'user_info'),
            'description': 'User who owns this session'
        }),
        ('Statistics', {
            'fields': ('message_count', 'created_at', 'updated_at'),
            'classes': ('collapse',),
            'description': 'Session usage statistics'
        }),
    )

    def user_link(self, obj):
        """Display user with link to user admin"""
        url = f'/admin/auth/user/{obj.user.id}/change/'
        return format_html('<a href="{}">{}</a>', url, obj.user.username)
    user_link.short_description = 'User'
    user_link.admin_order_field = 'user__username'

    def user_info(self, obj):
        """Display detailed user information"""
        return f"{obj.user.username} ({obj.user.email})"
    user_info.short_description = 'User Details'

    def message_count(self, obj):
        """Display total messages in session"""
        return obj.messages.filter(is_deleted=False).count()
    message_count.short_description = 'Messages'
    message_count.admin_order_field = 'messages'

    def is_active_badge(self, obj):
        """Display active status as colored badge"""
        if obj.is_active:
            return format_html('<span style="color: green; font-weight: bold;">Active</span>')
        else:
            return format_html('<span style="color: red; font-weight: bold;">Inactive</span>')
    is_active_badge.short_description = 'Status'
    is_active_badge.admin_order_field = 'is_active'

    def get_queryset(self, request):
        """Optimize queryset with select_related"""
        qs = super().get_queryset(request)
        return qs.select_related('user')


# ========== CHAT MESSAGE ADMIN ==========

@admin.register(Chat)
class ChatAdmin(admin.ModelAdmin):
    """Admin interface for Chat Messages"""

    list_display = ('message_preview', 'session_link', 'user_link', 'created_at', 'is_deleted_badge')
    list_filter = ('is_deleted', 'session__user', 'created_at', 'session__name')
    search_fields = ('message', 'response', 'session__name', 'session__user__username')
    readonly_fields = ('created_at', 'session_info', 'user_info', 'message_length', 'response_length')
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Message Content', {
            'fields': ('message', 'response'),
            'description': 'User message and AI response'
        }),
        ('Session Details', {
            'fields': ('session', 'session_info', 'user_info'),
            'description': 'Session and user who owns this message'
        }),
        ('Message Status', {
            'fields': ('is_deleted', 'created_at'),
            'description': 'Deletion status and timestamp'
        }),
        ('Statistics', {
            'fields': ('message_length', 'response_length'),
            'classes': ('collapse',),
            'description': 'Message size information'
        }),
    )

    def message_preview(self, obj):
        """Display truncated message preview"""
        preview = obj.message[:50] + '...' if len(obj.message) > 50 else obj.message
        return preview
    message_preview.short_description = 'Message'
    message_preview.admin_order_field = 'message'

    def session_link(self, obj):
        """Display session with link to session admin"""
        if obj.session:
            url = f'/admin/chatbot/chatsession/{obj.session.id}/change/'
            return format_html('<a href="{}">{}</a>', url, obj.session.name)
        return 'N/A'
    session_link.short_description = 'Session'
    session_link.admin_order_field = 'session__name'

    def user_link(self, obj):
        """Display user who owns the session"""
        if obj.session:
            user = obj.session.user
            url = f'/admin/auth/user/{user.id}/change/'
            return format_html('<a href="{}">{}</a>', url, user.username)
        return 'N/A'
    user_link.short_description = 'User'
    user_link.admin_order_field = 'session__user__username'

    def session_info(self, obj):
        """Display detailed session information"""
        if obj.session:
            return f"{obj.session.name} (ID: {obj.session.id})"
        return 'No session assigned'
    session_info.short_description = 'Session Info'

    def user_info(self, obj):
        """Display user information from session"""
        if obj.session and obj.session.user:
            user = obj.session.user
            return f"{user.username} ({user.email})"
        return 'No user assigned'
    user_info.short_description = 'User Info'

    def message_length(self, obj):
        """Display message character count"""
        return f"{len(obj.message)} characters"
    message_length.short_description = 'Message Length'

    def response_length(self, obj):
        """Display response character count"""
        return f"{len(obj.response)} characters"
    response_length.short_description = 'Response Length'

    def is_deleted_badge(self, obj):
        """Display deletion status as colored badge"""
        if obj.is_deleted:
            return format_html('<span style="color: red; font-weight: bold;">Deleted</span>')
        else:
            return format_html('<span style="color: green; font-weight: bold;">Active</span>')
    is_deleted_badge.short_description = 'Status'
    is_deleted_badge.admin_order_field = 'is_deleted'

    def get_queryset(self, request):
        """Optimize queryset with select_related"""
        qs = super().get_queryset(request)
        return qs.select_related('session', 'session__user')

    def has_add_permission(self, request):
        """Prevent manual message creation via admin"""
        return False

    def has_delete_permission(self, request, obj=None):
        """Prevent deletion - use soft delete (is_deleted flag)"""
        return False


# ========== TASK ADMIN ==========

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    """Admin interface for Tasks"""

    list_display = ('title_link', 'user_link', 'priority_badge', 'status_badge', 'due_date_display', 'overdue_indicator', 'created_at')
    list_filter = ('priority', 'status', 'created_at', 'due_date', 'user')
    search_fields = ('title', 'description', 'user__username', 'user__email')
    readonly_fields = ('created_at', 'updated_at', 'completed_at', 'days_until_due')
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Task Information', {
            'fields': ('title', 'description', 'user'),
            'description': 'Basic task details'
        }),
        ('Priority & Status', {
            'fields': ('priority', 'status'),
            'description': 'Task priority level and current status'
        }),
        ('Dates', {
            'fields': ('due_date', 'created_at', 'updated_at', 'completed_at', 'days_until_due'),
            'description': 'Task timeline information'
        }),
        ('Metadata', {
            'fields': ('created_from_chat',),
            'classes': ('collapse',),
            'description': 'Task creation source'
        }),
    )

    def title_link(self, obj):
        """Display task title as link"""
        url = f'/admin/chatbot/task/{obj.id}/change/'
        return format_html('<a href="{}">{}</a>', url, obj.title)
    title_link.short_description = 'Title'
    title_link.admin_order_field = 'title'

    def user_link(self, obj):
        """Display user with link to user admin"""
        url = f'/admin/auth/user/{obj.user.id}/change/'
        return format_html('<a href="{}">{}</a>', url, obj.user.username)
    user_link.short_description = 'User'
    user_link.admin_order_field = 'user__username'

    def priority_badge(self, obj):
        """Display priority as colored badge"""
        colors = {
            'low': '#4CAF50',      # Green
            'medium': '#2196F3',   # Blue
            'high': '#FF9800',     # Orange
            'urgent': '#F44336',   # Red
        }
        color = colors.get(obj.priority, '#2196F3')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px; font-weight: bold;">{}</span>',
            color,
            obj.get_priority_display()
        )
    priority_badge.short_description = 'Priority'
    priority_badge.admin_order_field = 'priority'

    def status_badge(self, obj):
        """Display status as colored badge"""
        colors = {
            'pending': '#FFC107',      # Amber
            'in_progress': '#2196F3',  # Blue
            'completed': '#4CAF50',    # Green
            'cancelled': '#9E9E9E',    # Gray
        }
        color = colors.get(obj.status, '#2196F3')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    status_badge.admin_order_field = 'status'

    def due_date_display(self, obj):
        """Display due date in readable format"""
        if obj.due_date:
            return obj.due_date.strftime('%Y-%m-%d %H:%M')
        return 'No due date'
    due_date_display.short_description = 'Due Date'
    due_date_display.admin_order_field = 'due_date'

    def overdue_indicator(self, obj):
        """Show if task is overdue"""
        if obj.is_overdue():
            return format_html('<span style="color: red; font-weight: bold;">OVERDUE</span>')
        elif obj.due_date and obj.days_until_due() is not None:
            days = obj.days_until_due()
            if days < 0:
                return format_html('<span style="color: red;">{}d left</span>', days)
            elif days == 0:
                return format_html('<span style="color: orange; font-weight: bold;">TODAY</span>')
            else:
                return format_html('<span style="color: green;">{}d left</span>', days)
        return '-'
    overdue_indicator.short_description = 'Due In'

    def days_until_due(self, obj):
        """Display days remaining until due date"""
        days = obj.days_until_due()
        if days is None:
            return 'No due date'
        return f'{days} days'
    days_until_due.short_description = 'Days Until Due'

    def get_queryset(self, request):
        """Optimize queryset with select_related"""
        qs = super().get_queryset(request)
        return qs.select_related('user', 'created_from_chat')