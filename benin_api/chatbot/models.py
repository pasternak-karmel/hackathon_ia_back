from django.db import models
from django.contrib.auth.models import User
import uuid

class Conversation(models.Model):
    """
    Modèle pour stocker les conversations avec le chatbot
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-updated_at']
    
    def __str__(self):
        return f"Conversation {self.id} - {self.title or 'Sans titre'}"
    
    def get_messages_count(self):
        return self.messages.count()
    
    def get_last_message(self):
        return self.messages.last()

class Message(models.Model):
    """
    Modèle pour stocker les messages dans une conversation
    """
    ROLE_CHOICES = [
        ('user', 'Utilisateur'),
        ('assistant', 'Assistant IA'),
        ('system', 'Système')
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    context_used = models.JSONField(default=dict, blank=True)  # Contexte utilisé pour la réponse
    
    class Meta:
        ordering = ['timestamp']
    
    def __str__(self):
        return f"{self.role}: {self.content[:50]}..."
