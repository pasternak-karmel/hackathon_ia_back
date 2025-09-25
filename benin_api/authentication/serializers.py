from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from utils.fields import FlexibleURLField

# Récupère le modèle personnalisé d'utilisateur
Utilisateur = get_user_model()

class UtilisateurSerializer(serializers.ModelSerializer):
    """Sérialiseur pour le modèle Utilisateur."""

    password = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'},
        label=_('Mot de passe')
    )

    image = FlexibleURLField(required=False, allow_null=True)

    class Meta:
        model = Utilisateur
        fields = [
            'id', 'email', 'password', 'type_utilisateur', 'telephone','first_name','last_name','image',
            'peut_modifier_fichier', 'peut_creer_reunion', 'peut_utiliser_ia',
            'date_creation', 'date_modification', 'is_active', 'is_last_message_read'
        ]
        read_only_fields = ['id','date_creation', 'date_modification']
        extra_kwargs = {
            'email': {'label': _('Adresse email'), 'required': True},
            'is_active': {'label': _('Est actif')}
        }

    def create(self, validated_data):
        """Crée un nouvel utilisateur avec un mot de passe crypté."""
        password = validated_data.pop('password')
        user = Utilisateur.objects.create(**validated_data)
        user.set_password(password)  # Hachage du mot de passe
        user.save()
        return user

    def update(self, instance, validated_data):
        """Met à jour un utilisateur existant."""
        password = validated_data.pop('password', None)
        user = super().update(instance, validated_data)

        if password:
            user.set_password(password)  # Hachage du nouveau mot de passe
            user.save()

        return user

class UserRegistrationSerializer(serializers.ModelSerializer):
    """Sérialiseur pour l'inscription des utilisateurs."""

    class Meta:
        model = Utilisateur
        fields = ['email', 'password']
        extra_kwargs = {'password': {'write_only': True},
           'email': {'required': True}
        }

    def create(self, validated_data):
        """Créer un utilisateur avec un mot de passe sécurisé."""
        user = Utilisateur.objects.create(
            email=validated_data['email'],
             est_actif=False
        )
        user.set_password(validated_data['password'])  # Hachage du mot de passe
        user.save()
        return user


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)

class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField(required=True)
    token = serializers.CharField(required=True)
    new_password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})

    def validate_new_password(self, value):
        from django.contrib.auth.password_validation import validate_password
        validate_password(value)
        return value
