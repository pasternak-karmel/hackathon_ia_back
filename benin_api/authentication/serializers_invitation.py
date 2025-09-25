from rest_framework import serializers
from .models_invitation import Invitation

class InvitationRegisterSerializer(serializers.Serializer):
    token = serializers.CharField()
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate_token(self, value):
        try:
            invitation = Invitation.objects.get(token=value, used=False)
        except Invitation.DoesNotExist:
            raise serializers.ValidationError("Lien d'invitation invalide ou déjà utilisé.")
        if invitation.is_expired():
            raise serializers.ValidationError("Lien d'invitation expiré.")
        return value
