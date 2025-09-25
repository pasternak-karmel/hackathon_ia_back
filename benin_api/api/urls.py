"""
URLs pour l'API d'extraction des coordonnées
"""

from django.urls import path
from . import views

urlpatterns = [
    path('extract-coordinates/', views.extract_coordinates, name='extract_coordinates'),
    path('extract-from-url/', views.extract_coordinates_from_url, name='extract_coordinates_from_url'),
    path('info/', views.api_info, name='api_info'),
    path('health/', views.health_check, name='health_check'),
]
