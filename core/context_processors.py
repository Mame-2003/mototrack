from django.conf import settings

from .alerting import alerts_for_user


def alert_notifications(request):
    if not request.user.is_authenticated:
        return {}
    alerts = alerts_for_user(request.user)
    return {
        "nav_alerts": alerts[:5],
        "nav_unread_alerts": alerts.filter(is_read=False).count(),
        "google_maps_api_key": settings.GOOGLE_MAPS_API_KEY,
    }
