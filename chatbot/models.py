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
    model = models.CharField(max_length=100, default='gemini-1.5-flash')
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
    