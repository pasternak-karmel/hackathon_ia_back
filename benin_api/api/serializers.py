"""
Serializers pour l'API d'extraction des coordonnées
"""

from rest_framework import serializers


class CoordinateSerializer(serializers.Serializer):
    """Serializer pour une coordonnée individuelle"""
    x = serializers.FloatField(
        help_text="Coordonnée X en UTM 31N (mètres)",
        min_value=390000,
        max_value=430000
    )
    y = serializers.FloatField(
        help_text="Coordonnée Y en UTM 31N (mètres)", 
        min_value=650000,
        max_value=1300000
    )


class ValidationResultSerializer(serializers.Serializer):
    """Serializer pour les résultats de validation"""
    total_extracted = serializers.IntegerField(
        help_text="Nombre total de coordonnées extraites"
    )
    valid_count = serializers.IntegerField(
        help_text="Nombre de coordonnées valides"
    )
    invalid_count = serializers.IntegerField(
        help_text="Nombre de coordonnées invalides"
    )
    success_rate = serializers.FloatField(
        help_text="Taux de réussite en pourcentage"
    )
    invalid_coordinates = CoordinateSerializer(
        many=True,
        help_text="Liste des coordonnées invalides"
    )


class MetadataSerializer(serializers.Serializer):
    """Serializer pour les métadonnées du fichier"""
    filename = serializers.CharField(
        help_text="Nom du fichier uploadé"
    )
    file_size = serializers.IntegerField(
        help_text="Taille du fichier en octets"
    )
    file_type = serializers.CharField(
        help_text="Extension du fichier (.png, .jpg, .pdf, etc.)"
    )
    processing_status = serializers.CharField(
        help_text="Statut du traitement (success/failed)"
    )


class ExtractCoordinatesResponseSerializer(serializers.Serializer):
    """Serializer pour la réponse d'extraction des coordonnées"""
    success = serializers.BooleanField(
        help_text="Indique si l'extraction a réussi"
    )
    coordinates = CoordinateSerializer(
        many=True,
        help_text="Liste des coordonnées valides extraites"
    )
    validation = ValidationResultSerializer(
        help_text="Résultats de la validation des coordonnées"
    )
    metadata = MetadataSerializer(
        help_text="Métadonnées du fichier traité"
    )
    centroid = CoordinateSerializer(
        help_text="Centre géométrique (centroïde) de toutes les coordonnées valides",
        required=False,
        allow_null=True
    )
    raw_response = serializers.CharField(
        help_text="Réponse brute de l'IA (tronquée à 500 caractères)",
        required=False
    )


class ErrorResponseSerializer(serializers.Serializer):
    """Serializer pour les réponses d'erreur"""
    success = serializers.BooleanField(
        default=False,
        help_text="Toujours False pour les erreurs"
    )
    error = serializers.CharField(
        help_text="Message d'erreur détaillé"
    )
    metadata = MetadataSerializer(
        help_text="Métadonnées du fichier (si disponibles)",
        required=False
    )


class APIInfoSerializer(serializers.Serializer):
    """Serializer pour les informations de l'API"""
    api_name = serializers.CharField()
    version = serializers.CharField()
    description = serializers.CharField()
    endpoints = serializers.DictField()
    supported_formats = serializers.ListField(child=serializers.CharField())
    coordinate_system = serializers.CharField()
    valid_ranges = serializers.DictField()


class HealthCheckSerializer(serializers.Serializer):
    """Serializer pour le health check"""
    status = serializers.CharField(
        help_text="Statut de l'API (healthy/unhealthy)"
    )
    google_api_configured = serializers.BooleanField(
        help_text="Indique si la clé API Google est configurée"
    )
    timestamp = serializers.CharField(
        help_text="Timestamp de la vérification"
    )
