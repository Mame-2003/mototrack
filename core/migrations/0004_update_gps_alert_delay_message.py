from django.db import migrations


def update_gps_messages(apps, schema_editor):
    Alert = apps.get_model("core", "Alert")
    for alert in Alert.objects.filter(type="GPS_DECONNECTE", message__contains="2 minutes"):
        alert.message = alert.message.replace("2 minutes", "10 minutes")
        alert.save(update_fields=["message"])


class Migration(migrations.Migration):
    dependencies = [("core", "0003_alert_mission_destination")]

    operations = [migrations.RunPython(update_gps_messages, migrations.RunPython.noop)]
