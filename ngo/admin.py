from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from django.urls import reverse,path
from .admin_views import admin_reply_message
from . import admin_views
from .models import (
    User, EntrepreneurProfile, InvestisseurProfile, IntermediaireProfile,
    Country, Category, Project, ProjectPhoto,Notification,
    Campaign, LoanCampaign, Contribution,Payment,
    Reward, Partner, Update, Testimonial,Region,Message,
    ContactMessage, TeamMember,IntermediairePayment,Currency,WithdrawalRequest
)

# --------------------------
# User
# --------------------------
@admin.register(User)
class UserAdmin(BaseUserAdmin):
    # --------------------------
    # Champs affichés dans la liste
    # --------------------------
    list_display = ("profile_preview", "email", "full_name", "role", "city", "country", "is_active", "is_staff")
    list_filter = ("role", "is_active", "is_staff", "country")
    search_fields = ("email", "full_name", "city", "country__name")
    ordering = ("email",)

    # --------------------------
    # Organisation des champs dans les formulaires
    # --------------------------
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (_("Informations personnelles"), {
            "fields": (
                "full_name", "phone", "country", "city",
                "profile_image", "bio", "profile_preview"
            )
        }),
        (_("Rôle et permissions"), {
            "fields": ("role", "is_active", "is_staff", "is_superuser", "groups", "user_permissions")
        }),
        (_("Dates importantes"), {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "full_name", "password1", "password2", "role", "is_active", "is_staff"),
        }),
    )

    readonly_fields = ("last_login", "date_joined", "profile_preview")

    # --------------------------
    # Aperçu de la photo de profil
    # --------------------------
    def profile_preview(self, obj):
        """Affiche une vignette de l'image de profil dans l'admin."""
        if obj.profile_image:
            return format_html(
                '<img src="{}" width="50" height="50" style="border-radius:50%; object-fit:cover;" />',
                obj.profile_image.url
            )
        return "—"
    profile_preview.short_description = "Photo de profil"


# --------------------------
# Profils
# --------------------------
@admin.register(EntrepreneurProfile)
class EntrepreneurProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user_display",
        "company_name",
        "profile_photo",
        "experience_short",
    )
    search_fields = ("user__email", "user__full_name", "company_name")
    list_filter = ("company_name",)
    readonly_fields = ("profile_photo",)

    fieldsets = (
        (_("Informations utilisateur"), {
            "fields": ("user", "profile_photo")
        }),
        (_("Détails de l'entreprise"), {
            "fields": ("company_name", "experience", "image"),
        }),
    )

    def user_display(self, obj):
        return obj.user.display_name()
    user_display.short_description = _("Utilisateur")

    def profile_photo(self, obj):
        if obj.get_avatar_url():
            return format_html(
                '<img src="{}" width="50" height="50" style="border-radius:50%; object-fit:cover;">',
                obj.get_avatar_url(),
            )
        return _("Aucune image")
    profile_photo.short_description = _("Photo")

    def experience_short(self, obj):
        if obj.experience:
            return (obj.experience[:50] + "...") if len(obj.experience) > 50 else obj.experience
        return "-"
    experience_short.short_description = _("Expérience")

    def get_queryset(self, request):
        """Optimisation des requêtes"""
        qs = super().get_queryset(request)
        return qs.select_related("user")


@admin.register(InvestisseurProfile)
class InvestisseurProfileAdmin(admin.ModelAdmin):
    list_display = (
        "get_avatar_preview",
        "get_full_name",
        "company",
        "capital_available",
        "get_email",
        "get_country",
        "get_city",
    )
    list_display_links = ("get_full_name",)
    search_fields = ("user__full_name", "user__email", "company")
    list_filter = ("user__country",)
    ordering = ("user__full_name",)

    fieldsets = (
        ("Informations utilisateur", {
            "fields": ("user", "image", "company", "capital_available")
        }),
    )

    def get_avatar_preview(self, obj):
        """Affiche une mini-photo de profil dans la liste admin."""
        return format_html(
            '<img src="{}" style="width:40px; height:40px; border-radius:50%; object-fit:cover;">',
            obj.get_avatar_url()
        )
    get_avatar_preview.short_description = "Photo"

    def get_email(self, obj):
        return obj.user.email
    get_email.short_description = "Email"

    def get_country(self, obj):
        return obj.user.country or "-"
    get_country.short_description = "Pays"

    def get_city(self, obj):
        return obj.user.city or "-"
    get_city.short_description = "Ville"


@admin.register(IntermediaireProfile)
class IntermediaireProfileAdmin(admin.ModelAdmin):
    list_display = ("user","organization","verified","subscription_paid","subscription_date",)
    list_filter = ("verified", "subscription_paid")
    search_fields = ("user__email", "user__full_name", "organization")
    ordering = ("user__full_name",)


# --------------------------
# Region Admin
# --------------------------
@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "active")
    list_filter = ("active",)
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("name",)

# --------------------------
# Currency Admin
# --------------------------
@admin.register(Currency)
class CurrencyAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "symbol", "exchange_rate_to_usd", "active")
    list_filter = ("active",)
    search_fields = ("code", "name")
    ordering = ("code",)


# --------------------------
# Country
# --------------------------
@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_display = ("name","code","region","currency","project_submission_fee","intermediaire_fee","commission_rate","active",)
    list_filter = ("active", "region", "currency")
    search_fields = ("name", "code")
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("name",)


# --------------------------
# Category
# --------------------------
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "image_preview")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name",)
    list_per_page = 20

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="50" height="50" style="border-radius: 5px; object-fit: cover;" />', obj.image.url)
        return "—"
    image_preview.short_description = "Aperçu"


# --------------------------
# ProjectPhoto Inline
# --------------------------
class ProjectPhotoInline(admin.TabularInline):
    model = ProjectPhoto
    extra = 1


# --------------------------
# Project
# --------------------------
@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("title", "entrepreneur", "country", "target_amount", "collected_amount", "status", "created_at")
    list_filter = ("status", "country", "categories", "created_at")
    search_fields = ("title", "entrepreneur__email", "description")
    autocomplete_fields = ("entrepreneur", "country", "categories")
    readonly_fields = ("slug", "collected_amount", "created_at")
    inlines = [ProjectPhotoInline]

    actions = ["approve_projects", "reject_projects"]

    def approve_projects(self, request, queryset):
        updated = queryset.update(status="approved")
        self.message_user(request, f"{updated} projet(s) approuvé(s) ✅")

    approve_projects.short_description = "✅ Approuver les projets sélectionnés"

    def reject_projects(self, request, queryset):
        updated = queryset.update(status="rejected")
        self.message_user(request, f"{updated} projet(s) rejeté(s) ❌")

    reject_projects.short_description = "❌ Rejeter les projets sélectionnés"

# --------------------------
# Campaign
# --------------------------
class RewardInline(admin.TabularInline):
    model = Reward
    extra = 1


class ContributionInline(admin.TabularInline):
    model = Contribution
    extra = 1
    readonly_fields = ("contributor_name", "amount", "payment_status", "created_at")


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = ("title", "project", "goal_amount", "collected_amount", "status", "start_date", "end_date")
    list_filter = ("status", "start_date", "end_date")
    search_fields = ("title", "project__title")
    inlines = [RewardInline, ContributionInline]
    readonly_fields = ("collected_amount",)
    ordering = ("-start_date",)


# --------------------------
# LoanCampaign
# --------------------------
@admin.register(LoanCampaign)
class LoanCampaignAdmin(admin.ModelAdmin):
    list_display = (
        "title", "project", "goal_amount", "collected_amount",
        "interest_rate", "repayment_duration", "status"
    )
    list_filter = ("status", "start_date", "end_date")
    search_fields = ("title", "project__title")
    inlines = [ContributionInline]
    readonly_fields = ("collected_amount",)


# --------------------------
# Contribution
# --------------------------
@admin.register(Contribution)
class ContributionAdmin(admin.ModelAdmin):
    list_display = (
        "contributor_name", "amount", "contribution_type", "payment_status",
        "campaign", "loan_campaign", "created_at"
    )
    list_filter = ("contribution_type", "payment_status", "created_at")
    search_fields = ("contributor_name", "transaction_id", "campaign__title", "loan_campaign__title")
    readonly_fields = ("created_at",)


# --------------------------
# Partner
# --------------------------
@admin.register(Partner)
class PartnerAdmin(admin.ModelAdmin):
    list_display = ("name", "partner_type", "email", "phone", "active")
    list_filter = ("partner_type", "active")
    search_fields = ("name", "email", "phone")
    prepopulated_fields = {"slug": ("name",)}


# --------------------------
# Update
# --------------------------
@admin.register(Update)
class UpdateAdmin(admin.ModelAdmin):
    list_display = ("title", "campaign", "created_at")
    search_fields = ("title", "campaign__title")
    ordering = ("-created_at",)


# --------------------------
# Testimonial
# --------------------------
@admin.register(Testimonial)
class TestimonialAdmin(admin.ModelAdmin):
    list_display = ("photo_preview", "name", "short_message", "project", "approved", "created_at")
    list_filter = ("approved", "project")
    search_fields = ("name", "message", "project__title")
    ordering = ("-created_at",)
    readonly_fields = ("photo_preview",)

    # --------------------------
    # Aperçu de la photo
    # --------------------------
    def photo_preview(self, obj):
        """Affiche une vignette de la photo dans l'admin."""
        if obj.photo:
            return format_html(
                '<img src="{}" width="60" height="60" style="border-radius:50%; object-fit:cover;" />',
                obj.photo.url
            )
        return "—"
    photo_preview.short_description = "Photo"

    # --------------------------
    # Message raccourci pour la liste
    # --------------------------
    def short_message(self, obj):
        return (obj.message[:60] + "...") if len(obj.message) > 60 else obj.message
    short_message.short_description = "Message"


# --------------------------
# ContactMessage
# --------------------------
@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "subject", "is_read", "created_at")
    list_filter = ("is_read",)
    search_fields = ("name", "email", "subject")
    ordering = ("-created_at",)


# --------------------------
# TeamMember
# --------------------------
@admin.register(TeamMember)
class TeamMemberAdmin(admin.ModelAdmin):
    list_display = ("name", "role", "order")
    list_editable = ("order",)
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("order",)

# --------------------------
# IntermediairePayment Admin
# --------------------------
@admin.register(IntermediairePayment)
class IntermediairePaymentAdmin(admin.ModelAdmin):
    list_display = ("intermediaire", "amount", "currency", "status", "created_at")
    list_filter = ("status", "currency", "created_at")
    search_fields = ("intermediaire__email", "intermediaire__full_name")
    readonly_fields = ("created_at",)
    ordering = ("-created_at",)


# --------------------------
# Paiement
# --------------------------
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("user", "project", "amount", "currency", "payment_type", "payment_method", "is_successful", "created_at")
    list_filter = ("payment_type", "payment_method", "is_successful", "currency")
    search_fields = ("user__email", "user__full_name", "project__title", "transaction_code")
    ordering = ("-created_at",)

# --------------------------
# Message
# --------------------------
@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = (
        'subject',
        'display_sender_avatar',  # ✅ Avatar de l’expéditeur
        'sender',
        'recipient',
        'message_type',
        'is_read',
        'archived',
        'created_at',
        'short_preview',  # ✅ Aperçu du message
    )
    list_filter = (
        'is_read',
        'archived',
        'message_type',
        'created_at',
    )
    search_fields = (
        'subject',
        'body',
        'sender__username',
        'recipient__username',
    )
    ordering = ('-created_at',)

    fieldsets = (
        (_("Informations principales"), {
            'fields': ('sender', 'recipient', 'subject', 'body', 'project', 'message_type')
        }),
        (_("Affichage et état"), {
            'fields': ('sender_avatar', 'preview_text', 'is_read', 'archived')
        }),
        (_("Métadonnées"), {
            'fields': ('created_at',),
        }),
    )
    readonly_fields = ('created_at',)

    # ✅ Méthode : Avatar affiché dans la liste
    def display_sender_avatar(self, obj):
        if obj.get_sender_avatar():
            return format_html('<img src="{}" width="35" height="35" style="border-radius:50%;" />', obj.get_sender_avatar())
        return _("(aucun)")
    display_sender_avatar.short_description = _("Avatar")

    # ✅ Méthode : petit aperçu du contenu
    def short_preview(self, obj):
        return obj.display_preview()
    short_preview.short_description = _("Aperçu")

# --------------------------
# Notification
# --------------------------
@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('title', 'recipient', 'type', 'is_read', 'created_at')
    list_filter = ('type', 'is_read', 'created_at')
    search_fields = ('title', 'message', 'recipient__username')
    readonly_fields = ('created_at', 'read_at')

    # Empêche l’admin de changer le destinataire après création si tu veux
    def get_readonly_fields(self, request, obj=None):
        if obj:  # édition
            return self.readonly_fields + ('recipient',)
        return self.readonly_fields

# -----------------------------------------------
# Demande de Retrait des fonds par l'entrepreneur
# -----------------------------------------------
@admin.register(WithdrawalRequest)
class WithdrawalRequestAdmin(admin.ModelAdmin):
    list_display = ("entrepreneur", "project", "amount", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("entrepreneur__username", "project__title")


# -----------------------------------------------
# Vue pour repondre aux messages
# -----------------------------------------------
