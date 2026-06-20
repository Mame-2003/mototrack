import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("core", "0002_profilutilisateur")]

    operations = [
        migrations.AddField(
            model_name="mission",
            name="destination_latitude",
            field=models.DecimalField(blank=True, decimal_places=7, max_digits=10, null=True),
        ),
        migrations.AddField(
            model_name="mission",
            name="destination_longitude",
            field=models.DecimalField(blank=True, decimal_places=7, max_digits=10, null=True),
        ),
        migrations.CreateModel(
            name="Alert",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("date", models.DateTimeField(auto_now_add=True)),
                ("type", models.CharField(choices=[("GPS_DECONNECTE", "GPS déconnecté"), ("SORTIE_ZONE", "Sortie de zone"), ("VALIDATION_COMMANDE", "Validation de commande")], max_length=30)),
                ("message", models.TextField()),
                ("is_read", models.BooleanField(default=False)),
                ("mission", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="alerts", to="core.mission")),
                ("moto", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="alerts", to="core.moto")),
            ],
            options={"ordering": ["-date"]},
        ),
        migrations.AddIndex(
            model_name="alert",
            index=models.Index(fields=["is_read", "-date"], name="alert_read_date_idx"),
        ),
        migrations.AddIndex(
            model_name="alert",
            index=models.Index(fields=["moto", "type", "is_read"], name="alert_moto_type_idx"),
        ),
    ]
