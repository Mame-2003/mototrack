from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import api_views

router = DefaultRouter()
router.register("motos", api_views.MotoViewSet)
router.register("livreurs", api_views.LivreurViewSet)
router.register("affectations", api_views.AffectationViewSet)
router.register("missions", api_views.MissionViewSet, basename="mission")
router.register("preuves", api_views.PreuveLivraisonViewSet, basename="preuve")
router.register("alerts", api_views.AlertViewSet, basename="alert")

urlpatterns = [
    path("auth/token/", api_views.LoginTokenView.as_view(), name="api_token"),
    path("driver/profile/", api_views.driver_profile_api, name="driver-profile-api"),
    path("driver/missions/", api_views.driver_missions_api, name="driver-missions-api"),
    path("driver/missions/<int:pk>/", api_views.driver_mission_detail_api, name="driver-mission-detail-api"),
    path("driver/missions/<int:pk>/validate-otp/", api_views.driver_validate_otp_api, name="driver-validate-otp-api"),
    path("driver/deliveries/", api_views.driver_deliveries_api, name="driver-deliveries-api"),
    path("driver/alerts/", api_views.driver_alerts_api, name="driver-alerts-api"),
    path("driver/alerts/<int:pk>/mark-read/", api_views.driver_alert_mark_read_api, name="driver-alert-mark-read-api"),
    path("driver/alerts/<int:pk>/delete/", api_views.driver_alert_delete_api, name="driver-alert-delete-api"),
    path("gps/positions/", api_views.gps_ingest, name="gps_ingest"),
    path("gps/latest/", api_views.latest_positions, name="latest_positions"),
    path("gps/history/<int:moto_id>/", api_views.moto_history, name="moto_history"),
    path("", include(router.urls)),
]
