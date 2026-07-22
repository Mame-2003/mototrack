from datetime import date
from io import StringIO

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from .models import Alert, Affectation, Livreur, Mission, Moto, PositionGPS, PreuveLivraison
from .forms import MissionForm
from .alerting import alerts_for_user


@override_settings(GPS_API_KEY="test-key")
class MotoTrackTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("livreur", password="secret", first_name="Awa", last_name="Diop")
        self.livreur = Livreur.objects.create(
            user=self.user, telephone="770000000", adresse="Dakar",
            numero_permis="PERMIS-1", numero_cni="CNI-1",
        )
        self.moto = Moto.objects.create(immatriculation="DK-001", marque="Yamaha", modele="YBR")
        Affectation.objects.create(livreur=self.livreur, moto=self.moto)

    def test_double_active_assignment_is_rejected(self):
        second_user = User.objects.create_user("second")
        second_driver = Livreur.objects.create(
            user=second_user, telephone="780000000", adresse="Dakar",
            numero_permis="PERMIS-2", numero_cni="CNI-2",
        )
        with self.assertRaises(ValidationError):
            Affectation.objects.create(livreur=second_driver, moto=self.moto)

    def test_otp_finishes_mission_and_creates_proof(self):
        mission = Mission.objects.create(
            nom_client="Client Test", telephone_client="760000000",
            adresse_livraison="Plateau", livreur=self.livreur, moto=self.moto,
        )
        mission.validate_otp(mission.otp)
        mission.refresh_from_db()
        self.assertEqual(mission.statut, Mission.Statut.TERMINEE)
        self.assertTrue(PreuveLivraison.objects.filter(mission=mission).exists())
        self.assertTrue(Alert.objects.filter(
            mission=mission,
            type=Alert.Type.VALIDATION_COMMANDE,
        ).exists())

    def test_manager_can_send_otp_by_whatsapp(self):
        manager = User.objects.create_user("manager-whatsapp", password="secret", is_staff=True)
        mission = Mission.objects.create(
            nom_client="Client WhatsApp", telephone_client="76 000 00 00",
            adresse_livraison="Plateau", livreur=self.livreur, moto=self.moto,
        )
        self.client.force_login(manager)

        response = self.client.get(reverse("mission_detail", args=[mission.id]))

        self.assertContains(response, "Envoyer l'OTP par WhatsApp")
        self.assertContains(response, f"https://wa.me/221760000000?text=")
        self.assertNotContains(response, "sms:")

    def test_mission_cannot_be_manually_marked_completed(self):
        mission = Mission(
            nom_client="Client Test", telephone_client="760000000",
            adresse_livraison="Plateau", livreur=self.livreur, moto=self.moto,
            statut=Mission.Statut.TERMINEE,
        )
        with self.assertRaises(ValidationError):
            mission.save()
        form = MissionForm()
        self.assertIn(
            Mission.Statut.TERMINEE,
            [value for value, _label in form.fields["statut"].choices],
        )
        rendered_status = str(form["statut"])
        self.assertIn('value="terminee" disabled', rendered_status)
        self.assertIn("validation OTP requise", rendered_status)

    def test_gps_endpoint_requires_key(self):
        client = APIClient()
        payload = {"moto_id": self.moto.id, "latitude": 14.7167, "longitude": -17.4677}
        self.assertEqual(client.post(reverse("gps_ingest"), payload, format="json").status_code, 401)
        response = client.post(reverse("gps_ingest"), payload, format="json", HTTP_X_API_KEY="test-key")
        self.assertEqual(response.status_code, 201)

    def test_out_of_zone_alert_is_created_without_duplicates(self):
        client = APIClient()
        payload = {"moto_id": self.moto.id, "latitude": 17.1, "longitude": -14.5}
        for _ in range(2):
            response = client.post(
                reverse("gps_ingest"), payload, format="json", HTTP_X_API_KEY="test-key"
            )
            self.assertEqual(response.status_code, 201)
        self.assertEqual(Alert.objects.filter(
            moto=self.moto,
            type=Alert.Type.SORTIE_ZONE,
            is_read=False,
        ).count(), 1)

    def test_gps_disconnect_command_creates_alert(self):
        call_command("check_gps_alerts", stdout=StringIO())
        self.assertTrue(Alert.objects.filter(
            moto=self.moto,
            type=Alert.Type.GPS_DECONNECTE,
            incident_actif=True,
            is_read=False,
        ).exists())

    def test_alert_unread_count_and_mark_read_api(self):
        manager = User.objects.create_user("manager", password="secret", is_staff=True)
        alert = Alert.objects.create(
            moto=self.moto,
            type=Alert.Type.GPS_DECONNECTE,
            incident_actif=True,
            message="GPS déconnecté.",
        )
        client = APIClient()
        client.force_authenticate(manager)
        response = client.get(reverse("alert-unread-count"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["unread_count"], 1)
        response = client.post(reverse("alert-mark-read", args=[alert.id]))
        self.assertEqual(response.status_code, 200)
        alert.refresh_from_db()
        self.assertTrue(alert.is_read)
        response = client.get(reverse("alert-unread-count"))
        self.assertEqual(response.data["unread_count"], 0)
        self.assertEqual(Alert.objects.filter(
            moto=self.moto,
            type=Alert.Type.GPS_DECONNECTE,
        ).count(), 1)

    def test_cdd_requires_valid_contract_dates(self):
        self.livreur.type_contrat = Livreur.TypeContrat.CDD
        with self.assertRaises(ValidationError):
            self.livreur.full_clean()
        self.livreur.date_debut_contrat = date(2026, 6, 1)
        self.livreur.date_fin_contrat = date(2026, 5, 1)
        with self.assertRaises(ValidationError):
            self.livreur.full_clean()
        self.livreur.date_fin_contrat = date(2026, 12, 31)
        self.livreur.full_clean()

    def test_manager_can_delete_alert(self):
        manager = User.objects.create_user("manager-delete", password="secret", is_staff=True)
        alert = Alert.objects.create(
            moto=self.moto,
            type=Alert.Type.SORTIE_ZONE,
            message="Sortie de zone.",
            incident_actif=True,
        )
        self.client.force_login(manager)
        response = self.client.post(reverse("alert_delete", args=[alert.id]))
        self.assertRedirects(response, reverse("alerts"))
        alert.refresh_from_db()
        self.assertTrue(alert.is_deleted)
        self.assertFalse(alerts_for_user(manager).filter(pk=alert.id).exists())

    def test_manager_does_not_receive_mission_cancelled_alert(self):
        manager = User.objects.create_user("manager-cancel", password="secret", is_staff=True)
        mission = Mission.objects.create(
            nom_client="Client annulé",
            telephone_client="760000002",
            adresse_livraison="Dakar",
            livreur=self.livreur,
            moto=self.moto,
        )
        mission.statut = Mission.Statut.ANNULEE
        mission.save()
        cancelled_alert = Alert.objects.get(
            mission=mission,
            type=Alert.Type.MISSION_ANNULEE,
        )
        self.assertFalse(alerts_for_user(manager).filter(pk=cancelled_alert.pk).exists())
        self.assertTrue(alerts_for_user(self.user).filter(pk=cancelled_alert.pk).exists())

    def test_manager_only_receives_validation_alert_for_missions(self):
        manager = User.objects.create_user("manager-mission-alerts", password="secret", is_staff=True)
        mission = Mission.objects.create(
            nom_client="Client validation",
            telephone_client="760000003",
            adresse_livraison="Thiès",
            livreur=self.livreur,
            moto=self.moto,
        )
        assigned_alert = Alert.objects.get(
            mission=mission,
            type=Alert.Type.MISSION_ASSIGNEE,
        )
        self.assertFalse(alerts_for_user(manager).filter(pk=assigned_alert.pk).exists())

        mission.validate_otp(mission.otp)
        validation_alert = Alert.objects.get(
            mission=mission,
            type=Alert.Type.VALIDATION_COMMANDE,
        )
        self.assertTrue(alerts_for_user(manager).filter(pk=validation_alert.pk).exists())

    def test_mission_api_returns_destination_and_last_position(self):
        manager = User.objects.create_user("manager-api", password="secret", is_staff=True)
        mission = Mission.objects.create(
            nom_client="Mamadou Diop",
            telephone_client="760000001",
            adresse_livraison="Bambey",
            destination_latitude="14.6928000",
            destination_longitude="-16.4665000",
            livreur=self.livreur,
            moto=self.moto,
        )
        PositionGPS.objects.create(
            moto=self.moto,
            latitude="14.6910000",
            longitude="-16.4657000",
        )
        client = APIClient()
        client.force_authenticate(manager)
        response = client.get(reverse("mission-detail", args=[mission.id]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(float(response.data["destination_latitude"]), 14.6928)
        self.assertEqual(float(response.data["destination_longitude"]), -16.4665)
        self.assertEqual(response.data["moto"]["immatriculation"], self.moto.immatriculation)
        self.assertEqual(float(response.data["last_position"]["latitude"]), 14.691)
        self.assertEqual(float(response.data["last_position"]["longitude"]), -16.4657)


@override_settings(GPS_API_KEY="test-key")
class DriverSpaceTests(TestCase):
    def setUp(self):
        self.driver_user = User.objects.create_user(
            "driver-one", password="secret", first_name="Moussa", last_name="Fall"
        )
        self.driver = Livreur.objects.create(
            user=self.driver_user, telephone="770000010", adresse="Bambey",
            numero_permis="PERMIS-10", numero_cni="CNI-10",
        )
        self.moto = Moto.objects.create(immatriculation="DK-010", marque="Honda", modele="CB")
        Affectation.objects.create(livreur=self.driver, moto=self.moto)
        self.mission = Mission.objects.create(
            nom_client="Client Livreur", telephone_client="770000011",
            adresse_livraison="Bambey", destination_latitude="14.6928000",
            destination_longitude="-16.4665000", livreur=self.driver, moto=self.moto,
        )
        self.other_user = User.objects.create_user("driver-two", password="secret")
        self.other_driver = Livreur.objects.create(
            user=self.other_user, telephone="770000020", adresse="Dakar",
            numero_permis="PERMIS-20", numero_cni="CNI-20",
        )
        self.other_moto = Moto.objects.create(immatriculation="DK-020", marque="Yamaha", modele="YBR")
        Affectation.objects.create(livreur=self.other_driver, moto=self.other_moto)
        self.other_mission = Mission.objects.create(
            nom_client="Autre Client", telephone_client="770000021",
            adresse_livraison="Dakar", livreur=self.other_driver, moto=self.other_moto,
        )

    def test_driver_login_redirects_to_dashboard(self):
        response = self.client.post(reverse("login"), {
            "username": "driver-one", "password": "secret",
        })
        self.assertEqual(response.status_code, 302)
        response = self.client.get(response.url, follow=True)
        self.assertRedirects(response, reverse("driver_space"))

    def test_manager_cannot_access_driver_pages(self):
        manager = User.objects.create_user("manager-driver-test", password="secret", is_staff=True)
        self.client.force_login(manager)
        response = self.client.get(reverse("driver_missions"))
        self.assertEqual(response.status_code, 302)

    def test_driver_profile_is_read_only(self):
        self.client.force_login(self.driver_user)
        response = self.client.post(reverse("driver_profile"), {
            "profile-telephone": "780000010",
            "profile-adresse": "Touba",
            "save_profile": "1",
        })
        self.assertEqual(response.status_code, 200)
        self.driver.refresh_from_db()
        self.assertEqual(self.driver.telephone, "770000010")
        self.assertEqual(self.driver.adresse, "Bambey")
        self.assertEqual(self.driver.numero_permis, "PERMIS-10")
        self.assertEqual(self.driver.numero_cni, "CNI-10")

        api = APIClient()
        api.force_authenticate(self.driver_user)
        response = api.get(reverse("driver-profile-api"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["numero_permis"], "PERMIS-10")
        response = api.patch(reverse("driver-profile-api"), {"telephone": "780000010"})
        self.assertEqual(response.status_code, 405)

    def test_driver_only_sees_own_missions(self):
        self.client.force_login(self.driver_user)
        response = self.client.get(reverse("driver_missions"))
        self.assertContains(response, "Client Livreur")
        self.assertNotContains(response, "Autre Client")
        self.assertEqual(
            self.client.get(reverse("driver_mission_detail", args=[self.other_mission.id])).status_code,
            404,
        )

    def test_driver_otp_validation_and_delivery_history(self):
        self.client.force_login(self.driver_user)
        response = self.client.post(
            reverse("driver_mission_detail", args=[self.mission.id]),
            {"otp": self.mission.otp},
        )
        self.assertEqual(response.status_code, 302)
        self.mission.refresh_from_db()
        self.assertEqual(self.mission.statut, Mission.Statut.TERMINEE)
        history = self.client.get(reverse("driver_deliveries"), {"q": "Client Livreur"})
        self.assertContains(history, "Client Livreur")
        self.assertNotContains(history, "Autre Client")

    def test_driver_alerts_are_filtered(self):
        own_alert = Alert.objects.create(
            mission=self.mission, moto=self.moto,
            type=Alert.Type.MISSION_ASSIGNEE, message="Alerte propre",
        )
        Alert.objects.create(
            mission=self.other_mission, moto=self.other_moto,
            type=Alert.Type.MISSION_ASSIGNEE, message="Alerte étrangère",
        )
        Alert.objects.create(
            mission=self.mission, moto=self.moto,
            type=Alert.Type.GPS_DECONNECTE, message="GPS à masquer",
        )
        api = APIClient()
        api.force_authenticate(self.driver_user)
        response = api.get(reverse("driver-alerts-api"))
        self.assertEqual(response.status_code, 200)
        messages = [item["message"] for item in response.data]
        self.assertIn(own_alert.message, messages)
        self.assertNotIn("Alerte étrangère", messages)
        self.assertNotIn("GPS à masquer", messages)

    def test_driver_pdf_download(self):
        self.mission.validate_otp(self.mission.otp)
        self.client.force_login(self.driver_user)
        response = self.client.get(reverse("driver_proof_pdf", args=[self.mission.id]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertTrue(response.content.startswith(b"%PDF"))
        self.assertIn(b"Signature numerique : MOTOTRACK", response.content)
        self.assertIn(b"Reference de preuve", response.content)

    def test_driver_can_delete_only_own_alert(self):
        own_alert = Alert.objects.filter(
            mission=self.mission,
            type=Alert.Type.MISSION_ASSIGNEE,
        ).first()
        other_alert = Alert.objects.filter(
            mission=self.other_mission,
            type=Alert.Type.MISSION_ASSIGNEE,
        ).first()
        self.client.force_login(self.driver_user)
        response = self.client.post(reverse("alert_delete", args=[own_alert.id]))
        self.assertRedirects(response, reverse("alerts"))
        own_alert.refresh_from_db()
        self.assertTrue(own_alert.is_deleted)
        response = self.client.post(reverse("alert_delete", args=[other_alert.id]))
        self.assertEqual(response.status_code, 404)
        other_alert.refresh_from_db()
        self.assertFalse(other_alert.is_deleted)


class AccountManagementTests(TestCase):
    def test_direct_link_to_any_interface_requires_fresh_login(self):
        manager = User.objects.create_user("responsable-direct-link", password="secret", is_staff=True)
        self.client.force_login(manager)

        response = self.client.get(
            reverse("livreurs"),
            HTTP_SEC_FETCH_SITE="none",
            HTTP_SEC_FETCH_MODE="navigate",
        )

        self.assertRedirects(response, reverse("login"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_internal_navigation_keeps_authenticated_session(self):
        manager = User.objects.create_user("responsable-internal-link", password="secret", is_staff=True)
        self.client.force_login(manager)

        response = self.client.get(
            reverse("livreurs"),
            HTTP_SEC_FETCH_SITE="same-origin",
            HTTP_SEC_FETCH_MODE="navigate",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("_auth_user_id", self.client.session)

    def test_root_entry_logs_out_existing_session(self):
        manager = User.objects.create_user("responsable-entry", password="secret", is_staff=True)
        self.client.force_login(manager)

        response = self.client.get(reverse("entry"))

        self.assertRedirects(response, reverse("login"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_manager_can_deactivate_and_reactivate_driver_account(self):
        manager = User.objects.create_user("responsable-toggle", password="secret", is_staff=True)
        driver_user = User.objects.create_user("livreur-toggle", password="secret")
        driver = Livreur.objects.create(
            user=driver_user,
            telephone="770000088",
            adresse="Dakar",
            numero_permis="PERMIS-TOGGLE",
            numero_cni="CNI-TOGGLE",
        )
        self.client.force_login(manager)

        response = self.client.post(reverse("livreurs"), {"toggle_active": driver.id})
        self.assertRedirects(response, reverse("livreurs"))
        driver.refresh_from_db()
        driver_user.refresh_from_db()
        self.assertFalse(driver.actif)
        self.assertFalse(driver_user.is_active)

        response = self.client.post(reverse("livreurs"), {"toggle_active": driver.id})
        self.assertRedirects(response, reverse("livreurs"))
        driver.refresh_from_db()
        driver_user.refresh_from_db()
        self.assertTrue(driver.actif)
        self.assertTrue(driver_user.is_active)

    def test_responsable_can_create_account(self):
        response = self.client.post(reverse("responsable_register"), {
            "username": "nouveau-responsable",
            "first_name": "Mame",
            "last_name": "Diop",
            "email": "responsable@mototrack.sn",
            "password1": "CompteResponsable2026!",
            "password2": "CompteResponsable2026!",
        })
        self.assertRedirects(response, reverse("dashboard"))
        user = User.objects.get(username="nouveau-responsable")
        self.assertTrue(user.is_staff)
        self.assertTrue(user.check_password("CompteResponsable2026!"))

    def test_responsable_can_change_driver_password_from_edit_form(self):
        manager = User.objects.create_user("responsable-password", password="secret", is_staff=True)
        driver_user = User.objects.create_user(
            "livreur-password",
            password="ancien-secret",
            first_name="Saliou",
            last_name="Diop",
        )
        driver = Livreur.objects.create(
            user=driver_user,
            telephone="770000099",
            adresse="Bambey",
            numero_permis="PERMIS-PASSWORD",
            numero_cni="CNI-PASSWORD",
        )
        self.client.force_login(manager)
        response = self.client.post(f"{reverse('livreurs')}?modifier={driver.id}", {
            "username": driver_user.username,
            "first_name": driver_user.first_name,
            "last_name": driver_user.last_name,
            "email": "",
            "password": "NouveauLivreur2026!",
            "password_confirm": "NouveauLivreur2026!",
            "age": "25",
            "telephone": driver.telephone,
            "adresse": driver.adresse,
            "numero_permis": driver.numero_permis,
            "numero_cni": driver.numero_cni,
            "type_contrat": Livreur.TypeContrat.CDI,
            "actif": "on",
        })
        self.assertRedirects(response, reverse("livreurs"))
        driver_user.refresh_from_db()
        self.assertTrue(driver_user.check_password("NouveauLivreur2026!"))
