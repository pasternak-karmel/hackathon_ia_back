"""
Serializers pour l'API des conversations du chatbot
"""

from rest_framework import serializers
from .models import Conversation, Message

class MessageSerializer(serializers.ModelSerializer):
    """
    Serializer pour les messages
    """
    class Meta:
        model = Message
        fields = ['id', 'role', 'content', 'timestamp', 'context_used']
        read_only_fields = ['id', 'timestamp']

class ConversationListSerializer(serializers.ModelSerializer):
    """
    Serializer pour la liste des conversations (vue simplifiée)
    """
    messages_count = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    
    class Meta:
        model = Conversation
        fields = ['id', 'title', 'created_at', 'updated_at', 'messages_count', 'last_message']
    
    def get_messages_count(self, obj):
        return obj.get_messages_count()
    
    def get_last_message(self, obj):
        last_msg = obj.get_last_message()
        if last_msg:
            return {
                'role': last_msg.role,
                'content': last_msg.content[:100] + '...' if len(last_msg.content) > 100 else last_msg.content,
                'timestamp': last_msg.timestamp
            }
        return None

class ConversationDetailSerializer(serializers.ModelSerializer):
    """
    Serializer pour le détail d'une conversation avec tous les messages
    """
    messages = MessageSerializer(many=True, read_only=True)
    messages_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Conversation
        fields = ['id', 'title', 'created_at', 'updated_at', 'is_active', 'messages', 'messages_count']
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_messages_count(self, obj):
        return obj.get_messages_count()

class ConversationCreateSerializer(serializers.ModelSerializer):
    """
    Serializer pour créer une nouvelle conversation
    """
    class Meta:
        model = Conversation
        fields = ['title']
        
    def create(self, validated_data):
        # Ajouter l'utilisateur si disponible
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            validated_data['user'] = request.user
        return super().create(validated_data)
