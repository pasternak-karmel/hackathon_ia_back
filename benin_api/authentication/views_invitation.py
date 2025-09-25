from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import get_user_model
from .models_invitation import Invitation
from .serializers_invitation import InvitationRegisterSerializer
from Equipe.models import Organisation
from django.utils import timezone
from django.db import transaction

Utilisateur = get_user_model()

class RegisterWithInvitationView(APIView):
    permission_classes = []  # Public endpoint

    def post(self, request):
        serializer = InvitationRegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        token = serializer.validated_data['token']
        email = serializer.validated_data['email']
        password = serializer.validated_data['password']
        try:
            invitation = Invitation.objects.select_related('organisation').get(token=token, used=False)
        except Invitation.DoesNotExist:
            return Response({'error': "Lien d'invitation invalide ou déjà utilisé."}, status=400)
        if invitation.is_expired():
            return Response({'error': "Lien d'invitation expiré."}, status=400)
        if invitation.email.lower() != email.lower():
            return Response({'error': "L'email ne correspond pas à l'invitation."}, status=400)
        with transaction.atomic():
            user = Utilisateur.objects.create_user(
                email=email,
                password=password
            )
            invitation.organisation.membres.add(user)
            invitation.mark_used()
        return Response({'message': 'Inscription réussie. Vous avez rejoint l’organisation.'}, status=201)
