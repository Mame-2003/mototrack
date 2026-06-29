from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, update_session_auth_hash
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import OuterRef, Subquery
from django.db.models.deletion import ProtectedError
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from datetime import timedelta

from .forms import (
    AffectationForm,
    LivreurForm,
    MissionForm,
    MotoForm,
    OTPForm,
    ProfileForm,
    ResponsableCreationForm,
    StyledPasswordChangeForm,
    DriverProfileForm,
)
from .models import Alert, Affectation, Livreur, Mission, Moto, PositionGPS, PreuveLivraison
from .alerting import alerts_for_user
from .pdf import delivery_proof_pdf


def service_worker(request):
    service_worker_path = settings.BASE_DIR / "static" / "service-worker.js"
    response = HttpResponse(
        service_worker_path.read_text(encoding="utf-8"),
        content_type="application/javascript",
    )
    response["Service-Worker-Allowed"] = "/"
    return response


def manager_required(view):
    return login_required(user_passes_test(lambda u: u.is_staff, login_url="driver_space")(view))


def driver_required(view):
    return login_required(user_passes_test(
        lambda u: not u.is_staff and hasattr(u, "livreur"),
        login_url="dashboard",
    )(view))


def responsable_register(request):
    if request.user.is_authenticated:
        return redirect("dashboard" if request.user.is_staff else "driver_space")
    form = ResponsableCreationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, "Votre compte responsable a ete cree.")
        return redirect("dashboard")
    return render(request, "registration/responsable_register.html", {"form": form})


@login_required
def dashboard(request):
    if not request.user.is_staff:
        return redirect("driver_space")
    latest_ids = PositionGPS.objects.filter(moto=OuterRef("pk")).order_by("-recue_le").values("id")[:1]
    ids = Moto.objects.annotate(pos_id=Subquery(latest_ids)).values_list("pos_id", flat=True)
    context = {
        "total_motos": Moto.objects.count(),
        "total_livreurs": Livreur.objects.filter(actif=True).count(),
        "livreurs_inactifs": Livreur.objects.filter(actif=False).count(),
        "missions_en_cours": Mission.objects.filter(statut=Mission.Statut.EN_COURS).count(),
        "missions_terminees": Mission.objects.filter(statut=Mission.Statut.TERMINEE).count(),
        "missions_en_attente": Mission.objects.filter(statut=Mission.Statut.EN_ATTENTE).count(),
        "missions_annulees": Mission.objects.filter(statut=Mission.Statut.ANNULEE).count(),
        "latest_positions": PositionGPS.objects.filter(id__in=[i for i in ids if i]).select_related("moto")[:6],
        "recent_missions": Mission.objects.select_related("livreur__user", "moto")[:6],
    }
    return render(request, "core/dashboard.html", context)


def _crud_page(request, model, form_class, template, context_name, edit_id=None):
    instance = get_object_or_404(model, pk=edit_id) if edit_id else None
    form = form_class(request.POST or None, request.FILES or None, instance=instance)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Enregistrement effectué avec succès.")
        return redirect(request.path)
    show_form = bool(instance or request.GET.get("ajouter") or request.method == "POST")
    return render(request, template, {
        context_name: model.objects.all(),
        "form": form,
        "editing": instance,
        "show_form": show_form,
    })


@manager_required
def motos_page(request):
    edit_id = request.GET.get("modifier")
    if request.method == "POST" and request.POST.get("delete"):
        try:
            get_object_or_404(Moto, pk=request.POST["delete"]).delete()
            messages.success(request, "Moto supprimée.")
        except ProtectedError:
            messages.error(request, "Cette moto est utilisée par une affectation ou une mission.")
        return redirect("motos")
    return _crud_page(request, Moto, MotoForm, "core/motos.html", "motos", edit_id)


@manager_required
def livreurs_page(request):
    edit_id = request.GET.get("modifier")
    if request.method == "POST" and request.POST.get("delete"):
        try:
            get_object_or_404(Livreur, pk=request.POST["delete"]).delete()
            messages.success(request, "Livreur supprimé.")
        except ProtectedError:
            messages.error(request, "Ce livreur est utilisé par une affectation ou une mission.")
        return redirect("livreurs")
    return _crud_page(request, Livreur, LivreurForm, "core/livreurs.html", "livreurs", edit_id)


@manager_required
def livreur_detail(request, pk):
    livreur = get_object_or_404(Livreur.objects.select_related("user"), pk=pk)
    affectation = livreur.affectations.filter(active=True).select_related("moto").first()
    return render(request, "core/livreur_detail.html", {
        "livreur": livreur,
        "affectation": affectation,
        "missions_count": livreur.missions.count(),
        "missions_terminees": livreur.missions.filter(statut=Mission.Statut.TERMINEE).count(),
    })


@manager_required
def affectations_page(request):
    edit_id = request.GET.get("modifier")
    if request.method == "POST" and request.POST.get("delete"):
        affectation = get_object_or_404(Affectation, pk=request.POST["delete"])
        moto = affectation.moto
        affectation.delete()
        if not Affectation.objects.filter(moto=moto, active=True).exists():
            moto.etat = Moto.Etat.DISPONIBLE
            moto.save(update_fields=["etat"])
        messages.success(request, "Affectation supprimée.")
        return redirect("affectations")
    return _crud_page(request, Affectation, AffectationForm, "core/affectations.html", "affectations", edit_id)


@manager_required
def missions_page(request):
    edit_id = request.GET.get("modifier")
    if request.method == "POST" and request.POST.get("delete"):
        mission = get_object_or_404(Mission, pk=request.POST["delete"])
        mission.delete()
        messages.success(request, "Mission supprimée.")
        return redirect("missions")
    return _crud_page(request, Mission, MissionForm, "core/missions.html", "missions", edit_id)


@login_required
def mission_detail(request, pk):
    mission = get_object_or_404(Mission.objects.select_related("livreur__user", "moto"), pk=pk)
    if not request.user.is_staff and mission.livreur.user_id != request.user.id:
        return redirect("driver_space")
    form = OTPForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            mission.validate_otp(form.cleaned_data["otp"])
            messages.success(request, "Livraison validée. La preuve a été enregistrée.")
            return redirect("mission_detail", pk=pk)
        except ValidationError as exc:
            form.add_error("otp", exc.messages[0])
    return render(request, "core/mission_detail.html", {
        "mission": mission,
        "form": form,
        "latest_position": mission.moto.positions.order_by("-recue_le").first(),
    })


@manager_required
def map_page(request):
    return render(request, "core/map.html", {"motos": Moto.objects.all()})


@manager_required
def proofs_page(request):
    proofs = PreuveLivraison.objects.select_related("mission__livreur__user", "mission__moto")
    return render(request, "core/proofs.html", {"proofs": proofs})


@login_required
def profile_page(request):
    profile_form = ProfileForm(request.POST or None, instance=request.user, prefix="profile")
    password_form = StyledPasswordChangeForm(request.user, request.POST or None, prefix="password")

    if request.method == "POST":
        if "save_profile" in request.POST and profile_form.is_valid():
            profile_form.save()
            messages.success(request, "Votre profil a été mis à jour.")
            return redirect("profile")
        if "change_password" in request.POST and password_form.is_valid():
            user = password_form.save()
            update_session_auth_hash(request, user)
            messages.success(request, "Votre mot de passe a été modifié.")
            return redirect("profile")

    return render(request, "core/profile.html", {
        "profile_form": profile_form,
        "password_form": password_form,
    })


@login_required
def alerts_page(request):
    return render(request, "core/alerts.html", {"alerts": alerts_for_user(request.user)})


@login_required
def alert_mark_read(request, pk):
    if request.method == "POST":
        alert = get_object_or_404(alerts_for_user(request.user), pk=pk)
        alert.is_read = True
        alert.save(update_fields=["is_read"])
        messages.success(request, "Alerte marquée comme lue.")
    return redirect("alerts")


@login_required
def alert_delete(request, pk):
    if request.method == "POST":
        alert = get_object_or_404(alerts_for_user(request.user), pk=pk)
        alert.is_deleted = True
        alert.is_read = True
        alert.save(update_fields=["is_deleted", "is_read"])
        messages.success(request, "Alerte supprimée.")
    return redirect("alerts")


@driver_required
def driver_space(request):
    livreur = request.user.livreur
    missions = Mission.objects.filter(livreur=livreur).select_related("moto")
    affectation = Affectation.objects.filter(livreur=livreur, active=True).select_related("moto").first()
    moto = affectation.moto if affectation else None
    latest_position = moto.positions.order_by("-recue_le").first() if moto else None
    return render(request, "driver/dashboard.html", {
        "livreur": livreur,
        "affectation": affectation,
        "latest_position": latest_position,
        "missions_en_attente": missions.filter(statut=Mission.Statut.EN_ATTENTE).count(),
        "missions_en_cours": missions.filter(statut=Mission.Statut.EN_COURS).count(),
        "missions_terminees": missions.filter(statut=Mission.Statut.TERMINEE).count(),
        "missions_annulees": missions.filter(statut=Mission.Statut.ANNULEE).count(),
        "total_livraisons": missions.filter(statut=Mission.Statut.TERMINEE).count(),
        "recent_missions": missions[:5],
        "priority_mission": missions.filter(
            statut__in=[Mission.Statut.EN_COURS, Mission.Statut.EN_ATTENTE]
        ).order_by(
            models.Case(
                models.When(statut=Mission.Statut.EN_COURS, then=0),
                default=1,
                output_field=models.IntegerField(),
            ),
            "cree_le",
        ).first(),
    })


@driver_required
def driver_profile(request):
    livreur = request.user.livreur
    return render(request, "driver/profile.html", {"livreur": livreur})


@driver_required
def driver_moto(request):
    affectation = Affectation.objects.filter(
        livreur=request.user.livreur, active=True
    ).select_related("moto").first()
    moto = affectation.moto if affectation else None
    latest_position = moto.positions.order_by("-recue_le").first() if moto else None
    return render(request, "driver/moto.html", {
        "affectation": affectation,
        "moto": moto,
        "latest_position": latest_position,
    })


@driver_required
def driver_missions(request):
    missions = Mission.objects.filter(livreur=request.user.livreur).select_related("moto")
    return render(request, "driver/missions.html", {"missions": missions})


@driver_required
def driver_mission_detail(request, pk):
    mission = get_object_or_404(
        Mission.objects.select_related("moto", "livreur__user"),
        pk=pk,
        livreur=request.user.livreur,
    )
    form = OTPForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            mission.validate_otp(form.cleaned_data["otp"])
            messages.success(request, "Livraison validée avec succès.")
            return redirect("driver_mission_detail", pk=mission.pk)
        except ValidationError as exc:
            form.add_error("otp", exc.messages[0])
    return render(request, "driver/mission_detail.html", {
        "mission": mission,
        "form": form,
        "latest_position": mission.moto.positions.order_by("-recue_le").first(),
    })


@driver_required
def driver_deliveries(request):
    missions = Mission.objects.filter(
        livreur=request.user.livreur,
        statut=Mission.Statut.TERMINEE,
    ).select_related("moto", "preuve")
    period = request.GET.get("periode", "")
    search = request.GET.get("q", "").strip()
    now = timezone.localtime()
    if period == "today":
        missions = missions.filter(valide_le__date=now.date())
    elif period == "week":
        missions = missions.filter(valide_le__gte=now - timedelta(days=7))
    elif period == "month":
        missions = missions.filter(valide_le__year=now.year, valide_le__month=now.month)
    if search:
        missions = missions.filter(nom_client__icontains=search)
    return render(request, "driver/deliveries.html", {
        "missions": missions,
        "period": period,
        "search": search,
    })


@driver_required
def driver_proof(request, pk):
    proof = get_object_or_404(
        PreuveLivraison.objects.select_related("mission__moto", "mission__livreur__user"),
        mission_id=pk,
        mission__livreur=request.user.livreur,
    )
    return render(request, "driver/proof.html", {"proof": proof})


@driver_required
def driver_proof_pdf(request, pk):
    proof = get_object_or_404(
        PreuveLivraison.objects.select_related("mission__moto", "mission__livreur__user"),
        mission_id=pk,
        mission__livreur=request.user.livreur,
    )
    response = HttpResponse(delivery_proof_pdf(proof), content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="preuve-mission-{pk}.pdf"'
    return response
