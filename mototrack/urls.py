from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import include, path

from core import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("connexion/", LoginView.as_view(template_name="registration/login.html"), name="login"),
    path("inscription-responsable/", views.responsable_register, name="responsable_register"),
    path("deconnexion/", LogoutView.as_view(), name="logout"),
    path("api/", include("core.api_urls")),
    path("", views.dashboard, name="dashboard"),
    path("motos/", views.motos_page, name="motos"),
    path("livreurs/", views.livreurs_page, name="livreurs"),
    path("livreurs/<int:pk>/", views.livreur_detail, name="livreur_detail"),
    path("affectations/", views.affectations_page, name="affectations"),
    path("missions/", views.missions_page, name="missions"),
    path("missions/<int:pk>/", views.mission_detail, name="mission_detail"),
    path("carte/", views.map_page, name="map"),
    path("preuves/", views.proofs_page, name="proofs"),
    path("profil/", views.profile_page, name="profile"),
    path("alertes/", views.alerts_page, name="alerts"),
    path("alertes/<int:pk>/lire/", views.alert_mark_read, name="alert_mark_read"),
    path("alertes/<int:pk>/supprimer/", views.alert_delete, name="alert_delete"),
    path("mon-espace/", views.driver_space, name="driver_space"),
    path("mon-espace/profil/", views.driver_profile, name="driver_profile"),
    path("mon-espace/ma-moto/", views.driver_moto, name="driver_moto"),
    path("mon-espace/missions/", views.driver_missions, name="driver_missions"),
    path("mon-espace/missions/<int:pk>/", views.driver_mission_detail, name="driver_mission_detail"),
    path("mon-espace/livraisons/", views.driver_deliveries, name="driver_deliveries"),
    path("mon-espace/livraisons/<int:pk>/preuve/", views.driver_proof, name="driver_proof"),
    path("mon-espace/livraisons/<int:pk>/preuve.pdf", views.driver_proof_pdf, name="driver_proof_pdf"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
