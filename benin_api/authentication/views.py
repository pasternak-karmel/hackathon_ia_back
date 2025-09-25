from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model, authenticate, login
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.tokens import default_token_generator
from django.contrib.sites.shortcuts import get_current_site
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import InvalidToken
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .logging_config import get_auth_logger
from .serializers import UserRegistrationSerializer, UtilisateurSerializer
from django.core.exceptions import ImproperlyConfigured
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError


from django.utils.encoding import force_str  # Remplacez force_text par force_str




from django.utils.http import urlsafe_base64_decode
from django.contrib.auth.tokens import default_token_generator
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import get_user_model



logger = get_auth_logger()
Utilisateur = get_user_model()

class UtilisateurViewSet(viewsets.ModelViewSet):
    queryset = Utilisateur.objects.all()
    serializer_class = UtilisateurSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        if self.action in ['inscriptions', 'connexion', 'verify_activation', 'me', 'forgot_password', 'reset_password']:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    @action(detail=False, methods=['post'], permission_classes=[permissions.AllowAny])
    def forgot_password(self, request):
        """
        Endpoint pour demander la réinitialisation du mot de passe.
        """
        from .serializers import PasswordResetRequestSerializer
        serializer = PasswordResetRequestSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            try:
                user = Utilisateur.objects.get(email=email)
            except Utilisateur.DoesNotExist:
                # Toujours retourner succès pour ne pas divulguer l'existence d'un compte
                return Response({'message': "Un email de réinitialisation a été envoyé si l'adresse existe."}, status=status.HTTP_200_OK)
            # Génère le token et le lien
            from django.utils.http import urlsafe_base64_encode
            from django.utils.encoding import force_bytes
            from django.contrib.auth.tokens import default_token_generator
            uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            # FRONTEND_URL obligatoire
            frontend_url = getattr(settings, 'FRONTEND_URL', None)
            if not frontend_url:
                return Response({'error': "FRONTEND_URL n'est pas défini dans settings.py"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            reset_url = f"{frontend_url.rstrip('/')}/reset-password/{uidb64}/{token}/"
            # Envoi mail
            subject = 'Réinitialisation de votre mot de passe'
            message = render_to_string('reset_password_email.html', {'reset_url': reset_url})
            try:
                send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email], html_message=message)
            except Exception as e:
                return Response({'error': f"Erreur lors de l'envoi de l'email: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            return Response({'message': "Un email de réinitialisation a été envoyé si l'adresse existe."}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], permission_classes=[permissions.AllowAny])
    def reset_password(self, request):
        """
        Endpoint pour confirmer la réinitialisation du mot de passe.
        """
        from .serializers import PasswordResetConfirmSerializer
        serializer = PasswordResetConfirmSerializer(data=request.data)
        if serializer.is_valid():
            uidb64 = serializer.validated_data['uid']
            token = serializer.validated_data['token']
            new_password = serializer.validated_data['new_password']
            from django.utils.encoding import force_str
            from django.utils.http import urlsafe_base64_decode
            from django.contrib.auth.tokens import default_token_generator
            try:
                uid = force_str(urlsafe_base64_decode(uidb64))
                user = Utilisateur.objects.get(pk=uid)
            except (TypeError, ValueError, OverflowError, Utilisateur.DoesNotExist):
                return Response({'error': 'Lien invalide ou utilisateur inexistant.'}, status=status.HTTP_400_BAD_REQUEST)
            if not default_token_generator.check_token(user, token):
                return Response({'error': 'Le lien de réinitialisation est invalide ou a expiré.'}, status=status.HTTP_400_BAD_REQUEST)
            user.set_password(new_password)
            user.save()
            # Optionnel : on peut rendre le compte actif si inactif
            if not user.est_actif:
                user.est_actif = True
                user.save()
            return Response({'message': 'Votre mot de passe a été réinitialisé avec succès.'}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


    
    

    @swagger_auto_schema(
    operation_description="Inscription avec email et mot de passe uniquement",
    request_body=UserRegistrationSerializer,
    responses={201: openapi.Response(description="Un email d'activation a été envoyé")}
)
    @action(detail=False, methods=['post'], permission_classes=[permissions.AllowAny])
    def inscriptions(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            
            # Vérification et utilisation de FRONTEND_URL
            if not hasattr(settings, 'FRONTEND_URL') or not settings.FRONTEND_URL:
                raise ImproperlyConfigured("FRONTEND_URL n'est pas défini dans settings.py")
            
            # Création du lien d'activation
            frontend_url = settings.FRONTEND_URL.rstrip('/')  # Retire le slash final s'il existe
            activation_path = f"activation/{urlsafe_base64_encode(force_bytes(user.pk))}/token/{default_token_generator.make_token(user)}"
            activation_url = f"{frontend_url}/{activation_path}"
            
            # Envoi de l'email
            mail_subject = 'Activez votre compte'
            message = render_to_string('authentication/activation_email.html', {
                'user': user,
                'activation_url': activation_url,
            })
            
            try:
                send_mail(
                    mail_subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    [user.email],
                    html_message=message
                )
                
                # Génération des tokens JWT
                refresh = RefreshToken.for_user(user)
                
                return Response({
                    'message': "Un email d'activation a été envoyé à votre adresse email.",
                    'activation_url': activation_url,  # Pour le développement
                    'user_id': user.id
                }, status=status.HTTP_201_CREATED)
                
            except Exception as e:
                # En cas d'erreur d'envoi, supprimer l'utilisateur
                user.delete()
                return Response({
                    'error': f"Erreur lors de l'envoi de l'email d'activation: {str(e)}"
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)





    @action(detail=False, methods=['post'], permission_classes=[permissions.AllowAny])
    def connexion(self, request):
        email = request.data.get('email')
        password = request.data.get('password')

        if not email or not password:
            return Response({
                'error': 'Email et mot de passe requis'
            }, status=status.HTTP_400_BAD_REQUEST)

        user = authenticate(request, email=email, password=password)

        if user and user.est_actif:
            refresh = RefreshToken.for_user(user)
            return Response({
                "token": str(refresh.access_token),
                "refresh": str(refresh),
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "first_name": user.first_name or "",
                    "last_name": user.last_name or "",
                    "telephone": user.telephone or "",
                    "type_utilisateur": user.type_utilisateur,
                    "image": user.image if user.image else None,
                    "est_actif": user.est_actif,
                    "peut_modifier_fichier": getattr(user, "peut_modifier_fichier", False),
                    "peut_creer_reunion": getattr(user, "peut_creer_reunion", False),
                    "peut_utiliser_ia": getattr(user, "peut_utiliser_ia", False)
                }
            })
        elif user and not user.est_actif:
            return Response({
                'error': "Veuillez activer votre compte via le lien envoyé par email"
            }, status=status.HTTP_401_UNAUTHORIZED)
        else:
            return Response({
                'error': "Email ou mot de passe incorrect"
            }, status=status.HTTP_401_UNAUTHORIZED)
        

    @swagger_auto_schema(
        operation_description="Active le compte d'un utilisateur via le lien d'activation",
        responses={
            200: openapi.Response(description="Compte activé avec succès", examples={'application/json': {'message': 'Votre compte a été activé'}}),
            400: openapi.Response(description="Lien d'activation invalide", examples={'application/json': {'error': "Lien invalide ou expiré"}})
        }
    )
    

    
    
    @action(detail=False, methods=['post'], permission_classes=[permissions.AllowAny])
    def verify_activation(self, request):
        try:
            uidb64 = request.data.get('uid')
            token = request.data.get('token')
            
            if not uidb64 or not token:
                return Response({
                    'error': 'UID et token requis'
                }, status=status.HTTP_400_BAD_REQUEST)

            try:
                uid = force_str(urlsafe_base64_decode(uidb64))
                user = Utilisateur.objects.get(pk=uid)
            except (TypeError, ValueError, OverflowError, Utilisateur.DoesNotExist):
                return Response({
                    'error': 'Utilisateur invalide'
                }, status=status.HTTP_400_BAD_REQUEST)

            if default_token_generator.check_token(user, token):
                user.est_actif = True
                user.save()
                return Response({
                    'message': 'Votre compte a été activé avec succès'
                })
            else:
                return Response({
                    'error': 'Le lien d\'activation est invalide ou a expiré'
                }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)





    @action(detail=False, methods=['get'])
    def me(self, request):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_description="Modification du mot de passe",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['old_password', 'new_password', 'confirm_password'],
            properties={
                'old_password': openapi.Schema(type=openapi.TYPE_STRING, description="Ancien mot de passe"),
                'new_password': openapi.Schema(type=openapi.TYPE_STRING, description="Nouveau mot de passe"),
                'confirm_password': openapi.Schema(type=openapi.TYPE_STRING, description="Confirmation du nouveau mot de passe")
            }
        ),
        responses={
            200: openapi.Response(description="Mot de passe modifié avec succès"),
            400: openapi.Response(description="Erreur dans les données fournies")
        }
    )
    @action(detail=False, methods=['patch'], permission_classes=[permissions.IsAuthenticated])
    def change_password(self, request):
        user = request.user
        old_password = request.data.get('old_password')
        new_password = request.data.get('new_password')
        confirm_password = request.data.get('confirm_password')

        # Vérification de l'ancien mot de passe
        if not user.check_password(old_password):
            return Response({
                'error': "L'ancien mot de passe est incorrect"
            }, status=status.HTTP_400_BAD_REQUEST)

        # Vérification de la correspondance des nouveaux mots de passe
        if new_password != confirm_password:
            return Response({
                'error': "Les nouveaux mots de passe ne correspondent pas"
            }, status=status.HTTP_400_BAD_REQUEST)

        # Validation du nouveau mot de passe
        try:
            validate_password(new_password, user)
        except ValidationError as e:
            return Response({
                'error': list(e.messages)
            }, status=status.HTTP_400_BAD_REQUEST)

        # Modification du mot de passe
        user.set_password(new_password)
        user.save()

        return Response({
            'message': "Mot de passe modifié avec succès"
        })

    @swagger_auto_schema(
        operation_description="Modification des informations du profil",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'email': openapi.Schema(type=openapi.TYPE_STRING, description="Email"),
                'first_name': openapi.Schema(type=openapi.TYPE_STRING, description="Prénom"),
                'last_name': openapi.Schema(type=openapi.TYPE_STRING, description="Nom"),
                'telephone': openapi.Schema(type=openapi.TYPE_STRING, description="Numéro de téléphone"),
                'image': openapi.Schema(type=openapi.TYPE_STRING, description="URL de l'image de profil"),
                'type_utilisateur': openapi.Schema(
                    type=openapi.TYPE_STRING, 
                    description="Type d'utilisateur",
                    enum=['ADMIN', 'MEMBRE_CSE', 'EMPLOYE', 'RESPONSABLE']
                )
            }
        ),
        responses={
            200: openapi.Response(description="Profil mis à jour avec succès"),
            400: openapi.Response(description="Erreur dans les données fournies"),
            403: openapi.Response(description="Permission refusée")
        }
    )
    @action(detail=False, methods=['patch'], permission_classes=[permissions.IsAuthenticated])
    def update_profile(self, request):
        user = request.user
        
        # Vérifier si l'utilisateur a les permissions pour changer le type_utilisateur
        new_type = request.data.get('type_utilisateur')
        if new_type and not request.user.is_superuser:
            return Response({
                'error': "Seuls les administrateurs peuvent modifier le type d'utilisateur"
            }, status=status.HTTP_403_FORBIDDEN)

        serializer = self.get_serializer(user, data=request.data, partial=True)

        if serializer.is_valid():
            # Vérifier l'email uniquement s'il est dans la requête
            new_email = request.data.get('email')
            if new_email and new_email != user.email:
                if Utilisateur.objects.filter(email=new_email).exists():
                    return Response({
                        'error': "Cet email est déjà utilisé"
                    }, status=status.HTTP_400_BAD_REQUEST)

            serializer.save()
            return Response({
                'message': "Profil mis à jour avec succès",
                'user': serializer.data
            })

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



class CustomTokenObtainPairView(TokenObtainPairView):
    def get_user(self, credentials):
        email = credentials.get('email')
        password = credentials.get('password')
        user = authenticate(email=email, password=password)
        if not user:
            raise InvalidToken({'detail': 'Aucun compte actif trouvé'})
        return user

    @swagger_auto_schema(
        operation_description="Authentifie un utilisateur et retourne les tokens JWT",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['email', 'password'],
            properties={
                'email': openapi.Schema(type=openapi.TYPE_STRING, description="Email"),
                'password': openapi.Schema(type=openapi.TYPE_STRING, description="Mot de passe")
            }
        ),
        responses={
            200: openapi.Response(
                description="Authentification réussie",
                examples={'application/json': {'access': 'string', 'refresh': 'string'}}
            ),
            401: openapi.Response(description="Identifiants invalides")
        }
    )
    def post(self, request, *args, **kwargs):
        user = self.get_user(request.data)
        if not user.is_active:
            return Response({'detail': "Votre compte n'est pas activé."}, status=status.HTTP_401_UNAUTHORIZED)
        response = super().post(request, *args, **kwargs)
        response.data.update({'user_id': user.id, 'email': user.email})
        return response











    
