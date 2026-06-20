from django.core.management.base import BaseCommand

from core.alerting import create_gps_disconnect_alerts


class Command(BaseCommand):
    help = "Crée les alertes pour les motos sans signal GPS récent (10 minutes par défaut)."

    def add_arguments(self, parser):
        parser.add_argument("--minutes", type=int, default=None)

    def handle(self, *args, **options):
        created = create_gps_disconnect_alerts(options["minutes"])
        self.stdout.write(self.style.SUCCESS(f"{created} nouvelle(s) alerte(s) GPS créée(s)."))
