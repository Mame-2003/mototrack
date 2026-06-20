# Generated for MotoTrack.
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]

    operations = [
        migrations.CreateModel(
            name="Moto",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("immatriculation", models.CharField(max_length=30, unique=True)),
                ("marque", models.CharField(max_length=80)),
                ("modele", models.CharField(max_length=80)),
                ("etat", models.CharField(choices=[("disponible", "Disponible"), ("affectee", "Affectée"), ("en_mission", "En mission"), ("hors_service", "Hors service")], default="disponible", max_length=20)),
                ("cree_le", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["immatriculation"]},
        ),
        migrations.CreateModel(
            name="Livreur",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("telephone", models.CharField(max_length=30)),
                ("adresse", models.CharField(max_length=255)),
                ("numero_permis", models.CharField(max_length=80, unique=True)),
                ("numero_cni", models.CharField(max_length=80, unique=True)),
                ("photo", models.ImageField(blank=True, null=True, upload_to="livreurs/")),
                ("actif", models.BooleanField(default=True)),
                ("user", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="livreur", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["user__last_name", "user__first_name"]},
        ),
        migrations.CreateModel(
            name="Affectation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("date_debut", models.DateTimeField(default=django.utils.timezone.now)),
                ("date_fin", models.DateTimeField(blank=True, null=True)),
                ("active", models.BooleanField(default=True)),
                ("livreur", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="affectations", to="core.livreur")),
                ("moto", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="affectations", to="core.moto")),
            ],
            options={"ordering": ["-date_debut"]},
        ),
        migrations.CreateModel(
            name="Mission",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nom_client", models.CharField(max_length=120)),
                ("telephone_client", models.CharField(max_length=30)),
                ("adresse_livraison", models.CharField(max_length=255)),
                ("description_lieu", models.TextField(blank=True)),
                ("statut", models.CharField(choices=[("en_attente", "En attente"), ("en_cours", "En cours"), ("terminee", "Terminée"), ("annulee", "Annulée")], default="en_attente", max_length=20)),
                ("otp", models.CharField(editable=False, max_length=6)),
                ("otp_expire_le", models.DateTimeField(blank=True, null=True)),
                ("cree_le", models.DateTimeField(auto_now_add=True)),
                ("modifie_le", models.DateTimeField(auto_now=True)),
                ("valide_le", models.DateTimeField(blank=True, null=True)),
                ("livreur", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="missions", to="core.livreur")),
                ("moto", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="missions", to="core.moto")),
            ],
            options={"ordering": ["-cree_le"]},
        ),
        migrations.CreateModel(
            name="PositionGPS",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("latitude", models.DecimalField(decimal_places=7, max_digits=10)),
                ("longitude", models.DecimalField(decimal_places=7, max_digits=10)),
                ("date_appareil", models.DateTimeField(blank=True, null=True)),
                ("recue_le", models.DateTimeField(auto_now_add=True)),
                ("moto", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="positions", to="core.moto")),
            ],
            options={"ordering": ["-date_appareil", "-recue_le"]},
        ),
        migrations.CreateModel(
            name="PreuveLivraison",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("otp_valide", models.BooleanField(default=True)),
                ("valide_le", models.DateTimeField(default=django.utils.timezone.now)),
                ("mission", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="preuve", to="core.mission")),
            ],
            options={"ordering": ["-valide_le"]},
        ),
        migrations.AddConstraint(
            model_name="affectation",
            constraint=models.UniqueConstraint(condition=models.Q(("active", True)), fields=("moto",), name="unique_moto_active"),
        ),
        migrations.AddConstraint(
            model_name="affectation",
            constraint=models.UniqueConstraint(condition=models.Q(("active", True)), fields=("livreur",), name="unique_livreur_actif"),
        ),
        migrations.AddIndex(
            model_name="positiongps",
            index=models.Index(fields=["moto", "-recue_le"], name="gps_moto_received_idx"),
        ),
    ]
