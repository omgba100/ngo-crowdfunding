from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils.text import slugify
from django.utils import timezone
from datetime import timedelta
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.contrib import messages



# --------------------------
# Custom User Manager
# --------------------------
class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("L'adresse e-mail est obligatoire.")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Le superutilisateur doit avoir is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Le superutilisateur doit avoir is_superuser=True.")

        return self.create_user(email, password, **extra_fields)


# --------------------------
# User model
# --------------------------
class User(AbstractUser):
    username = None
    email = models.EmailField(unique=True)

    ROLE_CHOICES = (
        ("entrepreneur", "Entrepreneur"),
        ("investisseur", "Investisseur"),
        ("intermediaire", "Intermédiaire"),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, blank=True, null=True)
    full_name = models.CharField(max_length=150, blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    country = models.ForeignKey("Country", on_delete=models.SET_NULL, null=True, blank=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    profile_image = models.ImageField(upload_to="users/profiles/", blank=True, null=True)
    bio = models.TextField(blank=True, null=True)
    is_deleted = models.BooleanField(default=False, verbose_name=_("Compte désactivé"))
    deleted_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Date de désactivation"))

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    class Meta:
        verbose_name = "Utilisateur"
        verbose_name_plural = "Utilisateurs"
        ordering = ["full_name"]

    def __str__(self):
        role = self.get_role_display() if self.role else "Utilisateur"
        return f"{self.full_name or self.email} ({role})"

    @property
    def is_entrepreneur(self):
        return self.role == "entrepreneur"

    @property
    def is_investisseur(self):
        return self.role == "investisseur"

    @property
    def is_intermediaire(self):
        return self.role == "intermediaire"

    def display_name(self):
        return self.full_name or self.email

    def mark_deleted(self):
        """Désactive le compte et note la date de suppression planifiée"""
        self.is_active = False
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save()

    def delete_permanently(self):
        """Suppression définitive"""
        super(User, self).delete()


# --------------------------
# Profils spécialisés
# --------------------------
class IntermediaireProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Utilisateur"),
        on_delete=models.CASCADE,
        related_name="intermediaire_profile"
    )
    organization = models.CharField(
        _("Organisation"),
        max_length=255,
        blank=True,
        null=True
    )
    verified = models.BooleanField(_("Vérifié"), default=False)
    subscription_paid = models.BooleanField(_("Abonnement payé"), default=False)
    subscription_date = models.DateTimeField(_("Date d'abonnement"), blank=True, null=True)

    represented_entrepreneurs = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        limit_choices_to={'role': 'entrepreneur'},
        related_name='represented_by_intermediaires',
        blank=True,
        verbose_name=_("Entrepreneurs représentés")
    )

    class Meta:
        verbose_name = _("Profil intermédiaire")
        verbose_name_plural = _("Profils intermédiaires")

    def __str__(self):
        return f"{_('Profil intermédiaire de')} {self.user.display_name()}"

    def get_entrepreneurs(self):
        """Retourne les entrepreneurs que cet intermédiaire représente."""
        return self.represented_entrepreneurs.all()

    # 🔹 Ajoute ceci :
    def get_avatar_url(self):
        """
        Retourne la photo du profil de l’intermédiaire, celle de l’utilisateur,
        ou une image par défaut si aucune n’est disponible.
        """
        if self.user.profile_image and hasattr(self.user.profile_image, 'url'):
            return self.user.profile_image.url
        return "/static/assets/img/team/default.png"

    def get_full_name(self):
        """Nom complet ou email de l’intermédiaire."""
        return self.user.full_name or self.user.email


class InvestisseurProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Utilisateur"),
        on_delete=models.CASCADE,
        related_name="investisseur_profile"
    )
    company = models.CharField(
        _("Entreprise"),
        max_length=255,
        blank=True,
        null=True
    )
    capital_available = models.DecimalField(
        _("Capital disponible"),
        max_digits=12,
        decimal_places=2,
        blank=True,
        null=True
    )
    image = models.ImageField(
        upload_to="avatars/investisseurs/",
        blank=True,
        null=True,
        verbose_name=_("Photo de profil")
    )

    class Meta:
        verbose_name = _("Profil investisseur")
        verbose_name_plural = _("Profils investisseurs")

    def __str__(self):
        return f"{_('Profil investisseur de')} {self.user.display_name()}"

    def get_avatar_url(self):
        """
        Retourne la photo du profil investisseur, celle de l’utilisateur,
        ou une image par défaut si aucune n’est disponible.
        """
        if self.image and hasattr(self.image, 'url'):
            return self.image.url
        if self.user.profile_image and hasattr(self.user.profile_image, 'url'):
            return self.user.profile_image.url
        return "/static/assets/img/team/default.png"

    def get_full_name(self):
        """Nom complet ou email de l’utilisateur."""
        return self.user.full_name or self.user.email


class EntrepreneurProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Utilisateur"),
        on_delete=models.CASCADE,
        related_name="entrepreneur_profile"
    )
    company_name = models.CharField(
        _("Nom de l'entreprise"),
        max_length=255,
        blank=True,
        null=True
    )
    experience = models.TextField(
        _("Expérience"),
        blank=True,
        null=True
    )
    image = models.ImageField(
        upload_to="avatars/entrepreneurs/",
        blank=True,
        null=True,
        verbose_name=_("Photo de profil")
    )

    class Meta:
        verbose_name = _("Profil entrepreneur")
        verbose_name_plural = _("Profils entrepreneurs")

    def __str__(self):
        return f"{_('Profil entrepreneur de')} {self.user.display_name()}"

    def get_avatar_url(self):
        """Retourne la photo du profil ou celle de l’utilisateur ou une image par défaut."""
        if self.image:
            return self.image.url
        if self.user.profile_image:
            return self.user.profile_image.url
        return "/static/assets/img/team/default.png"


# --------------------------
# Currency
# --------------------------
class Currency(models.Model):
    code = models.CharField(_("Code"), max_length=10, unique=True)
    name = models.CharField(_("Nom"), max_length=100)
    symbol = models.CharField(_("Symbole"), max_length=10, blank=True, null=True)
    exchange_rate_to_usd = models.DecimalField(_("Taux de change USD"), max_digits=12, decimal_places=4, default=1.0)
    active = models.BooleanField(_("Actif"), default=True)

    class Meta:
        verbose_name = _("Devise")
        verbose_name_plural = _("Devises")
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} ({self.symbol or ''})"


# --------------------------
# Region
# --------------------------
class Region(models.Model):
    name = models.CharField(_("Nom"), max_length=100, unique=True)
    slug = models.SlugField(_("Slug"), unique=True, blank=True)
    active = models.BooleanField(_("Actif"), default=True)

    class Meta:
        verbose_name = _("Région")
        verbose_name_plural = _("Régions")
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


# --------------------------
# Country
# --------------------------
class Country(models.Model):
    region = models.ForeignKey(
        "Region",
        on_delete=models.SET_NULL,
        null=True,
        related_name="countries",
        verbose_name=_("Région")
    )
    name = models.CharField(_("Nom"), max_length=150, unique=True)
    code = models.CharField(_("Code"), max_length=5, unique=True)
    flag = models.ImageField(_("Drapeau"), upload_to="countries/flags/", blank=True, null=True)
    slug = models.SlugField(_("Slug"), unique=True, blank=True)
    active = models.BooleanField(_("Actif"), default=True)
    currency = models.ForeignKey(
        "Currency",
        on_delete=models.PROTECT,
        related_name="countries",
        verbose_name=_("Monnaie")
    )
    project_submission_fee = models.DecimalField(_("Frais de soumission de projet"), max_digits=10, decimal_places=2, default=0)
    intermediaire_fee = models.DecimalField(_("Frais intermédiaire"), max_digits=10, decimal_places=2, default=0)
    commission_rate = models.FloatField(_("Taux de commission"), default=6.9)

    class Meta:
        verbose_name = _("Pays")
        verbose_name_plural = _("Pays")
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.currency.code})"

# --------------------------
# Tarification par region
# --------------------------
class Payment(models.Model):
    PAYMENT_TYPE_CHOICES = (
        ("project_submission", _("Soumission de projet")),
        ("intermediaire_subscription", _("Abonnement intermédiaire")),
    )
    PAYMENT_METHOD_CHOICES = (
        ("mobile_money", _("Mobile Money")),
        ("stripe", _("Stripe")),
        ("paypal", _("PayPal")),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=_("Utilisateur"), on_delete=models.CASCADE)
    project = models.ForeignKey("Project", verbose_name=_("Projet"), on_delete=models.CASCADE, null=True, blank=True)
    amount = models.DecimalField(_("Montant"), max_digits=12, decimal_places=2)
    currency = models.ForeignKey("Currency", verbose_name=_("Monnaie"), on_delete=models.SET_NULL, null=True)
    country = models.ForeignKey("Country", verbose_name=_("Pays"), on_delete=models.SET_NULL, null=True, blank=True)
    payment_type = models.CharField(_("Type de paiement"), max_length=50, choices=PAYMENT_TYPE_CHOICES)
    payment_method = models.CharField(_("Méthode de paiement"), max_length=20, choices=PAYMENT_METHOD_CHOICES)
    transaction_code = models.CharField(_("Code de transaction"), max_length=255, blank=True, null=True)
    proof = models.ImageField(_("Preuve de paiement"), upload_to="payments/proofs/", blank=True, null=True)
    is_successful = models.BooleanField(_("Réussi"), default=False)
    created_at = models.DateTimeField(_("Créé le"), auto_now_add=True)

    class Meta:
        verbose_name = _("Paiement")
        verbose_name_plural = _("Paiements")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.display_name()} - {self.payment_type} ({self.amount} {self.currency.code})"

# --------------------------
# Category
# --------------------------
class Category(models.Model):
    name = models.CharField(_("Nom"), max_length=100, unique=True)
    description = models.TextField(_("Description"), blank=True, null=True)
    image = models.ImageField(_("Image"), upload_to="categories/images/", blank=True, null=True)
    slug = models.SlugField(_("Slug"), unique=True, blank=True)

    class Meta:
        verbose_name = _("Catégorie")
        verbose_name_plural = _("Catégories")
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

# --------------------------
# Project
# --------------------------
class Project(models.Model):
    STATUS_CHOICES = (
        ("pending", _("En attente de validation")),
        ("approved", _("Approuvé")),
        ("rejected", _("Rejeté")),
        ("completed", _("Clôturé")),
    )

    entrepreneur = models.ForeignKey(
        "User",
        verbose_name=_("Entrepreneur"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="projects",
        limit_choices_to={"role": "entrepreneur"},
    )

    title = models.CharField(_("Titre"), max_length=255)
    slug = models.SlugField(_("Slug"), unique=True, blank=True)
    short_description = models.CharField(_("Description courte"), max_length=300, blank=True, null=True)
    description = models.TextField(_("Description"))
    country = models.ForeignKey("Country", verbose_name=_("Pays"), on_delete=models.SET_NULL, null=True, related_name="projects")
    categories = models.ManyToManyField("Category", verbose_name=_("Catégories"), related_name="projects", blank=True)

    target_amount = models.DecimalField(_("Montant cible"), max_digits=12, decimal_places=2)
    collected_amount = models.DecimalField(_("Montant collecté"), max_digits=12, decimal_places=2, default=0)
    status = models.CharField(_("Statut"), max_length=20, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(_("Créé le"), auto_now_add=True)
    deadline = models.DateTimeField(_("Date limite"), null=True, blank=True)
    image = models.ImageField(_("Image"), upload_to="projects/images/", blank=True, null=True)
    submitted_by = models.ForeignKey(
        "User",
        verbose_name=_("Soumis par"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="projects_submitted"
    )

    class Meta:
        verbose_name = _("Projet")
        verbose_name_plural = _("Projets")
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title)
            slug = base_slug
            num = 1
            while Project.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{num}"
                num += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def progress_percentage(self):
        if self.target_amount > 0:
            return round((self.collected_amount / self.target_amount) * 100, 2)
        return 0

    @property
    def total_collected(self):
        crowdfunding_total = sum(c.collected_amount for c in self.campaigns.all())
        loan_total = sum(l.collected_amount for l in self.loan_campaigns.all())
        return crowdfunding_total + loan_total

    def __str__(self):
        return self.title


# --------------------------
# ProjectPhoto
# --------------------------
class ProjectPhoto(models.Model):
    project = models.ForeignKey(
        Project,
        verbose_name=_("Projet"),
        on_delete=models.CASCADE,
        related_name="photos"
    )
    image = models.ImageField(_("Image"), upload_to="projects/photos/")
    caption = models.CharField(_("Légende"), max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(_("Créé le"), auto_now_add=True)

    class Meta:
        verbose_name = _("Photo de projet")
        verbose_name_plural = _("Photos de projet")
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.project.title} - {self.caption or _('Photo')}"


# --------------------------
# Campaign
# --------------------------
class Campaign(models.Model):
    STATUS_CHOICES = (
        ("draft", _("Brouillon")),
        ("active", _("Active")),
        ("paused", _("En pause")),
        ("completed", _("Terminée")),
        ("failed", _("Échouée")),
    )

    project = models.ForeignKey(
        "Project",
        verbose_name=_("Projet"),
        on_delete=models.CASCADE,
        related_name="campaigns"
    )
    created_by = models.ForeignKey(
        "User",
        verbose_name=_("Créé par"),
        on_delete=models.SET_NULL,
        null=True,
        related_name="campaigns_created"
    )

    title = models.CharField(_("Titre"), max_length=255)
    description = models.TextField(_("Description"), blank=True, null=True)
    goal_amount = models.DecimalField(_("Objectif financier"), max_digits=12, decimal_places=2)
    collected_amount = models.DecimalField(_("Montant collecté"), max_digits=12, decimal_places=2, default=0)
    status = models.CharField(_("Statut"), max_length=20, choices=STATUS_CHOICES, default="draft")
    start_date = models.DateTimeField(_("Date de début"), default=timezone.now)
    end_date = models.DateTimeField(_("Date de fin"), blank=True, null=True)
    image = models.ImageField(_("Image"), upload_to="campaigns/images/", blank=True, null=True)
    created_at = models.DateTimeField(_("Créé le"), auto_now_add=True)

    class Meta:
        verbose_name = _("Campagne")
        verbose_name_plural = _("Campagnes")
        ordering = ["-start_date"]

    def __str__(self):
        return f"{_('Campagne')} '{self.title}' {_('pour')} {self.project.title}"

    def progress_percentage(self):
        if self.goal_amount > 0:
            return round((self.collected_amount / self.goal_amount) * 100, 2)
        return 0

    @property
    def remaining_days(self):
        if self.end_date:
            delta = self.end_date - timezone.now()
            return max(delta.days, 0)
        return None

    def is_active(self):
        return self.status == "active" and (not self.end_date or self.end_date > timezone.now())


# --------------------------
# Contribution
# --------------------------
class Contribution(models.Model):
    TYPE_CHOICES = (
        ("donation", _("Don")),
        ("loan", _("Prêt")),
    )

    PAYMENT_METHODS = (
        ("stripe", _("Stripe")),
        ("paypal", _("PayPal")),
        ("mtn", _("MTN Mobile Money")),
        ("orange", _("Orange Mobile Money")),
        ("other", _("Autre")),
    )

    PAYMENT_STATUS = (
        ("pending", _("En attente")),
        ("completed", _("Complété")),
        ("failed", _("Échoué")),
    )

    investor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Investisseur"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="contributions",
        limit_choices_to={"role": "investisseur"},
    )
    campaign = models.ForeignKey(
        "Campaign",
        verbose_name=_("Campagne"),
        on_delete=models.CASCADE,
        related_name="contributions",
        blank=True,
        null=True,
    )
    loan_campaign = models.ForeignKey(
        "LoanCampaign",
        verbose_name=_("Campagne de prêt"),
        on_delete=models.CASCADE,
        related_name="contributions",
        blank=True,
        null=True,
    )

    contributor_name = models.CharField(_("Nom du contributeur"), max_length=150, blank=True, null=True)
    contributor_email = models.EmailField(_("Email du contributeur"), blank=True, null=True)

    amount = models.DecimalField(_("Montant"), max_digits=12, decimal_places=2)
    contribution_type = models.CharField(_("Type de contribution"), max_length=10, choices=TYPE_CHOICES)
    payment_method = models.CharField(_("Méthode de paiement"), max_length=50, choices=PAYMENT_METHODS, default="paypal")
    transaction_id = models.CharField(_("ID de transaction"), max_length=100, blank=True, null=True)
    payment_status = models.CharField(_("Statut du paiement"), max_length=20, choices=PAYMENT_STATUS, default="pending")
    created_at = models.DateTimeField(_("Créé le"), auto_now_add=True)

    class Meta:
        verbose_name = _("Contribution")
        verbose_name_plural = _("Contributions")
        ordering = ["-created_at"]

    def __str__(self):
        name = self.contributor_name or (self.investor.full_name if self.investor else _("Anonyme"))
        campaign_name = self.campaign.title if self.campaign else (self.loan_campaign.title if self.loan_campaign else _("Aucune campagne"))
        return f"{name} - {self.amount} XAF {_('pour')} {campaign_name}"

    def clean(self):
        # Une contribution ne peut pas être liée à la fois à une campagne de don et à une campagne de prêt
        if self.campaign and self.loan_campaign:
            raise ValidationError(_("Une contribution ne peut pas être liée à la fois à une campagne de don et à une campagne de prêt."))
        if not self.campaign and not self.loan_campaign:
            raise ValidationError(_("Une contribution doit être liée à une campagne (don ou prêt)."))
        if self.campaign and self.contribution_type != "donation":
            raise ValidationError(_("Les contributions à une campagne de don doivent avoir le type 'donation'."))
        if self.loan_campaign and self.contribution_type != "loan":
            raise ValidationError(_("Les contributions à une campagne de prêt doivent avoir le type 'loan'."))

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Met à jour les montants collectés automatiquement si paiement complété
        if self.payment_status == "completed":
            if self.campaign:
                total = self.campaign.contributions.filter(payment_status="completed").aggregate(models.Sum("amount"))["amount__sum"] or 0
                self.campaign.collected_amount = total
                self.campaign.save()
            elif self.loan_campaign:
                total = self.loan_campaign.contributions.filter(payment_status="completed").aggregate(models.Sum("amount"))["amount__sum"] or 0
                self.loan_campaign.collected_amount = total
                self.loan_campaign.save()

    @property
    def is_paid(self):
        return self.payment_status == "completed"

    # 🔹 Récupère le projet parent (don ou prêt)
    @property
    def project(self):
        if self.campaign:
            return self.campaign.project  # Assure-toi que Campaign a un ForeignKey vers Project
        if self.loan_campaign:
            return self.loan_campaign.project  # Assure-toi que LoanCampaign a un ForeignKey vers Project
        return None

    # 🔹 Pourcentage de contribution par rapport au projet
    @property
    def percentage_of_project(self):
        project = self.project
        if project and project.target_amount > 0:
            return round((self.amount / project.target_amount) * 100, 2)
        return 0

    # 🔹 Nom affiché à l'entrepreneur (sécurisé)
    @property
    def investor_name(self):
        return self.investor.full_name if self.investor and self.investor.full_name else _("Anonyme")

# --------------------------
# LoanCampaign
# --------------------------
class LoanCampaign(models.Model):
    STATUS_CHOICES = (
        ("draft", _("Brouillon")),
        ("active", _("Active")),
        ("paused", _("En pause")),
        ("completed", _("Terminée")),
        ("failed", _("Échouée")),
    )

    project = models.ForeignKey(
        "Project",
        verbose_name=_("Projet"),
        on_delete=models.CASCADE,
        related_name="loan_campaigns"
    )
    created_by = models.ForeignKey(
        "User",
        verbose_name=_("Créé par"),
        on_delete=models.SET_NULL,
        null=True,
        related_name="loan_campaigns_created"
    )
    title = models.CharField(_("Titre"), max_length=255)
    description = models.TextField(_("Description"), blank=True, null=True)
    goal_amount = models.DecimalField(_("Montant cible"), max_digits=12, decimal_places=2)
    collected_amount = models.DecimalField(_("Montant collecté"), max_digits=12, decimal_places=2, default=0)
    interest_rate = models.DecimalField(_("Taux d'intérêt (%)"), max_digits=5, decimal_places=2, default=0.0)
    repayment_duration = models.PositiveIntegerField(_("Durée de remboursement (mois)"), help_text=_("Durée du remboursement en mois"))
    status = models.CharField(_("Statut"), max_length=20, choices=STATUS_CHOICES, default="draft")
    start_date = models.DateTimeField(_("Date de début"), default=timezone.now)
    end_date = models.DateTimeField(_("Date de fin"), blank=True, null=True)
    image = models.ImageField(_("Image"), upload_to="loan_campaigns/images/", blank=True, null=True)
    created_at = models.DateTimeField(_("Créé le"), auto_now_add=True)

    class Meta:
        verbose_name = _("Campagne de prêt")
        verbose_name_plural = _("Campagnes de prêt")
        ordering = ["-start_date"]

    def __str__(self):
        return f"{_('Prêt')} '{self.title}' ({self.project.title})"

    def progress_percentage(self):
        if self.goal_amount > 0:
            return round((self.collected_amount / self.goal_amount) * 100, 2)
        return 0

    @property
    def total_interest(self):
        return (self.goal_amount * self.interest_rate / 100)

    @property
    def remaining_days(self):
        if self.end_date:
            delta = self.end_date - timezone.now()
            return max(delta.days, 0)
        return None

    def is_active(self):
        return self.status == "active" and (not self.end_date or self.end_date > timezone.now())

# --------------------------
# Partner
# --------------------------
class Partner(models.Model):
    PARTNER_TYPE_CHOICES = (
        ("ngo", _("ONG / Association")),
        ("company", _("Entreprise privée")),
        ("gov", _("Institution publique")),
        ("individual", _("Partenaire individuel")),
        ("other", _("Autre")),
    )

    name = models.CharField(_("Nom"), max_length=255, unique=True)
    slug = models.SlugField(_("Slug"), unique=True, blank=True)
    partner_type = models.CharField(_("Type de partenaire"), max_length=50, choices=PARTNER_TYPE_CHOICES, default="other")
    logo = models.ImageField(_("Logo"), upload_to="partners/logos/", blank=True, null=True)
    website = models.URLField(_("Site web"), blank=True, null=True)
    email = models.EmailField(_("Email"), blank=True, null=True)
    phone = models.CharField(_("Téléphone"), max_length=50, blank=True, null=True)
    description = models.TextField(_("Description"), blank=True)
    active = models.BooleanField(_("Actif"), default=True)
    created_at = models.DateTimeField(_("Créé le"), auto_now_add=True)

    class Meta:
        verbose_name = _("Partenaire")
        verbose_name_plural = _("Partenaires")
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


# --------------------------
# Update
# --------------------------
class Update(models.Model):
    campaign = models.ForeignKey(
        "Campaign",
        verbose_name=_("Campagne"),
        on_delete=models.CASCADE,
        related_name="updates"
    )
    title = models.CharField(_("Titre"), max_length=255)
    content = models.TextField(_("Contenu"))
    image = models.ImageField(_("Image"), upload_to="updates/images/", blank=True, null=True)
    created_at = models.DateTimeField(_("Créé le"), auto_now_add=True)

    class Meta:
        verbose_name = _("Mise à jour")
        verbose_name_plural = _("Mises à jour")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{_('Mise à jour')} {self.title} - {self.campaign.title}"


# --------------------------
# Testimonial
# --------------------------
class Testimonial(models.Model):
    name = models.CharField(_("Nom"), max_length=150)
    photo = models.ImageField(
        _("Photo"),
        upload_to="testimonials/photos/",
        blank=True,
        null=True,
        help_text=_("Photo du contributeur ou de la personne donnant le témoignage")
    )
    message = models.TextField(_("Message"))
    project = models.ForeignKey(
        "Project",
        verbose_name=_("Projet"),
        on_delete=models.CASCADE,
        related_name="testimonials",
        blank=True,
        null=True
    )
    approved = models.BooleanField(_("Approuvé"), default=False)
    created_at = models.DateTimeField(_("Créé le"), auto_now_add=True)

    class Meta:
        verbose_name = _("Témoignage")
        verbose_name_plural = _("Témoignages")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{_('Témoignage de')} {self.name}"

# --------------------------
# Reward
# --------------------------
class Reward(models.Model):
    campaign = models.ForeignKey(
        "Campaign",
        verbose_name=_("Campagne"),
        on_delete=models.CASCADE,
        related_name="rewards"
    )
    title = models.CharField(_("Titre"), max_length=255)
    description = models.TextField(_("Description"))
    minimum_amount = models.DecimalField(_("Montant minimum"), max_digits=10, decimal_places=2)
    image = models.ImageField(
        _("Image"),
        upload_to="rewards/images/",
        blank=True,
        null=True,
        help_text=_("Image représentative de la récompense (facultative)")
    )

    class Meta:
        verbose_name = _("Récompense")
        verbose_name_plural = _("Récompenses")
        ordering = ["minimum_amount"]

    def __str__(self):
        return f"{self.title} ({self.minimum_amount} XAF {_('min')})"

    def is_eligible(self, amount):
        """Vérifie si un montant donné donne droit à cette récompense"""
        return amount >= self.minimum_amount


# --------------------------
# ContactMessage
# --------------------------
class ContactMessage(models.Model):
    name = models.CharField(_("Nom"), max_length=150)
    email = models.EmailField(_("Email"))
    subject = models.CharField(_("Sujet"), max_length=200)
    message = models.TextField(_("Message"))
    is_read = models.BooleanField(_("Lu"), default=False)
    created_at = models.DateTimeField(_("Créé le"), auto_now_add=True)

    class Meta:
        verbose_name = _("Message de contact")
        verbose_name_plural = _("Messages de contact")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{_('Message de')} {self.name} - {self.subject}"


# --------------------------
# TeamMember
# --------------------------
class TeamMember(models.Model):
    name = models.CharField(_("Nom"), max_length=150)
    slug = models.SlugField(_("Slug"), unique=True, blank=True)
    role = models.CharField(_("Rôle"), max_length=150)
    bio = models.TextField(_("Biographie"), blank=True, null=True)
    photo = models.ImageField(_("Photo"), upload_to="team/photos/", blank=True, null=True)
    email = models.EmailField(_("Email"), blank=True, null=True)
    linkedin = models.URLField(_("LinkedIn"), blank=True, null=True)
    twitter = models.URLField(_("Twitter"), blank=True, null=True)
    facebook = models.URLField(_("Facebook"), blank=True, null=True)
    order = models.PositiveIntegerField(_("Ordre"), default=0)

    class Meta:
        ordering = ["order", "name"]
        verbose_name = _("Membre de l'équipe")
        verbose_name_plural = _("Membres de l'équipe")

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} - {self.role}"

# ---------------------------------------
# Modele de paiement pour l'intermediaire
# ---------------------------------------
class IntermediairePayment(models.Model):
    STATUS_CHOICES = (
        ("pending", _("En attente")),
        ("validated", _("Validé")),
    )

    intermediaire = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Intermédiaire"),
        on_delete=models.CASCADE,
        related_name="intermediaire_payments"
    )
    amount = models.DecimalField(_("Montant"), max_digits=12, decimal_places=2)
    currency = models.ForeignKey(
        "Currency",
        verbose_name=_("Devise"),
        on_delete=models.SET_NULL,
        null=True
    )
    proof = models.ImageField(
        _("Preuve"),
        upload_to="intermediaire/payments/",
        blank=True,
        null=True
    )
    status = models.CharField(
        _("Statut"),
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending"
    )
    created_at = models.DateTimeField(_("Créé le"), auto_now_add=True)

    class Meta:
        verbose_name = _("Paiement intermédiaire")
        verbose_name_plural = _("Paiements intermédiaires")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.intermediaire.display_name()} - {self.amount} {self.currency.code} ({_(self.status)})"

# --------------------------
# Message
# --------------------------
class Message(models.Model):
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='sent_messages',
        on_delete=models.CASCADE,
        verbose_name=_("Expéditeur")
    )
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='received_messages',
        on_delete=models.CASCADE,
        verbose_name=_("Destinataire")
    )
    subject = models.CharField(
        max_length=200,
        verbose_name=_("Objet")
    )
    body = models.TextField(
        verbose_name=_("Contenu")
    )
    project = models.ForeignKey(
        'Project',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        verbose_name=_("Projet associé")
    )

    # ✅ Nouveaux champs enrichis
    sender_avatar = models.ImageField(
        upload_to='avatars/messages/',
        null=True,
        blank=True,
        verbose_name=_("Avatar de l’expéditeur"),
        help_text=_("Image affichée dans la liste de messages.")
    )

    preview_text = models.CharField(
        max_length=120,
        blank=True,
        verbose_name=_("Aperçu"),
        help_text=_("Texte court pour aperçu dans les notifications.")
    )

    message_type = models.CharField(
        max_length=30,
        choices=[
            ('message', _("Message")),
            ('notification', _("Notification")),
            ('update', _("Mise à jour")),
        ],
        default='message',
        verbose_name=_("Type de message")
    )

    is_read = models.BooleanField(default=False, verbose_name=_("Lu"))
    archived = models.BooleanField(default=False, verbose_name=_("Archivé"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Date de création"))

    class Meta:
        verbose_name = _("Message")
        verbose_name_plural = _("Messages")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.subject} - {self.sender} → {self.recipient}"

    # ✅ Raccourci pour le temps écoulé
    def time_since(self):
        return timesince(self.created_at, timezone.now())

    # ✅ Raccourci pour un texte de notification stylé
    def display_preview(self):
        if self.preview_text:
            return self.preview_text
        return (self.body[:100] + "...") if len(self.body) > 100 else self.body

    # ✅ Pour récupérer la photo (même si l’utilisateur n’en a pas)
    def get_sender_avatar(self):
        if self.sender_avatar:
            return self.sender_avatar.url
        if hasattr(self.sender, "profile") and getattr(self.sender.profile, "avatar", None):
            return self.sender.profile.avatar.url
        return "/static/assets/img/team/default.png"


# --------------------------------------
# Notification (globale et intelligente)
# --------------------------------------
class Notification(models.Model):
    # ---------------------
    # Types possibles
    # ---------------------
    NOTIFICATION_TYPES = (
        ("project_validated", _("Projet validé")),
        ("project_rejected", _("Projet rejeté")),
        ("project_update", _("Mise à jour du projet")),
        ("new_comment", _("Nouveau commentaire")),
        ("campaign_contribution", _("Nouvelle contribution")),
        ("campaign_goal_reached", _("Objectif de campagne atteint")),
        ("campaign_update", _("Nouvelle mise à jour de campagne")),
        ("loan_contribution", _("Nouvelle contribution à un prêt")),
        ("loan_repayment", _("Remboursement reçu")),
        ("loan_completed", _("Campagne de prêt terminée")),
        ("intermediary_submission", _("Soumission par un intermédiaire")),
        ("payment_validated", _("Paiement validé")),
        ("payment_failed", _("Paiement échoué")),
        ("reward_earned", _("Récompense débloquée")),
        ("admin_message", _("Message administratif")),
        ("general", _("Notification générale")),
    )

    # ---------------------
    # Relations principales
    # ---------------------
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
        verbose_name=_("Destinataire")
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sent_notifications",
        verbose_name=_("Expéditeur")
    )

    # ---------------------
    # Contenu de la notification
    # ---------------------
    type = models.CharField(
        max_length=50,
        choices=NOTIFICATION_TYPES,
        default="general",
        verbose_name=_("Type de notification")
    )
    title = models.CharField(_("Titre"), max_length=255)
    message = models.TextField(_("Message"))
    short_message = models.CharField(
        _("Résumé"), max_length=255, blank=True,
        help_text=_("Texte court pour dropdown / notification nav")
    )
    icon = models.CharField(
        _("Icône"), max_length=50, blank=True,
        help_text=_("Nom d'icône (ex: bell, calendar, settings)")
    )
    bg_color = models.CharField(
        _("Couleur de fond icône"), max_length=50, blank=True,
        default="bg-dark", help_text=_("Ex: bg-success, bg-danger, bg-warning")
    )

    # ---------------------
    # Liens contextuels
    # ---------------------
    related_project = models.ForeignKey(
        "Project", null=True, blank=True, on_delete=models.SET_NULL,
        verbose_name=_("Projet lié")
    )
    related_campaign = models.ForeignKey(
        "Campaign", null=True, blank=True, on_delete=models.SET_NULL,
        verbose_name=_("Campagne liée")
    )
    related_loan = models.ForeignKey(
        "LoanCampaign", null=True, blank=True, on_delete=models.SET_NULL,
        verbose_name=_("Campagne de prêt liée")
    )
    related_reward = models.ForeignKey(
        "Reward", null=True, blank=True, on_delete=models.SET_NULL,
        verbose_name=_("Récompense liée")
    )
    related_update = models.ForeignKey(
        "Update", null=True, blank=True, on_delete=models.SET_NULL,
        verbose_name=_("Mise à jour liée")
    )
    related_contribution = models.ForeignKey(
        "Contribution", null=True, blank=True, on_delete=models.SET_NULL,
        verbose_name=_("Contribution liée")
    )

    # ---------------------
    # Statut & métadonnées
    # ---------------------
    is_read = models.BooleanField(default=False, verbose_name=_("Lue"))
    is_important = models.BooleanField(default=False, verbose_name=_("Importante"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Date de création"))
    read_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Date de lecture"))

    class Meta:
        verbose_name = _("Notification")
        verbose_name_plural = _("Notifications")
        ordering = ["-created_at"]

    def __str__(self):
        name = getattr(self.recipient, "display_name", None)
        return f"{self.title} → {name or self.recipient.username or 'Utilisateur'}"

    # ---------------------
    # Méthodes utilitaires
    # ---------------------
    def mark_as_read(self):
        """Marque la notification comme lue."""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=["is_read", "read_at"])

    def get_link(self):
        """Retourne un lien vers l’objet lié."""
        for related in [
            self.related_project,
            self.related_campaign,
            self.related_loan,
            self.related_contribution,
            self.related_update,
            self.related_reward,
        ]:
            if related and hasattr(related, "get_absolute_url"):
                return related.get_absolute_url()
        return "#"

    @classmethod
    def send(cls, recipient, title, message, sender=None, type="general",
             icon="bell", bg_color="bg-dark", short_message="", is_important=False, **relations):
        """
        Envoie une notification à un utilisateur avec icône et couleur pour dropdown.
        """
        return cls.objects.create(
            recipient=recipient,
            sender=sender,
            type=type,
            title=title,
            short_message=short_message or message[:50],
            message=message,
            icon=icon,
            bg_color=bg_color,
            is_important=is_important,
            **relations
        )



# -----------------------------------------------
# Demande de Retrait des fonds par l'entrepreneur
# -----------------------------------------------
class WithdrawalRequest(models.Model):
    STATUS_CHOICES = (
        ("pending", _("En attente")),
        ("approved", _("Approuvée")),
        ("rejected", _("Rejetée")),
        ("paid", _("Payée")),
    )

    entrepreneur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="withdrawal_requests",
        verbose_name=_("Entrepreneur")
    )
    project = models.ForeignKey(
        "Project",
        on_delete=models.CASCADE,
        related_name="withdrawal_requests",
        verbose_name=_("Projet concerné")
    )
    amount = models.DecimalField(_("Montant demandé"), max_digits=12, decimal_places=2)
    reason = models.TextField(_("Motif du retrait"), blank=True, null=True)
    status = models.CharField(_("Statut"), max_length=20, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(_("Date de demande"), auto_now_add=True)
    processed_at = models.DateTimeField(_("Date de traitement"), blank=True, null=True)

    class Meta:
        verbose_name = _("Demande de retrait")
        verbose_name_plural = _("Demandes de retrait")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.entrepreneur} - {self.project.title} ({self.amount} FCFA)"

    def is_editable(self):
        return self.status == "pending"