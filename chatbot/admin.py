from django.contrib import admin
from django.utils.html import format_html
from .models import (
    Chat, ChatSession, Task,
    Notification, NotificationPreference,
    RecurringTaskTemplate, RecurringTaskInstance,
    TaskAnalytics, ChatAnalytics,
    Skill, Flow, FlowStep, FlowExecution,
    SkillExecutionLog, SkillFeedback
)


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


# ========== NOTIFICATION ADMIN (PHASE 4) ==========

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    """Admin interface for Notifications"""

    list_display = ('subject', 'user_link', 'type_badge', 'is_sent_badge', 'sent_at', 'created_at')
    list_filter = ('notification_type', 'is_sent', 'created_at', 'user')
    search_fields = ('subject', 'message', 'user__username', 'user__email')
    readonly_fields = ('created_at', 'sent_at', 'read_at', 'last_error')
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Notification Details', {
            'fields': ('subject', 'message', 'notification_type'),
            'description': 'Notification content and type'
        }),
        ('Recipient', {
            'fields': ('user', 'task'),
            'description': 'User and related task (if any)'
        }),
        ('Delivery Status', {
            'fields': ('is_sent', 'sent_at', 'created_at', 'read_at'),
            'description': 'Delivery and reading status'
        }),
        ('Error Tracking', {
            'fields': ('attempts', 'last_error'),
            'classes': ('collapse',),
            'description': 'Retry attempts and error messages'
        }),
    )

    def user_link(self, obj):
        """Display user with link"""
        url = f'/admin/auth/user/{obj.user.id}/change/'
        return format_html('<a href="{}">{}</a>', url, obj.user.username)
    user_link.short_description = 'User'
    user_link.admin_order_field = 'user__username'

    def type_badge(self, obj):
        """Display notification type as badge"""
        colors = {
            'deadline_reminder': '#FF9800',
            'task_due_today': '#FFC107',
            'task_overdue': '#F44336',
            'task_completed': '#4CAF50',
            'recurring_created': '#2196F3',
        }
        color = colors.get(obj.notification_type, '#9E9E9E')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px; font-weight: bold;">{}</span>',
            color,
            obj.get_notification_type_display()
        )
    type_badge.short_description = 'Type'
    type_badge.admin_order_field = 'notification_type'

    def is_sent_badge(self, obj):
        """Display sent status"""
        if obj.is_sent:
            return format_html('<span style="color: green; font-weight: bold;">✓ Sent</span>')
        else:
            return format_html('<span style="color: orange;">Pending</span>')
    is_sent_badge.short_description = 'Sent'
    is_sent_badge.admin_order_field = 'is_sent'

    def get_queryset(self, request):
        """Optimize queryset"""
        qs = super().get_queryset(request)
        return qs.select_related('user', 'task')


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    """Admin interface for Notification Preferences"""

    list_display = ('user_link', 'deadline_enabled_badge', 'overdue_enabled_badge', 'daily_digest_badge', 'updated_at')
    list_filter = ('deadline_reminder_enabled', 'overdue_reminder_enabled', 'daily_digest_enabled', 'updated_at')
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        ('User', {
            'fields': ('user',),
        }),
        ('Deadline Reminders', {
            'fields': ('deadline_reminder_enabled', 'reminder_days_before', 'reminder_time'),
        }),
        ('Overdue Notifications', {
            'fields': ('overdue_reminder_enabled',),
        }),
        ('Daily Digest', {
            'fields': ('daily_digest_enabled', 'digest_time'),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    def user_link(self, obj):
        """Display user with link"""
        url = f'/admin/auth/user/{obj.user.id}/change/'
        return format_html('<a href="{}">{}</a>', url, obj.user.username)
    user_link.short_description = 'User'
    user_link.admin_order_field = 'user__username'

    def deadline_enabled_badge(self, obj):
        """Display deadline reminder status"""
        if obj.deadline_reminder_enabled:
            return format_html('<span style="color: green; font-weight: bold;">✓ Enabled</span>')
        return format_html('<span style="color: gray;">Disabled</span>')
    deadline_enabled_badge.short_description = 'Deadline Reminders'

    def overdue_enabled_badge(self, obj):
        """Display overdue notification status"""
        if obj.overdue_reminder_enabled:
            return format_html('<span style="color: green; font-weight: bold;">✓ Enabled</span>')
        return format_html('<span style="color: gray;">Disabled</span>')
    overdue_enabled_badge.short_description = 'Overdue Notifications'

    def daily_digest_badge(self, obj):
        """Display daily digest status"""
        if obj.daily_digest_enabled:
            return format_html('<span style="color: green; font-weight: bold;">✓ Enabled</span>')
        return format_html('<span style="color: gray;">Disabled</span>')
    daily_digest_badge.short_description = 'Daily Digest'


# ========== RECURRING TASK ADMIN (PHASE 4) ==========

@admin.register(RecurringTaskTemplate)
class RecurringTaskTemplateAdmin(admin.ModelAdmin):
    """Admin interface for Recurring Task Templates"""

    list_display = ('title', 'user_link', 'frequency_badge', 'priority_badge', 'is_active_badge', 'next_instance_date', 'created_at')
    list_filter = ('frequency', 'priority', 'is_active', 'created_at', 'user')
    search_fields = ('title', 'description', 'user__username')
    readonly_fields = ('created_at', 'updated_at', 'last_instance_created')
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Task Template', {
            'fields': ('user', 'title', 'description', 'priority'),
        }),
        ('Recurrence Settings', {
            'fields': ('frequency', 'start_date', 'end_date', 'is_active'),
        }),
        ('Schedule', {
            'fields': ('next_instance_date', 'last_instance_created'),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    def user_link(self, obj):
        """Display user with link"""
        url = f'/admin/auth/user/{obj.user.id}/change/'
        return format_html('<a href="{}">{}</a>', url, obj.user.username)
    user_link.short_description = 'User'
    user_link.admin_order_field = 'user__username'

    def frequency_badge(self, obj):
        """Display frequency as badge"""
        colors = {
            'daily': '#F44336',
            'weekly': '#FF9800',
            'biweekly': '#2196F3',
            'monthly': '#4CAF50',
            'quarterly': '#9C27B0',
            'yearly': '#009688',
        }
        color = colors.get(obj.frequency, '#9E9E9E')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px; font-weight: bold;">{}</span>',
            color,
            obj.get_frequency_display()
        )
    frequency_badge.short_description = 'Frequency'
    frequency_badge.admin_order_field = 'frequency'

    def priority_badge(self, obj):
        """Display priority as badge"""
        colors = {
            'low': '#4CAF50',
            'medium': '#2196F3',
            'high': '#FF9800',
            'urgent': '#F44336',
        }
        color = colors.get(obj.priority, '#2196F3')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px; font-weight: bold;">{}</span>',
            color,
            obj.get_priority_display()
        )
    priority_badge.short_description = 'Priority'
    priority_badge.admin_order_field = 'priority'

    def is_active_badge(self, obj):
        """Display active status"""
        if obj.is_active:
            return format_html('<span style="color: green; font-weight: bold;">✓ Active</span>')
        return format_html('<span style="color: red;">Inactive</span>')
    is_active_badge.short_description = 'Status'
    is_active_badge.admin_order_field = 'is_active'

    def get_queryset(self, request):
        """Optimize queryset"""
        qs = super().get_queryset(request)
        return qs.select_related('user')


@admin.register(RecurringTaskInstance)
class RecurringTaskInstanceAdmin(admin.ModelAdmin):
    """Admin interface for Recurring Task Instances"""

    list_display = ('template_link', 'task_link', 'instance_number', 'created_at')
    list_filter = ('template', 'created_at')
    search_fields = ('template__title', 'task__title', 'template__user__username')
    readonly_fields = ('created_at',)

    fieldsets = (
        ('Instance Info', {
            'fields': ('template', 'task', 'instance_number'),
        }),
        ('Timestamp', {
            'fields': ('created_at',),
            'classes': ('collapse',),
        }),
    )

    def template_link(self, obj):
        """Display template with link"""
        url = f'/admin/chatbot/recurringtasktemplate/{obj.template.id}/change/'
        return format_html('<a href="{}">{}</a>', url, obj.template.title)
    template_link.short_description = 'Template'
    template_link.admin_order_field = 'template__title'

    def task_link(self, obj):
        """Display task with link"""
        url = f'/admin/chatbot/task/{obj.task.id}/change/'
        return format_html('<a href="{}">{}</a>', url, obj.task.title)
    task_link.short_description = 'Task'
    task_link.admin_order_field = 'task__title'

    def get_queryset(self, request):
        """Optimize queryset"""
        qs = super().get_queryset(request)
        return qs.select_related('template', 'task')


# ========== ANALYTICS ADMIN (PHASE 5) ==========

@admin.register(TaskAnalytics)
class TaskAnalyticsAdmin(admin.ModelAdmin):
    """Admin interface for Task Analytics"""

    list_display = ('user_link', 'date', 'total_tasks', 'completion_rate_display', 'overdue_count', 'created_at')
    list_filter = ('date', 'user')
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('created_at',)

    fieldsets = (
        ('User & Date', {
            'fields': ('user', 'date'),
        }),
        ('Task Counts', {
            'fields': ('total_tasks', 'pending_count', 'in_progress_count', 'completed_count', 'completed_today', 'overdue_count'),
        }),
        ('Priority Breakdown', {
            'fields': ('urgent_count', 'high_count', 'medium_count', 'low_count'),
            'classes': ('collapse',),
        }),
        ('Metrics', {
            'fields': ('completion_rate',),
        }),
        ('Timestamp', {
            'fields': ('created_at',),
            'classes': ('collapse',),
        }),
    )

    def user_link(self, obj):
        """Display user with link"""
        url = f'/admin/auth/user/{obj.user.id}/change/'
        return format_html('<a href="{}">{}</a>', url, obj.user.username)
    user_link.short_description = 'User'
    user_link.admin_order_field = 'user__username'

    def completion_rate_display(self, obj):
        """Display completion rate as percentage"""
        return f"{obj.completion_rate:.1f}%"
    completion_rate_display.short_description = 'Completion Rate'
    completion_rate_display.admin_order_field = 'completion_rate'

    def get_queryset(self, request):
        """Optimize queryset"""
        qs = super().get_queryset(request)
        return qs.select_related('user')


@admin.register(ChatAnalytics)
class ChatAnalyticsAdmin(admin.ModelAdmin):
    """Admin interface for Chat Analytics"""

    list_display = ('user_link', 'date', 'total_messages', 'user_messages', 'ai_responses', 'total_sessions', 'created_at')
    list_filter = ('date', 'user')
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('created_at',)

    fieldsets = (
        ('User & Date', {
            'fields': ('user', 'date'),
        }),
        ('Message Counts', {
            'fields': ('total_messages', 'user_messages', 'ai_responses'),
        }),
        ('Session Info', {
            'fields': ('total_sessions', 'active_sessions', 'avg_session_length'),
        }),
        ('Timestamp', {
            'fields': ('created_at',),
            'classes': ('collapse',),
        }),
    )

    def user_link(self, obj):
        """Display user with link"""
        url = f'/admin/auth/user/{obj.user.id}/change/'
        return format_html('<a href="{}">{}</a>', url, obj.user.username)
    user_link.short_description = 'User'
    user_link.admin_order_field = 'user__username'

    def get_queryset(self, request):
        """Optimize queryset"""
        qs = super().get_queryset(request)
        return qs.select_related('user')


# ========== SKILL & FLOW ENGINE ADMIN (PHASE D) ==========

class FlowStepInline(admin.TabularInline):
    """Inline editor for flow steps"""
    model = FlowStep
    extra = 0
    ordering = ['order']
    fields = ('order', 'skill', 'input_mapping', 'config_override', 'condition')


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    """Admin interface for Skills"""

    list_display = ('name', 'user_link', 'type_badge', 'system_badge', 'version', 'rating_display', 'success_display', 'total_executions', 'created_at')
    list_filter = ('skill_type', 'is_system', 'created_at', 'user')
    search_fields = ('name', 'description', 'user__username')
    readonly_fields = ('created_at', 'updated_at', 'last_improved_at', 'avg_rating', 'success_rate', 'total_executions')

    fieldsets = (
        ('Skill Info', {
            'fields': ('user', 'name', 'description', 'skill_type', 'is_system'),
        }),
        ('Configuration', {
            'fields': ('config',),
        }),
        ('Statistics', {
            'fields': ('version', 'avg_rating', 'success_rate', 'total_executions', 'last_improved_at'),
            'classes': ('collapse',),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    def user_link(self, obj):
        url = f'/admin/auth/user/{obj.user.id}/change/'
        return format_html('<a href="{}">{}</a>', url, obj.user.username)
    user_link.short_description = 'User'
    user_link.admin_order_field = 'user__username'

    def type_badge(self, obj):
        colors = {
            'query': '#2196F3', 'transform': '#9C27B0', 'generate': '#FF9800',
            'action': '#F44336', 'condition': '#009688',
        }
        color = colors.get(obj.skill_type, '#9E9E9E')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px; font-weight: bold;">{}</span>',
            color, obj.skill_type
        )
    type_badge.short_description = 'Type'
    type_badge.admin_order_field = 'skill_type'

    def system_badge(self, obj):
        if obj.is_system:
            return format_html('<span style="color: #64b5f6; font-weight: bold;">System</span>')
        return format_html('<span style="color: #a0a0a0;">Custom</span>')
    system_badge.short_description = 'Source'

    def rating_display(self, obj):
        return f"{obj.avg_rating:.1f}/5"
    rating_display.short_description = 'Rating'
    rating_display.admin_order_field = 'avg_rating'

    def success_display(self, obj):
        return f"{obj.success_rate:.0f}%"
    success_display.short_description = 'Success'
    success_display.admin_order_field = 'success_rate'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')


@admin.register(Flow)
class FlowAdmin(admin.ModelAdmin):
    """Admin interface for Flows"""

    list_display = ('name', 'user_link', 'step_count', 'is_active_badge', 'updated_at')
    list_filter = ('is_active', 'created_at', 'user')
    search_fields = ('name', 'description', 'user__username')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [FlowStepInline]

    fieldsets = (
        ('Flow Info', {
            'fields': ('user', 'name', 'description', 'is_active'),
        }),
        ('Trigger', {
            'fields': ('trigger',),
            'classes': ('collapse',),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    def user_link(self, obj):
        url = f'/admin/auth/user/{obj.user.id}/change/'
        return format_html('<a href="{}">{}</a>', url, obj.user.username)
    user_link.short_description = 'User'
    user_link.admin_order_field = 'user__username'

    def step_count(self, obj):
        count = obj.steps.count()
        return f"{count} step{'s' if count != 1 else ''}"
    step_count.short_description = 'Steps'

    def is_active_badge(self, obj):
        if obj.is_active:
            return format_html('<span style="color: green; font-weight: bold;">Active</span>')
        return format_html('<span style="color: red;">Inactive</span>')
    is_active_badge.short_description = 'Status'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')


@admin.register(FlowExecution)
class FlowExecutionAdmin(admin.ModelAdmin):
    """Admin interface for Flow Executions"""

    list_display = ('id', 'flow_link', 'user_link', 'status_badge', 'progress_display', 'triggered_by', 'started_at', 'completed_at')
    list_filter = ('status', 'triggered_by', 'started_at', 'user')
    search_fields = ('flow__name', 'user__username', 'error_message')
    readonly_fields = ('started_at', 'completed_at', 'step_results', 'trigger_context')

    fieldsets = (
        ('Execution Info', {
            'fields': ('flow', 'user', 'status', 'triggered_by', 'chat_session'),
        }),
        ('Progress', {
            'fields': ('current_step', 'total_steps', 'step_results'),
        }),
        ('Context', {
            'fields': ('trigger_context',),
            'classes': ('collapse',),
        }),
        ('Error', {
            'fields': ('error_message',),
            'classes': ('collapse',),
        }),
        ('Timestamps', {
            'fields': ('started_at', 'completed_at'),
            'classes': ('collapse',),
        }),
    )

    def flow_link(self, obj):
        url = f'/admin/chatbot/flow/{obj.flow.id}/change/'
        return format_html('<a href="{}">{}</a>', url, obj.flow.name)
    flow_link.short_description = 'Flow'
    flow_link.admin_order_field = 'flow__name'

    def user_link(self, obj):
        url = f'/admin/auth/user/{obj.user.id}/change/'
        return format_html('<a href="{}">{}</a>', url, obj.user.username)
    user_link.short_description = 'User'
    user_link.admin_order_field = 'user__username'

    def status_badge(self, obj):
        colors = {
            'running': '#2196F3', 'completed': '#4CAF50',
            'failed': '#F44336', 'cancelled': '#9E9E9E',
        }
        color = colors.get(obj.status, '#9E9E9E')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px; font-weight: bold;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    status_badge.admin_order_field = 'status'

    def progress_display(self, obj):
        return f"{obj.current_step}/{obj.total_steps}"
    progress_display.short_description = 'Progress'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('flow', 'user', 'chat_session')


@admin.register(SkillExecutionLog)
class SkillExecutionLogAdmin(admin.ModelAdmin):
    """Admin interface for Skill Execution Logs"""

    list_display = ('id', 'skill_link', 'user_link', 'status_badge', 'duration_display', 'executed_at')
    list_filter = ('status', 'executed_at', 'user')
    search_fields = ('skill__name', 'user__username', 'error_message')
    readonly_fields = ('executed_at', 'input_data', 'output_data')

    fieldsets = (
        ('Execution Info', {
            'fields': ('skill', 'user', 'status', 'flow_execution'),
        }),
        ('Data', {
            'fields': ('input_data', 'output_data'),
        }),
        ('Performance', {
            'fields': ('duration_ms',),
        }),
        ('Error', {
            'fields': ('error_message',),
            'classes': ('collapse',),
        }),
        ('Timestamp', {
            'fields': ('executed_at',),
            'classes': ('collapse',),
        }),
    )

    def skill_link(self, obj):
        url = f'/admin/chatbot/skill/{obj.skill.id}/change/'
        return format_html('<a href="{}">{}</a>', url, obj.skill.name)
    skill_link.short_description = 'Skill'
    skill_link.admin_order_field = 'skill__name'

    def user_link(self, obj):
        url = f'/admin/auth/user/{obj.user.id}/change/'
        return format_html('<a href="{}">{}</a>', url, obj.user.username)
    user_link.short_description = 'User'
    user_link.admin_order_field = 'user__username'

    def status_badge(self, obj):
        color = '#4CAF50' if obj.status == 'success' else '#F44336'
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px; font-weight: bold;">{}</span>',
            color, obj.status
        )
    status_badge.short_description = 'Status'
    status_badge.admin_order_field = 'status'

    def duration_display(self, obj):
        if obj.duration_ms:
            return f"{obj.duration_ms}ms"
        return '-'
    duration_display.short_description = 'Duration'
    duration_display.admin_order_field = 'duration_ms'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('skill', 'user', 'flow_execution')


@admin.register(SkillFeedback)
class SkillFeedbackAdmin(admin.ModelAdmin):
    """Admin interface for Skill Feedback"""

    list_display = ('id', 'skill_link', 'user_link', 'rating_stars', 'applied_badge', 'created_at')
    list_filter = ('rating', 'applied', 'created_at')
    search_fields = ('skill__name', 'user__username', 'comment')
    readonly_fields = ('created_at', 'applied_at')

    fieldsets = (
        ('Feedback', {
            'fields': ('skill', 'user', 'execution_log', 'rating', 'comment', 'expected_output'),
        }),
        ('Improvement', {
            'fields': ('applied', 'applied_at'),
        }),
        ('Timestamp', {
            'fields': ('created_at',),
            'classes': ('collapse',),
        }),
    )

    def skill_link(self, obj):
        url = f'/admin/chatbot/skill/{obj.skill.id}/change/'
        return format_html('<a href="{}">{}</a>', url, obj.skill.name)
    skill_link.short_description = 'Skill'
    skill_link.admin_order_field = 'skill__name'

    def user_link(self, obj):
        url = f'/admin/auth/user/{obj.user.id}/change/'
        return format_html('<a href="{}">{}</a>', url, obj.user.username)
    user_link.short_description = 'User'
    user_link.admin_order_field = 'user__username'

    def rating_stars(self, obj):
        filled = int(obj.rating)
        stars = '<span style="color: #FFD700;">' + ('&#9733;' * filled) + ('&#9734;' * (5 - filled)) + '</span>'
        return format_html(stars)
    rating_stars.short_description = 'Rating'
    rating_stars.admin_order_field = 'rating'

    def applied_badge(self, obj):
        if obj.applied:
            return format_html('<span style="color: green; font-weight: bold;">Applied</span>')
        return format_html('<span style="color: #a0a0a0;">Pending</span>')
    applied_badge.short_description = 'Applied'
    applied_badge.admin_order_field = 'applied'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('skill', 'user', 'execution_log')