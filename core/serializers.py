from django.contrib.auth.models import User
from django.db import transaction
from rest_framework import serializers

from .models import Alert, Affectation, Livreur, Mission, Moto, PositionGPS, PreuveLivraison


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = User
        fields = ["id", "username", "first_name", "last_name", "email", "password"]


class MotoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Moto
        fields = "__all__"


class LivreurSerializer(serializers.ModelSerializer):
    user = UserSerializer()
    nom_complet = serializers.ReadOnlyField()

    class Meta:
        model = Livreur
        fields = [
            "id", "user", "nom_complet", "age", "telephone", "adresse", "numero_permis",
            "numero_cni", "photo", "type_contrat", "date_debut_contrat",
            "date_fin_contrat", "contrat", "actif",
        ]

    @transaction.atomic
    def create(self, validated_data):
        user_data = validated_data.pop("user")
        password = user_data.pop("password", None)
        user = User.objects.create_user(password=password, **user_data)
        return Livreur.objects.create(user=user, **validated_data)

    @transaction.atomic
    def update(self, instance, validated_data):
        user_data = validated_data.pop("user", {})
        password = user_data.pop("password", None)
        for field, value in user_data.items():
            setattr(instance.user, field, value)
        if password:
            instance.user.set_password(password)
        instance.user.save()
        return super().update(instance, validated_data)


class AffectationSerializer(serializers.ModelSerializer):
    livreur_nom = serializers.CharField(source="livreur.nom_complet", read_only=True)
    moto_immatriculation = serializers.CharField(source="moto.immatriculation", read_only=True)

    class Meta:
        model = Affectation
        fields = "__all__"

    def validate(self, attrs):
        instance = self.instance
        if not attrs.get("active", getattr(instance, "active", True)):
            return attrs
        moto = attrs.get("moto", getattr(instance, "moto", None))
        livreur = attrs.get("livreur", getattr(instance, "livreur", None))
        qs = Affectation.objects.filter(active=True)
        if instance:
            qs = qs.exclude(pk=instance.pk)
        if qs.filter(moto=moto).exists():
            raise serializers.ValidationError({"moto": "Cette moto est déjà affectée."})
        if qs.filter(livreur=livreur).exists():
            raise serializers.ValidationError({"livreur": "Ce livreur possède déjà une moto."})
        return attrs


class MissionSerializer(serializers.ModelSerializer):
    livreur_nom = serializers.CharField(source="livreur.nom_complet", read_only=True)
    moto_immatriculation = serializers.CharField(source="moto.immatriculation", read_only=True)
    otp = serializers.CharField(read_only=True)
    last_position = serializers.SerializerMethodField()

    class Meta:
        model = Mission
        fields = "__all__"

    def get_last_position(self, obj):
        position = obj.moto.positions.order_by("-recue_le").first()
        if not position:
            return None
        return {
            "latitude": position.latitude,
            "longitude": position.longitude,
            "date": position.recue_le,
        }

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation["moto"] = {
            "id": instance.moto_id,
            "immatriculation": instance.moto.immatriculation,
        }
        return representation

    def validate(self, attrs):
        livreur = attrs.get("livreur", getattr(self.instance, "livreur", None))
        moto = attrs.get("moto", getattr(self.instance, "moto", None))
        statut = attrs.get("statut", getattr(self.instance, "statut", Mission.Statut.EN_ATTENTE))
        if statut == Mission.Statut.TERMINEE:
            raise serializers.ValidationError({
                "statut": "Une mission ne peut être terminée que par validation de l'OTP."
            })
        if not Affectation.objects.filter(livreur=livreur, moto=moto, active=True).exists():
            raise serializers.ValidationError("La moto doit être activement affectée à ce livreur.")
        return attrs


class PositionGPSSerializer(serializers.ModelSerializer):
    moto_immatriculation = serializers.CharField(source="moto.immatriculation", read_only=True)

    class Meta:
        model = PositionGPS
        fields = "__all__"


class GPSIngestSerializer(serializers.Serializer):
    moto_id = serializers.IntegerField()
    latitude = serializers.DecimalField(max_digits=10, decimal_places=7)
    longitude = serializers.DecimalField(max_digits=10, decimal_places=7)
    date = serializers.DateField(required=False)
    heure = serializers.TimeField(required=False)

    def validate_moto_id(self, value):
        if not Moto.objects.filter(pk=value).exists():
            raise serializers.ValidationError("Moto inconnue.")
        return value

    def create(self, validated_data):
        from datetime import datetime
        from django.utils import timezone

        date = validated_data.pop("date", None)
        heure = validated_data.pop("heure", None)
        date_appareil = timezone.make_aware(datetime.combine(date, heure)) if date and heure else None
        return PositionGPS.objects.create(
            moto_id=validated_data.pop("moto_id"),
            date_appareil=date_appareil,
            **validated_data,
        )


class PreuveLivraisonSerializer(serializers.ModelSerializer):
    mission_detail = MissionSerializer(source="mission", read_only=True)

    class Meta:
        model = PreuveLivraison
        fields = "__all__"


class OTPSerializer(serializers.Serializer):
    otp = serializers.CharField(min_length=6, max_length=6)


class AlertSerializer(serializers.ModelSerializer):
    moto_immatriculation = serializers.CharField(source="moto.immatriculation", read_only=True)
    mission_numero = serializers.IntegerField(source="mission.id", read_only=True)
    type_display = serializers.CharField(source="get_type_display", read_only=True)

    class Meta:
        model = Alert
        fields = [
            "id", "date", "moto", "moto_immatriculation", "mission",
            "mission_numero", "type", "type_display", "message", "is_read",
            "incident_actif", "is_deleted",
        ]
        read_only_fields = fields


class DriverProfileSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(source="user.first_name", read_only=True)
    last_name = serializers.CharField(source="user.last_name", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = Livreur
        fields = [
            "id", "first_name", "last_name", "email", "telephone",
            "adresse", "numero_permis", "numero_cni", "photo",
        ]
        read_only_fields = ["id", "first_name", "last_name", "email", "numero_permis", "numero_cni"]
