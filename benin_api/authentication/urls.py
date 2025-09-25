from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from .views import UtilisateurViewSet, CustomTokenObtainPairView
from .views_invitation import RegisterWithInvitationView
from .views import UtilisateurViewSet, CustomTokenObtainPairView






router = DefaultRouter()
router.register('utilisateurs', UtilisateurViewSet)

urlpatterns = [
    path('register/invite/', RegisterWithInvitationView.as_view(), name='register-with-invitation'),
    path('', include(router.urls)),
    path('token/', CustomTokenObtainPairView.as_view(), name='token'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('forgot-password/', UtilisateurViewSet.as_view({'post': 'forgot_password'}), name='forgot-password'),
    path('reset-password/', UtilisateurViewSet.as_view({'post': 'reset_password'}), name='reset-password'),
]