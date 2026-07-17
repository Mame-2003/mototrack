import re
import secrets
from datetime import timedelta

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone


class Moto(models.Model):
    class Etat(models.TextChoices):
        DISPONIBLE = "disponible", "Disponible"
        AFFECTEE = "affectee", "Affectée"
        EN_MISSION = "en_mission", "En mission"
        HORS_SERVICE = "hors_service", "Hors service"

    immatriculation = models.CharField(max_length=30, unique=True)
    marque = models.CharField(max_length=80)
    modele = models.CharField(max_length=80)
    etat = models.CharField(max_length=20, choices=Etat.choices, default=Etat.DISPONIBLE)
    cree_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["immatriculation"]

    def __str__(self):
        return f"{self.immatriculation} - {self.marque} {self.modele}"


class Livreur(models.Model):
    class TypeContrat(models.TextChoices):
        CDD = "CDD", "CDD"
        CDI = "CDI", "CDI"

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="livreur")
    age = models.PositiveSmallIntegerField(
        blank=True,
        null=True,
        validators=[MinValueValidator(18), MaxValueValidator(80)],
    )
    telephone = models.CharField(max_length=30)
    adresse = models.CharField(max_length=255)
    numero_permis = models.CharField(max_length=80, unique=True)
    numero_cni = models.CharField(max_length=80, unique=True)
    photo = models.ImageField(upload_to="livreurs/", blank=True, null=True)
    type_contrat = models.CharField(max_length=3, choices=TypeContrat.choices, default=TypeContrat.CDI)
    date_debut_contrat = models.DateField(blank=True, null=True)
    date_fin_contrat = models.DateField(blank=True, null=True)
    contrat = models.FileField(upload_to="contrats/", blank=True, null=True)
    actif = models.BooleanField(default=True)

    class Meta:
        ordering = ["user__last_name", "user__first_name"]

    @property
    def nom_complet(self):
        return self.user.get_full_name() or self.user.username

    def clean(self):
        if self.type_contrat == self.TypeContrat.CDD:
            if not self.date_debut_contrat or not self.date_fin_contrat:
                raise ValidationError("Les dates de début et de fin sont obligatoires pour un CDD.")
            if self.date_fin_contrat < self.date_debut_contrat:
                raise ValidationError("La date de fin du CDD doit être postérieure à la date de début.")

    def __str__(self):
        return self.nom_complet


class ProfilUtilisateur(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profil")
    telephone = models.CharField(max_length=30, blank=True)

    def __str__(self):
        return f"Profil de {self.user.username}"


class Affectation(models.Model):
    livreur = models.ForeignKey(Livreur, on_delete=models.PROTECT, related_name="affectations")
    moto = models.ForeignKey(Moto, on_delete=models.PROTECT, related_name="affectations")
    date_debut = models.DateTimeField(default=timezone.now)
    date_fin = models.DateTimeField(blank=True, null=True)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-date_debut"]
        constraints = [
            models.UniqueConstraint(fields=["moto"], condition=models.Q(active=True), name="unique_moto_active"),
            models.UniqueConstraint(fields=["livreur"], condition=models.Q(active=True), name="unique_livreur_actif"),
        ]

    def clean(self):
        if not self.active:
            return
        if Affectation.objects.filter(moto=self.moto, active=True).exclude(pk=self.pk).exists():
            raise ValidationError("Cette moto possède déjà une affectation active.")
        if Affectation.objects.filter(livreur=self.livreur, active=True).exclude(pk=self.pk).exists():
            raise ValidationError("Ce livreur possède déjà une affectation active.")

    def save(self, *args, **kwargs):
        self.full_clean()
        if not self.active and not self.date_fin:
            self.date_fin = timezone.now()
        super().save(*args, **kwargs)
        self.moto.etat = Moto.Etat.AFFECTEE if self.active else Moto.Etat.DISPONIBLE
        self.moto.save(update_fields=["etat"])

    def __str__(self):
        return f"{self.livreur} → {self.moto.immatriculation}"


class Mission(models.Model):
    class Statut(models.TextChoices):
        EN_ATTENTE = "en_attente", "En attente"
        EN_COURS = "en_cours", "En cours"
        TERMINEE = "terminee", "Terminée"
        ANNULEE = "annulee", "Annulée"

    nom_client = models.CharField(max_length=120)
    telephone_client = models.CharField(max_length=30)
    adresse_livraison = models.CharField(max_length=255)
    description_lieu = models.TextField(blank=True)
    destination_latitude = models.DecimalField(max_digits=10, decimal_places=7, blank=True, null=True)
    destination_longitude = models.DecimalField(max_digits=10, decimal_places=7, blank=True, null=True)
    livreur = models.ForeignKey(Livreur, on_delete=models.PROTECT, related_name="missions")
    moto = models.ForeignKey(Moto, on_delete=models.PROTECT, related_name="missions")
    statut = models.CharField(max_length=20, choices=Statut.choices, default=Statut.EN_ATTENTE)
    otp = models.CharField(max_length=6, editable=False)
    otp_expire_le = models.DateTimeField(blank=True, null=True)
    cree_le = models.DateTimeField(auto_now_add=True)
    modifie_le = models.DateTimeField(auto_now=True)
    valide_le = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ["-cree_le"]

    @property
    def whatsapp_number(self):
        number = re.sub(r"\D", "", self.telephone_client)
        if len(number) == 9:
            return f"221{number}"
        return number

    def clean(self):
        if self.livreur_id and self.moto_id and not Affectation.objects.filter(
            livreur_id=self.livreur_id, moto_id=self.moto_id, active=True
        ).exists():
            raise ValidationError("La moto doit être activement affectée à ce livreur.")
        if self.statut == self.Statut.TERMINEE and not self.valide_le:
            raise ValidationError("Une mission ne peut être terminée que par validation de l'OTP.")

    def save(self, *args, **kwargs):
        previous_status = None
        if self.pk:
            previous_status = Mission.objects.filter(pk=self.pk).values_list("statut", flat=True).first()
        if not self.otp:
            self.otp = f"{secrets.randbelow(1_000_000):06d}"
            self.otp_expire_le = timezone.now() + timedelta(days=7)
        if self._state.adding:
            self.full_clean()
        is_new = self._state.adding
        super().save(*args, **kwargs)
        if is_new:
            Alert.objects.get_or_create(
                mission=self,
                type=Alert.Type.MISSION_ASSIGNEE,
                defaults={
                    "moto": self.moto,
                    "message": f"Nouvelle mission assignée : mission #{self.pk} pour {self.nom_client}.",
                },
            )
        if self.statut == self.Statut.ANNULEE and previous_status != self.Statut.ANNULEE:
            Alert.objects.get_or_create(
                mission=self,
                type=Alert.Type.MISSION_ANNULEE,
                defaults={
                    "moto": self.moto,
                    "message": f"La mission #{self.pk} a été annulée.",
                },
            )

    def validate_otp(self, code):
        if self.statut in [self.Statut.TERMINEE, self.Statut.ANNULEE]:
            raise ValidationError("Cette mission ne peut plus être validée.")
        if self.otp_expire_le and timezone.now() > self.otp_expire_le:
            raise ValidationError("Cet OTP a expiré.")
        if not secrets.compare_digest(self.otp, str(code).strip()):
            raise ValidationError("OTP incorrect.")
        self.statut = self.Statut.TERMINEE
        self.valide_le = timezone.now()
        self.save(update_fields=["statut", "valide_le", "modifie_le"])
        proof, _ = PreuveLivraison.objects.get_or_create(
            mission=self,
            defaults={"otp_valide": True, "valide_le": self.valide_le},
        )
        Alert.objects.get_or_create(
            mission=self,
            type=Alert.Type.VALIDATION_COMMANDE,
            defaults={"moto": self.moto, "message": f"La mission #{self.pk} a été validée avec succès."},
        )
        return proof

    def __str__(self):
        return f"Mission #{self.pk} - {self.nom_client}"


class PositionGPS(models.Model):
    moto = models.ForeignKey(Moto, on_delete=models.CASCADE, related_name="positions")
    latitude = models.DecimalField(max_digits=10, decimal_places=7)
    longitude = models.DecimalField(max_digits=10, decimal_places=7)
    date_appareil = models.DateTimeField(blank=True, null=True)
    recue_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date_appareil", "-recue_le"]
        indexes = [models.Index(fields=["moto", "-recue_le"], name="gps_moto_received_idx")]

    def __str__(self):
        return f"{self.moto.immatriculation} ({self.latitude}, {self.longitude})"


class PreuveLivraison(models.Model):
    mission = models.OneToOneField(Mission, on_delete=models.CASCADE, related_name="preuve")
    otp_valide = models.BooleanField(default=True)
    valide_le = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-valide_le"]

    def __str__(self):
        return f"Preuve - {self.mission}"


class Alert(models.Model):
    class Type(models.TextChoices):
        GPS_DECONNECTE = "GPS_DECONNECTE", "GPS déconnecté"
        SORTIE_ZONE = "SORTIE_ZONE", "Sortie de zone"
        VALIDATION_COMMANDE = "VALIDATION_COMMANDE", "Validation de commande"
        MISSION_ASSIGNEE = "MISSION_ASSIGNEE", "Mission assignée"
        MISSION_ANNULEE = "MISSION_ANNULEE", "Mission annulée"

    date = models.DateTimeField(auto_now_add=True)
    moto = models.ForeignKey(Moto, on_delete=models.CASCADE, related_name="alerts", blank=True, null=True)
    mission = models.ForeignKey(Mission, on_delete=models.CASCADE, related_name="alerts", blank=True, null=True)
    type = models.CharField(max_length=30, choices=Type.choices)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    incident_actif = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)

    class Meta:
        ordering = ["-date"]
        indexes = [
            models.Index(fields=["is_read", "-date"], name="alert_read_date_idx"),
            models.Index(fields=["moto", "type", "is_read"], name="alert_moto_type_idx"),
        ]

    def __str__(self):
        return self.message
