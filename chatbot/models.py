from django.db import models
from django.contrib.auth.models import User
import markdown
from django.utils.safestring import mark_safe
md = markdown.Markdown(extensions=["fenced_code", "tables"])

# Create your models here.
class ChatSession(models.Model):
    """Represents a conversation session for a user"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_sessions')
    name = models.CharField(max_length=200, default='Chat')
    model = models.CharField(max_length=100, default='gemini-2.0-flash')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
        ]

    def __str__(self):
        return f'{self.user.username} - {self.name}'


class Chat(models.Model):
    """Represents a single message exchange in a chat session"""
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages', null=True, blank=True)
    message = models.TextField()
    response = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_deleted = models.BooleanField(default=False)

    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['session', 'created_at']),
        ]

    def __str__(self):
        return f'{self.session.name} - {self.message[:50]}'

    def response_md(self):
        return mark_safe(md.convert(self.response))


# ========== TASK MANAGEMENT MODEL ==========

class Task(models.Model):
    """Represents a personal task or todo item for a user"""

    # Priority levels
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]

    # Status choices
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    # User and basic info
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tasks')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, default='')

    # Priority and status
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    # Dates
    due_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    # Optional link to chat message that created it
    created_from_chat = models.ForeignKey(Chat, null=True, blank=True, on_delete=models.SET_NULL, related_name='created_tasks')

    class Meta:
        ordering = ['-priority', '-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['user', '-due_date']),
            models.Index(fields=['user', '-created_at']),
        ]

    def __str__(self):
        return f'{self.user.username} - {self.title} ({self.get_status_display()})'

    def get_priority_color(self):
        """Return color code for priority"""
        colors = {
            'low': '#4CAF50',      # Green
            'medium': '#2196F3',   # Blue
            'high': '#FF9800',     # Orange
            'urgent': '#F44336',   # Red
        }
        return colors.get(self.priority, '#2196F3')

    def is_overdue(self):
        """Check if task is overdue"""
        if self.due_date and self.status != 'completed':
            from django.utils import timezone
            return timezone.now() > self.due_date
        return False

    def days_until_due(self):
        """Calculate days remaining until due date"""
        if self.due_date:
            from django.utils import timezone
            from datetime import timedelta
            diff = self.due_date - timezone.now()
            return diff.days
        return None


# ========== NOTIFICATION SYSTEM MODELS (PHASE 4) ==========

class Notification(models.Model):
    """Tracks notifications sent to users"""

    NOTIFICATION_TYPES = [
        ('deadline_reminder', 'Deadline Reminder'),
        ('task_due_today', 'Task Due Today'),
        ('task_overdue', 'Task Overdue'),
        ('task_completed', 'Task Completed'),
        ('recurring_created', 'Recurring Task Created'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    task = models.ForeignKey(Task, on_delete=models.CASCADE, null=True, blank=True, related_name='notifications')
    notification_type = models.CharField(max_length=50, choices=NOTIFICATION_TYPES)
    subject = models.CharField(max_length=200)
    message = models.TextField()
    is_sent = models.BooleanField(default=False)
    sent_at = models.DateTimeField(null=True, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    attempts = models.IntegerField(default=0)
    last_error = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['user', 'is_sent']),
        ]

    def __str__(self):
        return f'{self.user.username} - {self.get_notification_type_display()}'

    def mark_as_read(self):
        """Mark notification as read"""
        if not self.read_at:
            from django.utils import timezone
            self.read_at = timezone.now()
            self.save()


class NotificationPreference(models.Model):
    """User's notification settings"""

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='notification_preferences')
    deadline_reminder_enabled = models.BooleanField(default=True)
    reminder_days_before = models.IntegerField(default=1)
    reminder_time = models.TimeField(default='09:00')
    overdue_reminder_enabled = models.BooleanField(default=True)
    daily_digest_enabled = models.BooleanField(default=False)
    digest_time = models.TimeField(default='08:00')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Notification Preferences"

    def __str__(self):
        return f'{self.user.username} - Notification Settings'


# ========== RECURRING TASK MODELS (PHASE 4) ==========

class RecurringTaskTemplate(models.Model):
    """Template for recurring tasks"""

    FREQUENCY_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('biweekly', 'Bi-weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('yearly', 'Yearly'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='recurring_tasks')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, default='')
    priority = models.CharField(max_length=20, choices=Task.PRIORITY_CHOICES, default='medium')
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    last_instance_created = models.DateTimeField(null=True, blank=True)
    next_instance_date = models.DateTimeField()

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['user', 'next_instance_date']),
        ]

    def __str__(self):
        return f'{self.user.username} - {self.title} ({self.get_frequency_display()})'

    def get_frequency_display(self):
        """Return human-readable frequency"""
        freq_map = dict(self.FREQUENCY_CHOICES)
        return freq_map.get(self.frequency, 'Unknown')


class RecurringTaskInstance(models.Model):
    """Tracks individual instances of recurring tasks"""

    template = models.ForeignKey(RecurringTaskTemplate, on_delete=models.CASCADE, related_name='instances')
    task = models.OneToOneField(Task, on_delete=models.CASCADE, related_name='recurring_instance')
    created_at = models.DateTimeField(auto_now_add=True)
    instance_number = models.IntegerField()

    class Meta:
        ordering = ['-created_at']
        unique_together = ('template', 'task')

    def __str__(self):
        return f'{self.template.title} - Instance {self.instance_number}'


# ========== ANALYTICS MODELS (PHASE 5) ==========

class TaskAnalytics(models.Model):
    """Daily task analytics snapshot for trending and reporting"""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='task_analytics')
    date = models.DateField()
    total_tasks = models.IntegerField()
    pending_count = models.IntegerField()
    in_progress_count = models.IntegerField()
    completed_count = models.IntegerField()
    overdue_count = models.IntegerField()
    completed_today = models.IntegerField()
    completion_rate = models.FloatField()
    urgent_count = models.IntegerField()
    high_count = models.IntegerField()
    medium_count = models.IntegerField()
    low_count = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'date')
        ordering = ['-date']
        indexes = [
            models.Index(fields=['user', '-date']),
        ]
        verbose_name_plural = "Task Analytics"

    def __str__(self):
        return f'{self.user.username} - {self.date}'


class ChatAnalytics(models.Model):
    """Daily chat activity analytics"""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_analytics')
    date = models.DateField()
    total_messages = models.IntegerField()
    user_messages = models.IntegerField()
    ai_responses = models.IntegerField()
    total_sessions = models.IntegerField()
    active_sessions = models.IntegerField()
    avg_session_length = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'date')
        ordering = ['-date']
        indexes = [
            models.Index(fields=['user', '-date']),
        ]
        verbose_name_plural = "Chat Analytics"

    def __str__(self):
        return f'{self.user.username} - {self.date}'


# ========== CLAUDE TERMINAL INTEGRATION ==========

class ClaudeTerminalSession(models.Model):
    """Represents a Claude Code terminal session linked to a web chat"""

    CONNECTION_CHOICES = [
        ('http', 'HTTP Proxy'),
        ('ipc', 'Inter-Process Communication'),
        ('file', 'File Queue'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='claude_terminals')
    web_chat_session = models.OneToOneField(ChatSession, on_delete=models.SET_NULL, null=True, blank=True, related_name='terminal_session')

    # Process management
    terminal_pid = models.IntegerField(null=True, blank=True, help_text="Process ID of Claude terminal")
    is_active = models.BooleanField(default=False, help_text="Terminal is running and connected")
    is_enabled = models.BooleanField(default=False, help_text="Terminal mode enabled for this session")

    # Connection configuration
    connection_method = models.CharField(
        max_length=10,
        choices=CONNECTION_CHOICES,
        default='http',
        help_text="Communication method (HTTP, IPC, or File)"
    )
    connection_config = models.JSONField(
        default=dict,
        blank=True,
        help_text="Connection config (port for HTTP, pipe path for IPC, queue dir for File)"
    )

    # Status and monitoring
    started_at = models.DateTimeField(null=True, blank=True)
    last_message_at = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True, help_text="Last error message if any")
    error_count = models.IntegerField(default=0)

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['is_active', '-updated_at']),
        ]
        verbose_name = "Claude Terminal Session"
        verbose_name_plural = "Claude Terminal Sessions"

    def __str__(self):
        status = "Active" if self.is_active else "Inactive"
        method = self.get_connection_method_display()
        return f'{self.user.username} - {method} ({status})'

    @property
    def is_connected(self):
        """Check if terminal is currently connected"""
        return self.is_active and self.terminal_pid is not None

    @property
    def uptime_seconds(self):
        """Get terminal uptime in seconds"""
        if not self.started_at:
            return 0
        from django.utils import timezone
        return int((timezone.now() - self.started_at).total_seconds())

    def mark_error(self, error_message):
        """Record an error and increment error count"""
        self.last_error = error_message[:500]  # Truncate long errors
        self.error_count += 1
        self.save()

    def clear_error(self):
        """Clear error state"""
        self.last_error = ''
        self.error_count = 0
        self.save()
