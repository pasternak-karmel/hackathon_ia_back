"""
API Views pour l'extraction des coordonnées des levés topographiques béninois
Avec documentation Swagger/OpenAPI complète
"""

import os
import tempfile
import json
from datetime import datetime
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from rest_framework.decorators import api_view, parser_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from drf_spectacular.types import OpenApiTypes

from .utils import get_coordinates, parse_coordinates_response, validate_benin_coordinates, download_file_from_url, calculate_centroid
from .serializers import (
    ExtractCoordinatesResponseSerializer, 
    ErrorResponseSerializer,
    APIInfoSerializer,
    HealthCheckSerializer
)


@extend_schema(
    operation_id='extract_coordinates',
    summary='🗺️ Extraire les coordonnées d\'un levé topographique',
    description='''
    **Extrait automatiquement les coordonnées des bornes à partir d'un fichier de levé topographique.**
    
    Cette API utilise l'intelligence artificielle (Google Gemini) pour analyser l'image ou le PDF 
    et extraire les coordonnées des points de bornage.
    
    ## 📋 Formats supportés:
    - **Images**: PNG, JPG, JPEG
    - **Documents**: PDF
    
    ## 🎯 Processus:
    1. Upload du fichier de levé
    2. Analyse IA du document
    3. Extraction des coordonnées (X, Y)
    4. Validation pour le Bénin (UTM 31N)
    5. Retour des coordonnées valides
    
    ## ⚠️ Limites:
    - Taille max: 50MB
    - Coordonnées valides: X(390k-430k), Y(650k-1.3M)
    ''',
    request={
        'multipart/form-data': {
            'type': 'object',
            'properties': {
                'file': {
                    'type': 'string',
                    'format': 'binary',
                    'description': 'Fichier de levé topographique (PNG, JPG, JPEG, PDF)'
                }
            },
            'required': ['file']
        }
    },
    responses={
        200: ExtractCoordinatesResponseSerializer,
        400: ErrorResponseSerializer,
        500: ErrorResponseSerializer,
    },
    examples=[
        OpenApiExample(
            'Réponse réussie',
            value={
                "success": True,
                "coordinates": [
                    {"x": 392930.09, "y": 699294.99},
                    {"x": 392922.77, "y": 699270.66},
                    {"x": 392919.76, "y": 699249.80}
                ],
                "validation": {
                    "total_extracted": 8,
                    "valid_count": 8,
                    "invalid_count": 0,
                    "success_rate": 100.0,
                    "invalid_coordinates": []
                },
                "metadata": {
                    "filename": "leve_topographique.png",
                    "file_size": 1024000,
                    "file_type": ".png",
                    "processing_status": "success"
                }
            },
            response_only=True,
        ),
    ],
    tags=['🗺️ Extraction de Coordonnées']
)
@csrf_exempt
@api_view(['POST'])
@parser_classes([MultiPartParser, FormParser])
def extract_coordinates(request):
    """
    API endpoint pour extraire les coordonnées d'un levé topographique
    
    POST /api/extract-coordinates/
    
    Body (multipart/form-data):
    - file: Fichier image (PNG, JPG, JPEG) ou PDF du levé topographique
    
    Returns:
    - coordinates: Liste des coordonnées extraites
    - validation: Résultats de validation
    - metadata: Informations sur le traitement
    """
    
    if request.method != 'POST':
        return Response(
            {"error": "Méthode non autorisée. Utilisez POST."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED
        )
    
    # Vérifier qu'un fichier a été envoyé
    if 'file' not in request.FILES:
        return Response(
            {"error": "Aucun fichier fourni. Envoyez un fichier avec la clé 'file'."},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    uploaded_file = request.FILES['file']
    
    # Vérifier le type de fichier
    allowed_extensions = ['.png', '.jpg', '.jpeg', '.pdf']
    file_extension = os.path.splitext(uploaded_file.name)[1].lower()
    
    if file_extension not in allowed_extensions:
        return Response(
            {
                "error": f"Type de fichier non supporté: {file_extension}",
                "allowed_types": allowed_extensions
            },
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Sauvegarder temporairement le fichier
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_file:
            for chunk in uploaded_file.chunks():
                temp_file.write(chunk)
            temp_file_path = temp_file.name
        
        # Extraire les coordonnées avec ton code
        result = get_coordinates(temp_file_path)
        
        # Parser la réponse
        coordinates_raw = result.content if hasattr(result, 'content') else str(result)
        coordinates = parse_coordinates_response(coordinates_raw)
        
        # Valider les coordonnées
        validation = validate_benin_coordinates(coordinates)
        
        # Métadonnées
        metadata = {
            "filename": uploaded_file.name,
            "file_size": uploaded_file.size,
            "file_type": file_extension,
            "processing_status": "success"
        }
        
        # Calculer le centroïde des coordonnées valides
        centroid = calculate_centroid(validation["valid_coordinates"])
        
        response_data = {
            "success": True,
            "coordinates": validation["valid_coordinates"],
            "validation": {
                "total_extracted": validation["total_extracted"],
                "valid_count": validation["valid_count"],
                "invalid_count": validation["invalid_count"],
                "success_rate": round(validation["success_rate"], 2),
                "invalid_coordinates": validation["invalid_coordinates"]
            },
            "metadata": metadata,
            "centroid": centroid,  # NOUVEAU: Centre géométrique des coordonnées
            "raw_response": coordinates_raw[:500] + "..." if len(coordinates_raw) > 500 else coordinates_raw
        }
        
        return Response(response_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {
                "success": False,
                "error": f"Erreur lors du traitement: {str(e)}",
                "metadata": {
                    "filename": uploaded_file.name,
                    "processing_status": "failed"
                }
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    finally:
        # Nettoyer le fichier temporaire
        try:
            if 'temp_file_path' in locals():
                os.unlink(temp_file_path)
        except:
            pass


@extend_schema(
    operation_id='api_info',
    summary='ℹ️ Informations sur l\'API',
    description='Retourne les informations générales sur l\'API d\'extraction des coordonnées.',
    responses={200: APIInfoSerializer},
    tags=['ℹ️ Informations']
)
@api_view(['GET'])
def api_info(request):
    """
    Informations sur l'API
    
    GET /api/info/
    """
    return Response({
        "api_name": "Benin Survey Coordinates Extractor",
        "version": "1.0.0",
        "description": "API pour extraire les coordonnées des levés topographiques béninois",
        "endpoints": {
            "/api/extract-coordinates/": {
                "method": "POST",
                "description": "Extrait les coordonnées d'un fichier de levé",
                "parameters": {
                    "file": "Fichier image (PNG, JPG, JPEG) ou PDF"
                }
            },
            "/api/info/": {
                "method": "GET", 
                "description": "Informations sur l'API"
            }
        },
        "supported_formats": [".png", ".jpg", ".jpeg", ".pdf"],
        "coordinate_system": "UTM 31N (EPSG:32631)",
        "valid_ranges": {
            "x": "390000 - 430000",
            "y": "650000 - 1300000"
        }
    })


@extend_schema(
    operation_id='health_check',
    summary='🏥 Vérification de santé de l\'API',
    description='Vérifie que l\'API fonctionne correctement et que les dépendances sont configurées.',
    responses={200: HealthCheckSerializer},
    tags=['🏥 Monitoring']
)
@api_view(['GET'])
def health_check(request):
    """
    Vérification de santé de l'API
    
    GET /api/health/
    """
    # Vérifier que la clé API Google est configurée
    google_api_key = os.getenv("GOOGLE_API_KEY")
    
    return Response({
        "status": "healthy",
        "google_api_configured": bool(google_api_key),
        "timestamp": datetime.now().isoformat()
    })


@extend_schema(
    operation_id='extract_coordinates_from_url',
    summary='🌐 Extraire les coordonnées depuis une URL (S3, HTTP)',
    description='''
    Permet d'extraire les coordonnées à partir d'un fichier accessible via une URL HTTP(S) 
    (ex: S3 presigned URL, CDN, serveur de fichiers). Le fichier est téléchargé temporairement, 
    puis analysé par l'IA comme pour un upload local.

    ## Formats supportés
    - PNG, JPG, JPEG, PDF

    ## Body JSON attendu
    { "url": "https://exemple.com/levé.pdf" }
    ''',
    request={
        'application/json': {
            'type': 'object',
            'properties': {
                'url': {
                    'type': 'string',
                    'format': 'uri',
                    'description': 'URL HTTP(S) pointant vers le fichier de levé (PNG/JPG/PDF)'
                }
            },
            'required': ['url']
        }
    },
    responses={
        200: ExtractCoordinatesResponseSerializer,
        400: ErrorResponseSerializer,
        500: ErrorResponseSerializer,
    },
    tags=['🗺️ Extraction de Coordonnées']
)
@api_view(['POST'])
def extract_coordinates_from_url(request):
    """
    API endpoint: extraire les coordonnées d'un fichier distant via URL

    POST /api/extract-from-url/
    Body JSON: { "url": "https://.../fichier.pdf" }
    """
    try:
        data = request.data or {}
        url = data.get('url')
        if not url:
            return Response({
                'success': False,
                'error': "Champ 'url' requis"
            }, status=status.HTTP_400_BAD_REQUEST)

        # Télécharger le fichier vers un fichier temporaire
        temp_file_path = download_file_from_url(url)

        # Exécuter l'extraction habituelle
        result = get_coordinates(temp_file_path)
        coordinates_raw = result.content if hasattr(result, 'content') else str(result)
        coordinates = parse_coordinates_response(coordinates_raw)
        validation = validate_benin_coordinates(coordinates)

        # Métadonnées avec URL convertie si nécessaire
        from .utils import convert_github_url_to_raw
        converted_url = convert_github_url_to_raw(url)
        metadata = {
            'source_url': url,
            'converted_url': converted_url if converted_url != url else None,
            'processing_status': 'success'
        }

        # Calculer le centroïde des coordonnées valides
        centroid = calculate_centroid(validation['valid_coordinates'])
        
        response_data = {
            'success': True,
            'coordinates': validation['valid_coordinates'],
            'validation': {
                'total_extracted': validation['total_extracted'],
                'valid_count': validation['valid_count'],
                'invalid_count': validation['invalid_count'],
                'success_rate': round(validation['success_rate'], 2),
                'invalid_coordinates': validation['invalid_coordinates']
            },
            'metadata': metadata,
            'centroid': centroid,  # NOUVEAU: Centre géométrique des coordonnées
            'raw_response': coordinates_raw[:500] + '...' if len(coordinates_raw) > 500 else coordinates_raw
        }

        return Response(response_data, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({
            'success': False,
            'error': f"Erreur lors du traitement: {str(e)}"
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    finally:
        try:
            if 'temp_file_path' in locals() and temp_file_path and os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
        except Exception:
            pass
