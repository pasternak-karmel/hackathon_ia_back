"""
URLs pour l'API chatbot expert foncier béninois
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Router pour les ViewSets
router = DefaultRouter()
router.register(r'conversations', views.ConversationViewSet, basename='conversation')

urlpatterns = [
    # Endpoints existants
    path('ask/', views.ask_chatbot, name='chatbot_ask'),  # MAINTENANT AVEC SAUVEGARDE AUTO
    path('conversation/', views.chatbot_conversation, name='chatbot_conversation'),
    path('health/', views.chatbot_health, name='chatbot_health'),
    path('info/', views.chatbot_info, name='chatbot_info'),
    
    # Nouveaux endpoints simples pour récupérer les conversations
    path('conversations-list/', views.get_all_conversations, name='get_all_conversations'),
    path('conversation/<uuid:conversation_id>/messages/', views.get_conversation_messages, name='get_conversation_messages'),
    
    # Routes complètes pour les conversations (ViewSet)
    path('', include(router.urls)),
]
