"""
URLs pour l'API chatbot expert foncier béninois
"""

from django.urls import path
from . import views

urlpatterns = [
    # Endpoint principal pour poser une question (avec streaming intégré)
    path('ask/', views.ask_chatbot, name='chatbot_ask'),
    
    # Conversation avec historique
    path('conversation/', views.chatbot_conversation, name='chatbot_conversation'),
    
    # Health check
    path('health/', views.chatbot_health, name='chatbot_health'),
    
    # Informations sur le chatbot
    path('info/', views.chatbot_info, name='chatbot_info'),
]
