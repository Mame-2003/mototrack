from django.contrib import admin

from .models import Alert, Affectation, Livreur, Mission, Moto, PositionGPS, PreuveLivraison, ProfilUtilisateur

admin.site.site_header = "Administration MotoTrack"
admin.site.site_title = "MotoTrack"

admin.site.register([Moto, Livreur, Affectation, Mission, PositionGPS, PreuveLivraison, ProfilUtilisateur, Alert])
