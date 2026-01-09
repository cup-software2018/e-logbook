from django.db import models
from django.contrib.auth.models import User, Group
from django.utils import timezone
from .constants import LOGBOOK_TYPES, LOGBOOK_PROPERTIES

class Logbook(models.Model):
    # Access Level Choices
    ACCESS_CHOICES = [
        ('private', 'Private (Owner only)'),
        ('shared', 'Shared (Group Members)'),
        ('public', 'Public (All Users)'),
    ]

    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    # Owner relationship
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='owned_logbooks')
    
    # [New] Group Sharing Logic
    # Specifies which groups can access this logbook if access_level is 'shared'
    allowed_groups = models.ManyToManyField(Group, blank=True, related_name='shared_logbooks')
    
    # Access control setting
    access_level = models.CharField(max_length=20, choices=ACCESS_CHOICES, default='private')
    
    # (Optional) Retained for backward compatibility if needed, otherwise can be removed
    allowed_users = models.ManyToManyField(User, blank=True, related_name='permitted_logbooks')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class Log(models.Model):
    """
    Each Log entry belongs to a specific Logbook.
    """
    logbook = models.ForeignKey(
        Logbook, on_delete=models.CASCADE, related_name='entries'
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    
    # Changed: Added default=timezone.now to prevent errors if not provided.
    # You can still override this manually if needed.
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # Default ordering: Oldest logs first (Chronological order)
        # Change to '-created_at' if you prefer newest on top
        ordering = ['created_at']

    def __str__(self):
        return f"Log by {self.user.username} in {self.logbook.name} at {self.created_at}"


class LogImage(models.Model):
    """
    Stores multiple images for a single Log entry.
    """
    log = models.ForeignKey(
        Log, on_delete=models.CASCADE, related_name='images'
    )
    # Organize uploads by date folder
    image = models.ImageField(upload_to='logs/%Y/%m/%d/')
    width = models.IntegerField(default=400)
    caption = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"Image for Log {self.log.id}"


class Comment(models.Model):
    """
    Stores comments associated with a specific Log.
    """
    log = models.ForeignKey(
        Log, on_delete=models.CASCADE, related_name='comments'
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='comments'
    )
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # Default ordering: Chronological
        ordering = ['created_at']

    def __str__(self):
        return f"Comment by {self.user.username} on Log {self.log.id}"
    