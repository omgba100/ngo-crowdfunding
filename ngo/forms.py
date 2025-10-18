# ngo/forms.py
from django import forms
from django.contrib.auth.forms import PasswordResetForm
from django.forms import ModelForm
from django.utils.translation import gettext_lazy as _
from django.forms.widgets import ClearableFileInput
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Row, Field, Column,HTML,Fieldset,Div
from .models import User,ContactMessage,Project,Payment,IntermediairePayment,Message,WithdrawalRequest,EntrepreneurProfile,InvestisseurProfile,IntermediaireProfile,Country
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import authenticate
from django.contrib.auth import get_user_model

User = get_user_model()

class ContactForm(forms.ModelForm):
    class Meta:
        model = ContactMessage
        fields = ["name", "email", "subject", "message"]

        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Votre nom"}),
            "email": forms.EmailInput(attrs={"class": "form-control", "placeholder": "Votre email"}),
            "subject": forms.TextInput(attrs={"class": "form-control", "placeholder": "Sujet"}),
            "message": forms.Textarea(attrs={"class": "form-control", "rows": 5, "placeholder": "Votre message"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = "post"
        self.helper.layout = Layout(
            Row(
                Column("name", css_class="col-md-6"),
                Column("email", css_class="col-md-6"),
            ),
            "subject",
            "message",
            Submit("submit", "Envoyer", css_class="btn btn-primary w-100 mt-3")
        )

# --------------------------
# Formulaire de base
# --------------------------
class BaseRegisterForm(UserCreationForm):
    full_name = forms.CharField(
        label="Nom complet",
        widget=forms.TextInput(attrs={
            'placeholder': 'Entrez votre nom complet',
            'class': 'form-control'
        })
    )
    city = forms.CharField(
        label="Ville",
        widget=forms.TextInput(attrs={
            'placeholder': 'Ville de résidence',
            'class': 'form-control'
        })
    )

    class Meta:
        model = User
        fields = ("email", "full_name", "city", "password1", "password2")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = "post"
        self.helper.form_class = "card p-4 shadow-lg border-0 bg-light"
        self.helper.label_class = "text-title fw-bold"
        self.helper.field_class = "mb-3"
        self.helper.form_tag = False  # important car ton <form> est déjà dans le template

        self.helper.layout = Layout(
            HTML("<h3 class='text-center mb-4' style='color: var(--text-title);'>Créer un compte</h3>"),

            Row(
                Column("full_name", css_class="col-md-6"),
                Column("city", css_class="col-md-6"),
            ),

            "email",

            Row(
                Column("password1", css_class="col-md-6"),
                Column("password2", css_class="col-md-6"),
            ),

            # Le bouton sera dans le template, donc pas nécessaire ici
        )


# --------------------------
# Formulaire Investisseur
# --------------------------
class InvestisseurRegisterForm(BaseRegisterForm):
    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = "investisseur"
        if commit:
            user.save()  
        return user

# --------------------------
# Entrepreneurs
# --------------------------
class EntrepreneurRegisterForm(BaseRegisterForm):
    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = "entrepreneur"
        if commit:
            user.save()
        return user


# --------------------------
# Intermédiaires
# --------------------------
class IntermediaireRegisterForm(BaseRegisterForm):
    organization = forms.CharField(label="Organisation", widget=forms.TextInput(attrs={'placeholder': 'Nom de votre organisation'}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper.layout.insert(
            3, "organization"
        )

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = "intermediaire"
        if commit:
            user.save()
        return user

# --------------------------
# Login Form
# --------------------------
class CustomLoginForm(AuthenticationForm):
    username = forms.EmailField(
        label="Adresse e-mail",
        widget=forms.EmailInput(attrs={"placeholder": "Entrez votre e-mail"}),
    )
    password = forms.CharField(
        label="Mot de passe",
        widget=forms.PasswordInput(attrs={"placeholder": "Entrez votre mot de passe"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = "post"
        self.helper.form_class = "card p-4 shadow-lg border-0"
        self.helper.layout = Layout(
            HTML("<h3 class='text-center mb-4' style='color: var(--text-title);'>Connexion</h3>"),
            "username",
            "password",
            Submit(
                "submit",
                "Se connecter",
                css_class="btn w-100 mt-3 fw-bold",
                style="background-color: var(--bg-secondary); color: var(--text-white); border-radius: 10px;"
            )
        )

    def clean(self):
        """
        On renvoie le champ 'username' avec l'email pour que Django Auth fonctionne.
        """
        cleaned_data = super().clean()
        email = cleaned_data.get("username")
        password = cleaned_data.get("password")

        if email and password:
            # Force Django à vérifier avec email
            self.user_cache = authenticate(self.request, email=email, password=password)
            if self.user_cache is None:
                raise forms.ValidationError("Adresse e-mail ou mot de passe invalide.")
        return cleaned_data

# --------------------------
# Password Reset Form
# --------------------------
class UniversalPasswordResetForm(PasswordResetForm):
    email = forms.EmailField(
        label="Adresse e-mail",
        widget=forms.EmailInput(attrs={
            "placeholder": "Entrez votre e-mail",
        })
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.form_method = "post"
        self.helper.form_class = "card p-6 shadow-lg border-0 rounded-3xl"
        self.helper.layout = Layout(
            HTML("<h3 class='text-center mb-4' style='color: var(--text-title);'>Réinitialiser votre mot de passe</h3>"),
            Field("email", css_class="form-control mb-3", placeholder="Entrez votre e-mail"),
            Submit(
                "submit",
                "Envoyer le lien de réinitialisation",
                css_class="btn w-100 fw-bold",
                style="background-color: var(--bg-secondary); color: var(--text-white); border-radius: 12px; padding: 0.75rem;"
            ),
        )

# --------------------------
# Project Form
# --------------------------
class ProjectForm(ModelForm):
    class Meta:
        model = Project
        fields = [
            "title", "short_description", "description", "country",
            "categories", "target_amount", "deadline", "image"
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 5}),
            "deadline": forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = "post"
        self.helper.form_class = "card p-4 shadow border-0"
        self.helper.layout = Layout(
            HTML("<h4 class='text-center mb-4 fw-bold' style='color: var(--text-title);'>Créer / Modifier un Projet</h4>"),
            "title",
            "short_description",
            "description",
            Row(
                Column("country", css_class="col-md-6"),
                Column("categories", css_class="col-md-6"),
            ),
            Row(
                Column("target_amount", css_class="col-md-6"),
                Column("deadline", css_class="col-md-6"),
            ),
            "image",
            Submit("submit", "Enregistrer", css_class="btn btn-primary w-100 fw-bold mt-3")
        )

# --------------------------
# Preuve de Paiement
# --------------------------
class ProjectPaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ["proof"]

    proof = forms.ImageField(
        label="Preuve de paiement",
        required=True,
        widget=forms.ClearableFileInput(attrs={"class": "form-control"})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = "post"
        self.helper.form_class = "card p-4 shadow-lg border-0"
        self.helper.layout = Layout(
            Field("proof"),
            Submit(
                "submit", 
                "Soumettre le paiement", 
                css_class="btn w-100 mt-3",
                style="background-color: var(--bg-secondary); color: var(--text-white); font-weight: bold; border-radius: 10px;"
            )
        )

# --------------------------------
# Preuve de Paiement intermediaire
# --------------------------------
class IntermediairePaymentForm(forms.ModelForm):
    class Meta:
        model = IntermediairePayment
        fields = ("amount", "currency", "proof")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = "post"
        self.helper.form_class = "card p-4 shadow-lg border-0"
        self.helper.layout = Layout(
            "amount",
            "currency",
            "proof",
            Submit("submit", "Envoyer la preuve de paiement", css_class="btn w-100", style="background-color: var(--bg-secondary); color: var(--text-white); font-weight:bold;")
        )

# --------------------------------
# Message
# --------------------------------
class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ['subject', 'body', 'project']  # ✅ on retire 'recipient'
        labels = {
            'subject': _("Objet"),
            'body': _("Contenu"),
            'project': _("Projet associé"),
        }
        widgets = {
            'body': forms.Textarea(attrs={'rows': 5, 'placeholder': _('Saisissez votre message ici...')}),
        }

    def __init__(self, *args, **kwargs):
        # ✅ on récupère le sender depuis la vue
        self.sender = kwargs.pop('sender', None)
        super().__init__(*args, **kwargs)

        # ✅ configuration du style Bootstrap/Crispy
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_class = 'needs-validation'
        self.helper.label_class = 'form-label'
        self.helper.field_class = 'mb-3'
        self.helper.add_input(Submit('submit', _('Envoyer'), css_class='btn btn-primary w-100'))

        # ✅ adapter les projets visibles selon le rôle du sender
        if self.sender:
            role = getattr(self.sender, 'role', None)

            if role == 'entrepreneur':
                # 🔸 L’entrepreneur ne peut sélectionner que ses propres projets
                self.fields['project'].queryset = Project.objects.filter(owner=self.sender)

            elif role == 'intermediaire':
                # 🔸 L’intermédiaire peut voir les projets des entrepreneurs qu’il représente
                if hasattr(self.sender, 'intermediaire_profile'):
                    represented_users = self.sender.intermediaire_profile.represented_entrepreneurs.all()
                    self.fields['project'].queryset = Project.objects.filter(owner__in=represented_users)
                else:
                    self.fields['project'].queryset = Project.objects.none()

            else:
                # 🔸 L’investisseur ou autre rôle ne peut associer aucun projet
                self.fields['project'].queryset = Project.objects.none()
                self.fields['project'].widget.attrs['disabled'] = True

    def clean_project(self):
        """✅ Vérifie que le projet appartient bien à un entrepreneur légitime."""
        project = self.cleaned_data.get('project')

        if not self.sender or not project:
            return project

        role = getattr(self.sender, 'role', None)

        if role == 'entrepreneur' and project.owner != self.sender:
            raise forms.ValidationError(_("Ce projet ne vous appartient pas."))

        elif role == 'intermediaire':
            if hasattr(self.sender, 'intermediaire_profile'):
                represented_users = self.sender.intermediaire_profile.represented_entrepreneurs.all()
                if project.owner not in represented_users:
                    raise forms.ValidationError(_("Vous ne représentez pas l’entrepreneur de ce projet."))
            else:
                raise forms.ValidationError(_("Aucun lien avec un entrepreneur n’a été trouvé."))

        return project

    def save(self, commit=True):
        msg = super().save(commit=False)

        # ✅ définit automatiquement l’expéditeur
        msg.sender = self.sender

        # ✅ force le destinataire à être l’administrateur
        admin_user = User.objects.filter(is_superuser=True).first()
        msg.recipient = admin_user

        if commit:
            msg.save()
        return msg

# ----------------------------------------------------------
# Demande de Retrait des fonds par l'entrepreneur formulaire
# ----------------------------------------------------------
class WithdrawalRequestForm(forms.ModelForm):
    class Meta:
        model = WithdrawalRequest
        fields = ["amount", "reason"]
        widgets = {
            "reason": forms.Textarea(attrs={"rows": 3, "placeholder": _("Expliquez le motif de votre retrait (facultatif)")}),
        }

    def __init__(self, *args, **kwargs):
        project = kwargs.pop("project", None)  # pour afficher les infos du projet
        super().__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.form_method = "post"
        self.helper.form_class = "card shadow-lg p-4 border-0 bg-light"
        self.helper.label_class = "fw-semibold"
        self.helper.field_class = "mb-3"

        # Design moderne avec sections claires
        self.helper.layout = Layout(
            HTML("<h4 class='text-center text-primary fw-bold mb-4'>💰 {% trans 'Demande de retrait de fonds' %}</h4>"),
            HTML(f"""
                <div class='alert alert-info'>
                    <strong>{_('Projet')} :</strong> {project.title if project else ''}
                    <br>
                    <strong>{_('Montant disponible')} :</strong> {getattr(project, 'collected_amount', 0)} FCFA
                </div>
            """),
            Row(
                Column("amount", css_class="col-md-6"),
                Column("reason", css_class="col-md-6"),
            ),
            HTML("<hr>"),
            Submit("submit", _("Soumettre la demande"), css_class="btn btn-primary btn-lg w-100 fw-bold mt-3"),
        )

# --------------------------------
# Mise a jour de User
# --------------------------------
class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = [
            "full_name",
            "email",
            "phone",
            "country",
            "city",
            "profile_image",
            "bio",
        ]
        labels = {
            "full_name": _("Nom complet"),
            "email": _("Adresse e-mail"),
            "phone": _("Téléphone"),
            "country": _("Pays"),
            "city": _("Ville"),
            "profile_image": _("Photo de profil"),
            "bio": _("Biographie"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # ✅ Crispy Forms helper
        self.helper = FormHelper()
        self.helper.form_method = "post"
        self.helper.form_show_labels = True
        self.helper.enctype = "multipart/form-data"
        self.helper.label_class = "fw-bold text-primary"
        self.helper.field_class = "mb-3"

        # ✅ Mise en page responsive avec Bootstrap 5
        self.helper.layout = Layout(
            Fieldset(
                _("Informations personnelles"),
                Row(
                    Column("full_name", css_class="col-md-6"),
                    Column("email", css_class="col-md-6"),
                ),
                Row(
                    Column("phone", css_class="col-md-6"),
                    Column("country", css_class="col-md-6"),
                ),
                Row(
                    Column("city", css_class="col-md-6"),
                    Column("profile_image", css_class="col-md-6"),
                ),
                "bio",
            ),
            Submit("submit", _("Mettre à jour le profil"), css_class="btn btn-primary px-4 mt-3 float-end"),
        )
# ----------------------------------------------------------
# Formulaire pour mettre le profil de l'entrepreneur a jour 
# ----------------------------------------------------------
class EntrepreneurProfileForm(forms.ModelForm):
    # Champs venant du modèle User
    full_name = forms.CharField(label=_("Nom complet"), required=False)
    email = forms.EmailField(label=_("Adresse e-mail"), required=False)
    phone = forms.CharField(label=_("Téléphone"), required=False)
    country = forms.ModelChoiceField(
        queryset=User._meta.get_field("country").remote_field.model.objects.all(),
        label=_("Pays"),
        required=False
    )
    city = forms.CharField(label=_("Ville"), required=False)
    profile_image = forms.ImageField(label=_("Photo de profil"), required=False)
    bio = forms.CharField(
        label=_("Biographie"),
        widget=forms.Textarea(attrs={"rows": 3, "placeholder": _("Présentez-vous brièvement...")}),
        required=False,
    )
    password = forms.CharField(
        label=_("Mot de passe"),
        widget=forms.PasswordInput(render_value=False, attrs={"placeholder": _("••••••••")}),
        required=False,
        help_text=_("Laissez vide pour ne pas changer le mot de passe."),
    )

    class Meta:
        model = EntrepreneurProfile
        fields = [
            "company_name",
            "experience",
        ]
        labels = {
            "company_name": _("Nom de l'entreprise"),
            "experience": _("Expérience professionnelle"),
        }
        widgets = {
            "experience": forms.Textarea(attrs={"rows": 3, "placeholder": _("Décrivez votre expérience...")}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)  # Permet de passer l'utilisateur depuis la vue
        super().__init__(*args, **kwargs)

        # ✅ Pré-remplissage des champs User
        if user:
            self.fields["full_name"].initial = user.full_name
            self.fields["email"].initial = user.email
            self.fields["phone"].initial = user.phone
            self.fields["country"].initial = user.country
            self.fields["city"].initial = user.city
            self.fields["profile_image"].initial = user.profile_image
            self.fields["bio"].initial = user.bio

        # ✅ Crispy Forms Helper
        self.helper = FormHelper()
        self.helper.form_method = "post"
        self.helper.form_show_labels = True
        self.helper.enctype = "multipart/form-data"
        self.helper.label_class = "fw-bold text-primary"
        self.helper.field_class = "mb-3"

        # ✅ Mise en page avec sections claires
        self.helper.layout = Layout(
            Fieldset(
                _("Informations personnelles"),
                Row(
                    Column("full_name", css_class="col-md-6"),
                    Column("email", css_class="col-md-6"),
                ),
                Row(
                    Column("phone", css_class="col-md-6"),
                    Column("country", css_class="col-md-6"),
                ),
                Row(
                    Column("city", css_class="col-md-6"),
                    Column("profile_image", css_class="col-md-6"),
                ),
                "bio",
            ),
            Fieldset(
                _("Informations professionnelles"),
                Row(
                    Column("company_name", css_class="col-md-6"),
                    Column("experience", css_class="col-md-6"),
                ),
            ),
            Fieldset(
                _("Sécurité du compte"),
                "password",
            ),
            Submit("submit", _("Enregistrer les modifications"), css_class="btn btn-success px-4 mt-3 float-end"),
        )

    def clean_password(self):
        password = self.cleaned_data.get("password")
        if password and len(password) < 8:
            raise forms.ValidationError(_("Le mot de passe doit contenir au moins 8 caractères."))
        return password

    def save(self, commit=True):
        """Sauvegarde à la fois les données User et EntrepreneurProfile"""
        profile = super().save(commit=False)
        user = profile.user

        # Mise à jour des champs User
        user.full_name = self.cleaned_data.get("full_name")
        user.email = self.cleaned_data.get("email")
        user.phone = self.cleaned_data.get("phone")
        user.country = self.cleaned_data.get("country")
        user.city = self.cleaned_data.get("city")
        user.bio = self.cleaned_data.get("bio")

        if self.cleaned_data.get("profile_image"):
            user.profile_image = self.cleaned_data.get("profile_image")

        password = self.cleaned_data.get("password")
        if password:
            user.set_password(password)

        if commit:
            user.save()
            profile.user = user
            profile.save()
        return profile


# ----------------------------------------------------------
# Formulaire pour mettre le profil de l'investisseur a jour 
# ----------------------------------------------------------
class InvestisseurProfileForm(forms.ModelForm):
    # Champs liés à User
    full_name = forms.CharField(label="Nom complet")
    email = forms.EmailField(label="Email")
    phone = forms.CharField(label="Téléphone", required=False)
    country = forms.ModelChoiceField(
        queryset=None,  # défini dynamiquement dans __init__
        label="Pays",
        required=False
    )
    city = forms.CharField(label="Ville", required=False)
    profile_image = forms.ImageField(label="Photo de profil", required=False)
    bio = forms.CharField(label="Bio", widget=forms.Textarea(attrs={"rows": 3}), required=False)
    password = forms.CharField(label="Mot de passe", widget=forms.PasswordInput, required=False)

    class Meta:
        model = InvestisseurProfile
        fields = [
            "full_name", "email", "phone", "country", "city",
            "profile_image", "bio", "password",
            "company", "capital_available", "image",
        ]

    def __init__(self, *args, **kwargs):
        from .models import Country  # import ici pour éviter les boucles
        super().__init__(*args, **kwargs)

        # Charger les pays dans le champ
        self.fields["country"].queryset = Country.objects.all()

        # Crispy Form Helper
        self.helper = FormHelper()
        self.helper.form_method = "post"
        self.helper.form_enctype = "multipart/form-data"
        self.helper.layout = Layout(
            Row(
                Column("full_name", css_class="col-md-6"),
                Column("email", css_class="col-md-6"),
            ),
            Row(
                Column("phone", css_class="col-md-6"),
                Column("password", css_class="col-md-6"),
            ),
            Row(
                Column("country", css_class="col-md-6"),
                Column("city", css_class="col-md-6"),
            ),
            Row(
                Column("company", css_class="col-md-6"),
                Column("capital_available", css_class="col-md-6"),
            ),
            "bio",
            Row(
                Column("profile_image", css_class="col-md-6"),
                Column("image", css_class="col-md-6"),
            ),
            Submit("submit", "Enregistrer le profil", css_class="btn btn-primary w-100 mt-3")
        )

    def save(self, commit=True):
        """Sauvegarde le profil et met à jour les infos de l’utilisateur lié."""
        profile = super().save(commit=False)
        user = profile.user

        user.full_name = self.cleaned_data.get("full_name")
        user.email = self.cleaned_data.get("email")
        user.phone = self.cleaned_data.get("phone")
        user.country = self.cleaned_data.get("country")
        user.city = self.cleaned_data.get("city")
        user.bio = self.cleaned_data.get("bio")

        if self.cleaned_data.get("profile_image"):
            user.profile_image = self.cleaned_data["profile_image"]

        if self.cleaned_data.get("password"):
            user.set_password(self.cleaned_data["password"])

        if commit:
            user.save()
            profile.user = user
            profile.save()
        return profile


# ----------------------------------------------------------
# Formulaire pour mettre le profil de l'intermediaire a jour 
# ----------------------------------------------------------
class IntermediaireProfileForm(forms.ModelForm):
    # Champs liés à User
    full_name = forms.CharField(label="Nom complet")
    email = forms.EmailField(label="Email")
    phone = forms.CharField(label="Téléphone", required=False)
    country = forms.ModelChoiceField(
        queryset=Country.objects.all(),
        label="Pays",
        required=False
    )
    city = forms.CharField(label="Ville", required=False)
    profile_image = forms.ImageField(label="Photo de profil", required=False)
    bio = forms.CharField(label="Bio", widget=forms.Textarea(attrs={"rows": 3}), required=False)
    password = forms.CharField(label="Mot de passe", widget=forms.PasswordInput, required=False)

    class Meta:
        model = IntermediaireProfile
        fields = [
            "full_name", "email", "phone", "country", "city",
            "profile_image", "bio", "password",
            "organization", "verified", "subscription_paid",
            "subscription_date", "represented_entrepreneurs"
        ]
        widgets = {
            "subscription_date": forms.DateInput(attrs={"type": "date"}),
            "represented_entrepreneurs": forms.SelectMultiple(attrs={"class": "select2"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Initialisation Crispy Forms
        self.helper = FormHelper()
        self.helper.form_method = "post"
        self.helper.form_enctype = "multipart/form-data"
        self.helper.layout = Layout(
            Fieldset(
                "Informations personnelles",
                Row(
                    Column("full_name", css_class="col-md-6"),
                    Column("email", css_class="col-md-6"),
                ),
                Row(
                    Column("phone", css_class="col-md-6"),
                    Column("password", css_class="col-md-6"),
                ),
                Row(
                    Column("country", css_class="col-md-6"),
                    Column("city", css_class="col-md-6"),
                ),
                "bio",
                Column("profile_image", css_class="col-md-6"),
            ),
            Fieldset(
                "Informations professionnelles",
                Row(
                    Column("organization", css_class="col-md-6"),
                    Column("verified", css_class="col-md-6"),
                ),
                Row(
                    Column("subscription_paid", css_class="col-md-6"),
                    Column("subscription_date", css_class="col-md-6"),
                ),
                "represented_entrepreneurs",
            ),
            Div(
                Submit("save", "💾 Enregistrer", css_class="btn btn-primary mt-3"),
                css_class="text-end"
            ),
        )

        # Initialiser les champs User avec les valeurs actuelles
        if self.instance and self.instance.user:
            user = self.instance.user
            self.fields["full_name"].initial = user.full_name
            self.fields["email"].initial = user.email
            self.fields["phone"].initial = user.phone
            self.fields["country"].initial = user.country
            self.fields["city"].initial = user.city
            self.fields["profile_image"].initial = user.profile_image
            self.fields["bio"].initial = user.bio

    def save(self, commit=True):
        """Met à jour à la fois l'utilisateur et le profil intermédiaire."""
        profile = super().save(commit=False)
        user = profile.user

        user.full_name = self.cleaned_data.get("full_name")
        user.email = self.cleaned_data.get("email")
        user.phone = self.cleaned_data.get("phone")
        user.country = self.cleaned_data.get("country")
        user.city = self.cleaned_data.get("city")
        user.bio = self.cleaned_data.get("bio")

        if self.cleaned_data.get("profile_image"):
            user.profile_image = self.cleaned_data["profile_image"]

        if self.cleaned_data.get("password"):
            user.set_password(self.cleaned_data["password"])

        if commit:
            user.save()
            profile.user = user
            profile.save()
            # M2M field
            self.save_m2m()
        return profile


class ConfirmIntermediaireDisableAccountForm(forms.Form):
    confirm = forms.BooleanField(
        label="Je confirme vouloir désactiver mon compte.",
        required=True
    )

class ConfirmIntermediaireDeleteAccountForm(forms.Form):
    confirm = forms.BooleanField(
        label="⚠️ Je comprends que cette action est irréversible.",
        required=True
    )