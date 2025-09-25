from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import Group
from .models import Utilisateur
from Equipe.models import Organisation
from unfold.admin import ModelAdmin
from unfold.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm

# Masquer le modèle Group dans l'interface d'administration
admin.site.unregister(Group)


class OrganisationFilter(admin.SimpleListFilter):
    title = "Organisation"
    parameter_name = "organisation"

    def lookups(self, request, model_admin):
        return [(org.id, org.nom_entreprise) for org in Organisation.objects.all()]

    def queryset(self, request, queryset):
        if self.value():
            try:
                org = Organisation.objects.get(id=self.value())
                ids = list(org.membres.values_list('id', flat=True)) + [org.createur_id]
                return queryset.filter(id__in=ids)
            except Organisation.DoesNotExist:
                return queryset.none()
        return queryset


@admin.register(Utilisateur)
class UtilisateurAdmin(UserAdmin, ModelAdmin):
    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm
    """Configuration de l'interface d'administration pour le modèle Utilisateur."""

    list_display = [
        'last_name', 'first_name', 'email', 'telephone', 'type_utilisateur', 'is_staff', 'date_creation',
        'organisations', 'webinaires_inscrits',
        'peut_modifier_fichier', 'peut_creer_reunion', 'peut_utiliser_ia'
    ]
    list_filter = [
        'type_utilisateur', 'est_actif', 'date_creation', 'is_staff', 'is_superuser',
        'peut_modifier_fichier', 'peut_creer_reunion', 'peut_utiliser_ia',
        OrganisationFilter
    ]
    search_fields = ['email', 'telephone', 'first_name', 'last_name']  # Ajout de la recherche sur first_name et last_name
    ordering = ['-date_creation']

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (_('Informations personnelles'), {'fields': ('first_name', 'last_name', 'telephone', 'image')}),
        (_('Type et statut'), {'fields': ('type_utilisateur',)}),  
        (_('Permissions'), {
            'fields': ('est_actif', 'is_staff', 'is_superuser', 'groups', 'user_permissions', 'peut_modifier_fichier', 'peut_creer_reunion', 'peut_utiliser_ia'), 
            'classes': ('collapse',)
        }),
        (_('Dates importantes'), {
            'fields': ('last_login', 'date_creation', 'date_modification'),
            'classes': ('collapse',)
        }),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'first_name', 'last_name', 'password1', 'password2', 'type_utilisateur', 'telephone'),
        }),
    )

    readonly_fields = ['date_creation', 'date_modification']

    def webinaires_inscrits(self, obj):
        """Retourne une liste des titres de webinaires auxquels l'utilisateur est inscrit."""
        titres = obj.inscriptions_webinaire.select_related('webinaire').values_list('webinaire__titre', flat=True)
        return ", ".join(titres) or "-"
    webinaires_inscrits.short_description = "Webinaires inscrits"

    # ---- Organisation helpers ----
    def organisations(self, obj):
        """Noms des organisations où l'utilisateur est créateur ou membre"""
        orgs_cree = Organisation.objects.filter(createur=obj)
        orgs_membre = Organisation.objects.filter(membres=obj)
        noms = set(list(orgs_cree.values_list('nom_entreprise', flat=True)) + list(orgs_membre.values_list('nom_entreprise', flat=True)))
        return ", ".join(noms) or "-"
    organisations.short_description = "Organisation(s)"


class OrganisationFilter(admin.SimpleListFilter):
    title = "Organisation"
    parameter_name = "organisation"

    def lookups(self, request, model_admin):
        return [(org.id, org.nom_entreprise) for org in Organisation.objects.all()]

    def queryset(self, request, queryset):
        if self.value():
            try:
                org = Organisation.objects.get(id=self.value())
                ids = list(org.membres.values_list('id', flat=True)) + [org.createur_id]
                return queryset.filter(id__in=ids)
            except Organisation.DoesNotExist:
                return queryset.none()
        return queryset


