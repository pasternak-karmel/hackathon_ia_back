from django.db import models
from django.utils import timezone
from django.conf import settings
import uuid

class Invitation(models.Model):
    email = models.EmailField()
    organisation = models.ForeignKey('Equipe.Organisation', on_delete=models.CASCADE, related_name='auth_invitations')
    token = models.CharField(max_length=64, unique=True, default=uuid.uuid4)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)
    used_at = models.DateTimeField(null=True, blank=True)

    def is_expired(self):
        return timezone.now() > self.expires_at

    def mark_used(self):
        self.used = True
        self.used_at = timezone.now()
        self.save()

    def __str__(self):
        return f"Invitation {self.email} pour {self.organisation.nom_entreprise} (utilisée: {self.used})"
