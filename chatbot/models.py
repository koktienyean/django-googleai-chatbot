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
