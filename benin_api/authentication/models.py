from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.db import models
from django.utils.translation import gettext_lazy as _


class UtilisateurManager(BaseUserManager):
    """Gestionnaire personnalisé pour le modèle Utilisateur."""
    
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("L'adresse e-mail est obligatoire")
        email = self.normalize_email(email)
        extra_fields.setdefault('est_actif', True)  # Activation par défaut
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, password, **extra_fields)


class Utilisateur(AbstractBaseUser, PermissionsMixin):
    """Modèle personnalisé pour les utilisateurs du système."""

    email = models.EmailField(unique=True, verbose_name="Adresse e-mail")
    # Changement du champ image en URLField
    image = models.URLField(
        blank=True, 
        null=True,
        verbose_name="URL de l'image de profil"
    )
    first_name = models.CharField(max_length=30, blank=True, verbose_name="Prénom")
    last_name = models.CharField(max_length=30, blank=True, verbose_name="Nom")
    
    type_utilisateur = models.CharField(
        max_length=20,
        choices=[
            ('ADMIN', 'Administrateur'),
            ('MEMBRE_CSE', 'Membre CSE'),
            ('EMPLOYE', 'Employé'),
            ('RESPONSABLE', 'Responsable')
        ],
        default='EMPLOYE',
        verbose_name="Type d'utilisateur"
    )

    telephone = models.CharField(max_length=15, blank=True, verbose_name="Numéro de téléphone")
    date_creation = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")
    date_modification = models.DateTimeField(auto_now=True, verbose_name="Date de modification")
    est_actif = models.BooleanField(default=True, verbose_name="Est actif")
    is_staff = models.BooleanField(default=False, verbose_name="Membre du staff")

    # Permissions personnalisées
    peut_modifier_fichier = models.BooleanField(default=False, verbose_name="Peut modifier/ajouter les fichiers")
    peut_creer_reunion = models.BooleanField(default=False, verbose_name="Peut créer des réunions")
    peut_utiliser_ia = models.BooleanField(default=False, verbose_name="Peut utiliser l'IA")

    is_last_message_read = models.BooleanField(default=False, verbose_name="Dernier message lu")

    objects = UtilisateurManager()

    USERNAME_FIELD = 'email'  # On utilise l'email comme identifiant principal
    REQUIRED_FIELDS = ['first_name', 'last_name']  # Champs requis pour la création d'un superutilisateur

    def get_full_name(self):
        """Retourne le nom complet de l'utilisateur"""
        full_name = f"{self.first_name} {self.last_name}".strip()
        return full_name if full_name else self.email
    def get_username(self):
        return self.email  # Remplace `username` par `email`


    def get_short_name(self):
        """Retourne le prénom de l'utilisateur"""
        return self.first_name if self.first_name else self.email
    class Meta:
        verbose_name = "Utilisateur"
        verbose_name_plural = "Utilisateurs"

    def __str__(self):
        return self.email

