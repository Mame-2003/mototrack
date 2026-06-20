from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("core", "0004_update_gps_alert_delay_message")]

    operations = [
        migrations.AlterField(
            model_name="alert",
            name="type",
            field=models.CharField(
                choices=[
                    ("GPS_DECONNECTE", "GPS déconnecté"),
                    ("SORTIE_ZONE", "Sortie de zone"),
                    ("VALIDATION_COMMANDE", "Validation de commande"),
                    ("MISSION_ASSIGNEE", "Mission assignée"),
                    ("MISSION_ANNULEE", "Mission annulée"),
                ],
                max_length=30,
            ),
        ),
    ]
