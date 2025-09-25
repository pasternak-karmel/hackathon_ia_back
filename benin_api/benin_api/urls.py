"""
URL configuration for benin_api project.
API pour l'extraction des coordonnées des levés topographiques béninois
"""
from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

def api_root(request):
    """Page d'accueil de l'API avec liens vers la documentation"""
    return JsonResponse({
        "message": "🗺️ API d'extraction des coordonnées des levés topographiques béninois",
        "version": "1.0.0",
        "hackathon": "Hackathon Foncier Bénin 2025 🇧🇯",
        "documentation": {
            "swagger_ui": "/api/docs/",
            "redoc": "/api/redoc/",
            "openapi_schema": "/api/schema/"
        },
        "endpoints": {
            "/api/extract-coordinates/": "Extraction des coordonnées (POST)",
            "/api/info/": "Informations sur l'API (GET)",
            "/api/health/": "Vérification de santé (GET)"
        },
        "supported_formats": ["PNG", "JPG", "JPEG", "PDF"],
        "coordinate_system": "UTM 31N (EPSG:32631)",
        "description": "Envoyez vos fichiers de levés topographiques pour extraire automatiquement les coordonnées avec l'IA"
    })

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),
    
    # API endpoints
    path('api/', include('api.urls')),
    
    # Documentation Swagger/OpenAPI
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    
    # Page d'accueil
    path('', api_root, name='api_root'),
]
