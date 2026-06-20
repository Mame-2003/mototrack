import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ProfilUtilisateur",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("telephone", models.CharField(blank=True, max_length=30)),
                ("user", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="profil", to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
