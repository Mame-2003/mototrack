from django import forms
from django.contrib.auth.forms import PasswordChangeForm, UserCreationForm
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.models import User
from django.db import transaction

from .models import Affectation, Livreur, Mission, Moto, ProfilUtilisateur


class StyledModelForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")


class MotoForm(StyledModelForm):
    class Meta:
        model = Moto
        fields = ["immatriculation", "marque", "modele", "etat"]


class LivreurForm(StyledModelForm):
    username = forms.CharField(label="Nom d'utilisateur")
    first_name = forms.CharField(label="Prénom")
    last_name = forms.CharField(label="Nom")
    email = forms.EmailField(required=False)
    password = forms.CharField(
        label="Nouveau mot de passe",
        widget=forms.PasswordInput,
        required=False,
        help_text="Laissez vide pour conserver le mot de passe actuel.",
    )
    password_confirm = forms.CharField(
        label="Confirmer le nouveau mot de passe",
        widget=forms.PasswordInput,
        required=False,
    )

    class Meta:
        model = Livreur
        fields = [
            "age", "telephone", "adresse", "numero_permis", "numero_cni", "photo",
            "type_contrat", "date_debut_contrat", "date_fin_contrat", "contrat", "actif",
        ]
        widgets = {
            "date_debut_contrat": forms.DateInput(attrs={"type": "date"}),
            "date_fin_contrat": forms.DateInput(attrs={"type": "date"}),
        }
        labels = {
            "age": "Age",
            "type_contrat": "Type de contrat",
            "date_debut_contrat": "Date de début du contrat",
            "date_fin_contrat": "Date de fin du contrat",
            "contrat": "Document du contrat",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            user = self.instance.user
            for name in ["username", "first_name", "last_name", "email"]:
                self.fields[name].initial = getattr(user, name)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")
        self.fields["type_contrat"].widget.attrs["data-contract-type"] = "true"
        self.fields["date_debut_contrat"].widget.attrs["data-contract-start"] = "true"
        self.fields["date_fin_contrat"].widget.attrs["data-contract-end"] = "true"

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        users = User.objects.filter(username__iexact=username)
        if self.instance.pk:
            users = users.exclude(pk=self.instance.user_id)
        if users.exists():
            raise forms.ValidationError("Ce nom d'utilisateur est déjà utilisé.")
        return username

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        password_confirm = cleaned_data.get("password_confirm")
        if password or password_confirm:
            if password != password_confirm:
                self.add_error("password_confirm", "Les deux mots de passe ne correspondent pas.")
            elif password:
                validate_password(password, self.instance.user if self.instance.pk else None)
        return cleaned_data

    @transaction.atomic
    def save(self, commit=True):
        livreur = super().save(commit=False)
        if livreur.pk:
            user = livreur.user
        else:
            user = User()
        for name in ["username", "first_name", "last_name", "email"]:
            setattr(user, name, self.cleaned_data[name])
        if self.cleaned_data.get("password"):
            user.set_password(self.cleaned_data["password"])
        elif not user.pk:
            user.set_unusable_password()
        user.save()
        livreur.user = user
        if commit:
            livreur.save()
        return livreur


class AffectationForm(StyledModelForm):
    class Meta:
        model = Affectation
        fields = ["livreur", "moto", "date_debut", "date_fin", "active"]
        widgets = {
            "date_debut": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "date_fin": forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }


class MissionStatusSelect(forms.Select):
    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex, attrs)
        if value == Mission.Statut.TERMINEE and not selected:
            option["attrs"]["disabled"] = True
            option["label"] = f"{label} (validation OTP requise)"
        return option


class MissionForm(StyledModelForm):
    class Meta:
        model = Mission
        fields = [
            "nom_client", "telephone_client", "adresse_livraison",
            "description_lieu", "destination_latitude", "destination_longitude",
            "livreur", "moto", "statut",
        ]
        widgets = {
            "description_lieu": forms.Textarea(attrs={"rows": 3}),
            "destination_latitude": forms.NumberInput(attrs={"step": "any", "id": "id_destination_latitude"}),
            "destination_longitude": forms.NumberInput(attrs={"step": "any", "id": "id_destination_longitude"}),
            "statut": MissionStatusSelect(),
        }
        labels = {
            "destination_latitude": "Latitude de destination",
            "destination_longitude": "Longitude de destination",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["statut"].choices = Mission.Statut.choices
        if self.instance.pk and self.instance.statut == Mission.Statut.TERMINEE:
            self.fields["statut"].disabled = True


class OTPForm(forms.Form):
    otp = forms.CharField(
        label="Code OTP",
        min_length=6,
        max_length=6,
        widget=forms.TextInput(attrs={"class": "form-control otp-input", "inputmode": "numeric", "placeholder": "000000"}),
    )


class ProfileForm(forms.ModelForm):
    telephone = forms.CharField(label="Numéro de téléphone", required=False)

    class Meta:
        model = User
        fields = ["first_name", "last_name", "email"]
        labels = {"first_name": "Prénom", "last_name": "Nom", "email": "Adresse e-mail"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        livreur = getattr(self.instance, "livreur", None)
        profil = getattr(self.instance, "profil", None)
        self.fields["telephone"].initial = livreur.telephone if livreur else getattr(profil, "telephone", "")
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")

    @transaction.atomic
    def save(self, commit=True):
        user = super().save(commit=commit)
        telephone = self.cleaned_data.get("telephone", "")
        livreur = getattr(user, "livreur", None)
        if livreur:
            livreur.telephone = telephone
            livreur.save(update_fields=["telephone"])
        else:
            ProfilUtilisateur.objects.update_or_create(user=user, defaults={"telephone": telephone})
        return user


class StyledPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")


class ResponsableCreationForm(UserCreationForm):
    first_name = forms.CharField(label="Prenom")
    last_name = forms.CharField(label="Nom")
    email = forms.EmailField(label="Adresse e-mail")

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ["username", "first_name", "last_name", "email"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Cette adresse e-mail est deja utilisee.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"].strip().lower()
        user.is_staff = True
        if commit:
            user.save()
        return user


class DriverProfileForm(StyledModelForm):
    class Meta:
        model = Livreur
        fields = ["telephone", "adresse", "photo"]
        labels = {
            "telephone": "Numéro de téléphone",
            "adresse": "Adresse",
            "photo": "Photo de profil",
        }
