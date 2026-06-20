import secrets

from django.conf import settings
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import OuterRef, Subquery
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import Alert, Affectation, Livreur, Mission, Moto, PositionGPS, PreuveLivraison
from .alerting import alerts_for_user, create_gps_disconnect_alerts, process_gps_position
from .permissions import IsManager, IsManagerOrReadOwn
from .serializers import (
    AffectationSerializer,
    GPSIngestSerializer,
    LivreurSerializer,
    MissionSerializer,
    MotoSerializer,
    OTPSerializer,
    PositionGPSSerializer,
    PreuveLivraisonSerializer,
    AlertSerializer,
    DriverProfileSerializer,
)


class LoginTokenView(ObtainAuthToken):
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        response.data["user"] = request.data.get("username")
        return response


class MotoViewSet(viewsets.ModelViewSet):
    queryset = Moto.objects.all()
    serializer_class = MotoSerializer
    permission_classes = [IsManager]


class LivreurViewSet(viewsets.ModelViewSet):
    queryset = Livreur.objects.select_related("user")
    serializer_class = LivreurSerializer
    permission_classes = [IsManager]


class AffectationViewSet(viewsets.ModelViewSet):
    queryset = Affectation.objects.select_related("livreur__user", "moto")
    serializer_class = AffectationSerializer
    permission_classes = [IsManager]


class MissionViewSet(viewsets.ModelViewSet):
    serializer_class = MissionSerializer
    permission_classes = [IsManagerOrReadOwn]

    def get_queryset(self):
        qs = Mission.objects.select_related("livreur__user", "moto")
        if self.request.user.is_staff:
            return qs
        return qs.filter(livreur__user=self.request.user)

    def perform_create(self, serializer):
        if not self.request.user.is_staff:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Seul le responsable peut créer une mission.")
        serializer.save()

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def valider_otp(self, request, pk=None):
        mission = self.get_object()
        serializer = OTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            proof = mission.validate_otp(serializer.validated_data["otp"])
        except DjangoValidationError as exc:
            return Response({"detail": exc.messages[0]}, status=status.HTTP_400_BAD_REQUEST)
        return Response(PreuveLivraisonSerializer(proof).data)


class PreuveLivraisonViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PreuveLivraisonSerializer
    permission_classes = [IsManagerOrReadOwn]

    def get_queryset(self):
        qs = PreuveLivraison.objects.select_related("mission__livreur__user", "mission__moto")
        if self.request.user.is_staff:
            return qs
        return qs.filter(mission__livreur__user=self.request.user)


class AlertViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AlertSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return alerts_for_user(self.request.user)

    @action(detail=False, methods=["get"], url_path="unread-count")
    def unread_count(self, request):
        if request.user.is_staff:
            create_gps_disconnect_alerts()
        queryset = self.get_queryset()
        latest = queryset.filter(is_read=False).first()
        return Response({
            "unread_count": queryset.filter(is_read=False).count(),
            "latest_alert": AlertSerializer(latest).data if latest else None,
        })

    @action(detail=True, methods=["post"], url_path="mark-read")
    def mark_read(self, request, pk=None):
        alert = self.get_object()
        alert.is_read = True
        alert.save(update_fields=["is_read"])
        return Response(AlertSerializer(alert).data)


@api_view(["POST"])
@permission_classes([AllowAny])
def gps_ingest(request):
    provided_key = request.headers.get("X-API-Key", "")
    if not secrets.compare_digest(provided_key, settings.GPS_API_KEY):
        return Response({"detail": "Clé API invalide."}, status=status.HTTP_401_UNAUTHORIZED)
    serializer = GPSIngestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    position = serializer.save()
    process_gps_position(position)
    return Response(PositionGPSSerializer(position).data, status=status.HTTP_201_CREATED)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def latest_positions(request):
    latest_id = PositionGPS.objects.filter(moto=OuterRef("pk")).order_by("-recue_le").values("id")[:1]
    ids = Moto.objects.annotate(latest_position_id=Subquery(latest_id)).values_list("latest_position_id", flat=True)
    positions = PositionGPS.objects.filter(id__in=[i for i in ids if i]).select_related("moto")
    return Response(PositionGPSSerializer(positions, many=True).data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def moto_history(request, moto_id):
    positions = PositionGPS.objects.filter(moto_id=moto_id).select_related("moto")
    limit = min(int(request.query_params.get("limit", 200)), 1000)
    return Response(PositionGPSSerializer(positions[:limit], many=True).data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def driver_profile_api(request):
    if request.user.is_staff or not hasattr(request.user, "livreur"):
        return Response({"detail": "Accès réservé aux livreurs."}, status=status.HTTP_403_FORBIDDEN)
    livreur = request.user.livreur
    serializer = DriverProfileSerializer(livreur, context={"request": request})
    return Response(serializer.data)


def _driver_or_403(request):
    if request.user.is_staff or not hasattr(request.user, "livreur"):
        return None
    return request.user.livreur


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def driver_missions_api(request):
    livreur = _driver_or_403(request)
    if not livreur:
        return Response({"detail": "Accès réservé aux livreurs."}, status=status.HTTP_403_FORBIDDEN)
    missions = Mission.objects.filter(livreur=livreur).select_related("moto")
    return Response(MissionSerializer(missions, many=True).data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def driver_mission_detail_api(request, pk):
    livreur = _driver_or_403(request)
    if not livreur:
        return Response({"detail": "Accès réservé aux livreurs."}, status=status.HTTP_403_FORBIDDEN)
    mission = get_object_or_404(Mission.objects.select_related("moto"), pk=pk, livreur=livreur)
    return Response(MissionSerializer(mission).data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def driver_validate_otp_api(request, pk):
    livreur = _driver_or_403(request)
    if not livreur:
        return Response({"detail": "Accès réservé aux livreurs."}, status=status.HTTP_403_FORBIDDEN)
    mission = get_object_or_404(Mission, pk=pk, livreur=livreur)
    serializer = OTPSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    try:
        proof = mission.validate_otp(serializer.validated_data["otp"])
    except DjangoValidationError as exc:
        return Response({"detail": exc.messages[0]}, status=status.HTTP_400_BAD_REQUEST)
    return Response(PreuveLivraisonSerializer(proof).data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def driver_deliveries_api(request):
    livreur = _driver_or_403(request)
    if not livreur:
        return Response({"detail": "Accès réservé aux livreurs."}, status=status.HTTP_403_FORBIDDEN)
    missions = Mission.objects.filter(
        livreur=livreur, statut=Mission.Statut.TERMINEE
    ).select_related("moto")
    return Response(MissionSerializer(missions, many=True).data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def driver_alerts_api(request):
    livreur = _driver_or_403(request)
    if not livreur:
        return Response({"detail": "Accès réservé aux livreurs."}, status=status.HTTP_403_FORBIDDEN)
    return Response(AlertSerializer(alerts_for_user(request.user), many=True).data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def driver_alert_mark_read_api(request, pk):
    livreur = _driver_or_403(request)
    if not livreur:
        return Response({"detail": "Accès réservé aux livreurs."}, status=status.HTTP_403_FORBIDDEN)
    alert = get_object_or_404(alerts_for_user(request.user), pk=pk)
    alert.is_read = True
    alert.save(update_fields=["is_read"])
    return Response(AlertSerializer(alert).data)


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def driver_alert_delete_api(request, pk):
    livreur = _driver_or_403(request)
    if not livreur:
        return Response({"detail": "Accès réservé aux livreurs."}, status=status.HTTP_403_FORBIDDEN)
    alert = get_object_or_404(alerts_for_user(request.user), pk=pk)
    alert.is_deleted = True
    alert.is_read = True
    alert.save(update_fields=["is_deleted", "is_read"])
    return Response(status=status.HTTP_204_NO_CONTENT)
