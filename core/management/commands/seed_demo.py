from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from core.models import Affectation, Livreur, Mission, Moto


class Command(BaseCommand):
    help = "Crée un responsable et des données de démonstration."

    def handle(self, *args, **options):
        admin, created = User.objects.get_or_create(
            username="responsable",
            defaults={"first_name": "Aminata", "last_name": "Ndiaye", "email": "admin@mototrack.local", "is_staff": True, "is_superuser": True},
        )
        admin.first_name = "Aminata"
        admin.last_name = "Ndiaye"
        admin.email = "admin@mototrack.local"
        admin.is_staff = True
        admin.is_superuser = True
        admin.is_active = True
        admin.set_password("MotoTrack2026!")
        admin.save()

        driver_user, created = User.objects.get_or_create(
            username="livreur",
            defaults={"first_name": "Moussa", "last_name": "Fall", "email": "livreur@mototrack.local"},
        )
        driver_user.first_name = "Moussa"
        driver_user.last_name = "Fall"
        driver_user.email = "livreur@mototrack.local"
        driver_user.is_active = True
        driver_user.set_password("MotoTrack2026!")
        driver_user.save()

        livreur, _ = Livreur.objects.get_or_create(
            user=driver_user,
            defaults={"telephone": "770000001", "adresse": "Dakar", "numero_permis": "PERMIS-DEMO", "numero_cni": "CNI-DEMO"},
        )
        moto, _ = Moto.objects.get_or_create(
            immatriculation="DK-2026-MT",
            defaults={"marque": "Yamaha", "modele": "YBR 125"},
        )
        Affectation.objects.get_or_create(livreur=livreur, moto=moto, active=True)
        Mission.objects.get_or_create(
            nom_client="Fatou Diop",
            telephone_client="770000002",
            adresse_livraison="Plateau, Dakar",
            livreur=livreur,
            moto=moto,
            defaults={"description_lieu": "Immeuble face à la pharmacie", "statut": Mission.Statut.EN_COURS},
        )
        self.stdout.write(self.style.SUCCESS("Données créées. Responsable/livreur : mot de passe MotoTrack2026!"))
