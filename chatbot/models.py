from django.db import models
from django.contrib.auth.models import User
import markdown
from django.utils.safestring import mark_safe
md = markdown.Markdown(extensions=["fenced_code", "tables"])

# Create your models here.


class Chat(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField()
    response = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.user.username}: {self.message}'
    
    def response_md(self):
        return mark_safe(md.convert(self.response))