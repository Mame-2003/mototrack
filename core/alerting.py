from datetime import timedelta

from django.conf import settings
from django.db.models import Max, Q
from django.utils import timezone

from .models import Alert, Moto

SENEGAL_LIMITS = {
    "latitude_min": 12.0,
    "latitude_max": 16.8,
    "longitude_min": -17.7,
    "longitude_max": -11.3,
}


def is_inside_senegal(latitude, longitude):
    latitude = float(latitude)
    longitude = float(longitude)
    return (
        SENEGAL_LIMITS["latitude_min"] <= latitude <= SENEGAL_LIMITS["latitude_max"]
        and SENEGAL_LIMITS["longitude_min"] <= longitude <= SENEGAL_LIMITS["longitude_max"]
    )


def process_gps_position(position):
    moto = position.moto
    Alert.objects.filter(
        moto=moto,
        type=Alert.Type.GPS_DECONNECTE,
        incident_actif=True,
    ).update(is_read=True, incident_actif=False)

    if not is_inside_senegal(position.latitude, position.longitude):
        Alert.objects.get_or_create(
            moto=moto,
            type=Alert.Type.SORTIE_ZONE,
            incident_actif=True,
            defaults={"message": f"La moto {moto.immatriculation} est sortie de la zone autorisée."},
        )
    else:
        Alert.objects.filter(
            moto=moto,
            type=Alert.Type.SORTIE_ZONE,
            incident_actif=True,
        ).update(is_read=True, incident_actif=False)


def create_gps_disconnect_alerts(minutes=None):
    minutes = minutes or getattr(settings, "GPS_DISCONNECT_MINUTES", 10)
    cutoff = timezone.now() - timedelta(minutes=minutes)
    motos = (
        Moto.objects.filter(Q(affectations__active=True) | Q(etat=Moto.Etat.EN_MISSION))
        .annotate(last_gps=Max("positions__recue_le"))
        .distinct()
    )
    created = 0
    for moto in motos:
        if moto.last_gps and moto.last_gps >= cutoff:
            continue
        _, was_created = Alert.objects.get_or_create(
            moto=moto,
            type=Alert.Type.GPS_DECONNECTE,
            incident_actif=True,
            defaults={
                "message": (
                    f"GPS déconnecté : aucune position reçue pour la moto "
                    f"{moto.immatriculation} depuis plus de {minutes} minutes."
                )
            },
        )
        created += int(was_created)
    return created


def alerts_for_user(user):
    queryset = Alert.objects.filter(is_deleted=False).select_related("moto", "mission")
    if user.is_staff:
        return queryset.exclude(
            type__in=[Alert.Type.MISSION_ASSIGNEE, Alert.Type.MISSION_ANNULEE]
        )
    livreur = getattr(user, "livreur", None)
    if not livreur:
        return queryset.none()
    return queryset.filter(
        mission__livreur=livreur,
        type__in=[Alert.Type.MISSION_ASSIGNEE, Alert.Type.MISSION_ANNULEE],
    ).distinct()
