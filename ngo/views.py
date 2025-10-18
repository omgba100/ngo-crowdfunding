from django.shortcuts import render,redirect, get_object_or_404
from django.contrib.auth import views as auth_views
import os
from django.conf import settings
from django.contrib.auth.views import PasswordResetView
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.core.mail import send_mail
from django.http import HttpResponse,JsonResponse
from django.utils import timezone
from django.utils.timesince import timesince
from django.db.models import Sum, Count, Q
from django.urls import reverse_lazy
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.contrib.auth import authenticate, login
from django.utils.translation import get_language, gettext as _

import logging
logger = logging.getLogger(__name__)

User = get_user_model()

# forms
from .forms import (ContactForm,BaseRegisterForm,EntrepreneurRegisterForm,InvestisseurRegisterForm,
                    IntermediaireRegisterForm,CustomLoginForm,ProjectForm,ProjectPaymentForm,
                    IntermediairePaymentForm,UniversalPasswordResetForm,MessageForm,WithdrawalRequestForm,
                    EntrepreneurProfileForm,InvestisseurProfileForm,IntermediaireProfileForm,
                    ConfirmIntermediaireDisableAccountForm,ConfirmIntermediaireDeleteAccountForm)
 
# models
from .models import (User,EntrepreneurProfile,InvestisseurProfile,IntermediaireProfile,Message,Notification,
                     Currency,Region,Country,Payment,Category,Project,ProjectPhoto,Campaign,Contribution,
                     Partner,Update,Testimonial,Reward,LoanCampaign,ContactMessage,TeamMember,IntermediairePayment,
                     WithdrawalRequest)

# ---------------------------
# Home / Accueil
# ---------------------------
def home(request):
    projects = Project.objects.filter(status="approved")[:6]
    campaigns = Campaign.objects.filter(status="active")[:6]
    categories = Category.objects.all().order_by("name")[:6]
    partners = Partner.objects.filter(active=True)
    team = TeamMember.objects.all().order_by("order")[:6]
    testimonials = Testimonial.objects.filter(approved=True).order_by("-created_at")[:6]

    context ={
        "projects": projects,
        "campaigns": campaigns,
        "categories": categories,
        "partners": partners,
        "team": team,
        "testimonials": testimonials,
    }

    return render(request, "ngo/index.html", context)


# ---------------------------
# Categorie
# ---------------------------
def category_list(request):
    """Affiche la liste de toutes les catégories."""
    categories = Category.objects.all().order_by("name")
    return render(request, "ngo/categorie/categorie_list.html", {"categories": categories})


def category_detail(request, slug):
    category = get_object_or_404(Category, slug=slug)

    # Tous les pays qui ont au moins un projet dans cette catégorie
    country = Country.objects.filter(
        projects__categories=category,
        active=True
    ).distinct().first()  # prendre un pays par défaut (ou None si pas de projets)

    # Tous les projets de cette catégorie
    projects = Project.objects.filter(
        categories=category,
        status__in=["approved", "completed"],
        collected_amount__gt=0
    )

    return render(request, "ngo/categorie/categorie_detail.html", {
        "category": category,
        "country": country,
        "projects": projects,
    })


# ---------------------------
# Liste des projets
# ---------------------------
def project_list(request):
    projects = Project.objects.filter(status="approved").select_related("country").prefetch_related("categories")

    country_slug = request.GET.get("country")
    category_slug = request.GET.get("category")

    if country_slug:
        projects = projects.filter(country__slug=country_slug)
    if category_slug:
        projects = projects.filter(categories__slug=category_slug)

    countries = Country.objects.filter(active=True)
    categories = Category.objects.all()

    context={
        'projects':projects,
        'countries': countries,
        'categories': categories,
        'selected_country': country_slug,
        'selected_category':category_slug,
    }

    return render(request, "ngo/projet/project_list.html", context)

# ---------------------------
# Détail d’un projet
# --------------------------- 
def project_detail(request, slug):
    project = get_object_or_404(Project, slug=slug, status="approved")
    return render(request, "ngo/projet/project_detail.html", {"project": project})


# ---------------------------
# Campaigns
# ---------------------------
def campaign_list(request):
    """
    Affiche la liste de toutes les campagnes actives (don participatif) 
    avec le pourcentage de fonds collectés pour chaque campagne.
    """
    campaigns = Campaign.objects.filter(
        status="active",
        end_date__gt=timezone.now()
    ).order_by("-start_date")

    # Calculer le pourcentage pour chaque campagne
    for c in campaigns:
        if c.goal_amount > 0:
            c.progress_percent = round(c.collected_amount / c.goal_amount * 100, 2)
        else:
            c.progress_percent = 0

    context = {
        "campaigns": campaigns,
    }
    return render(request, "ngo/campaign/campaign_list.html", context)


def campaign_detail(request, pk):
    campaign = get_object_or_404(Campaign, pk=pk)

    contributions = campaign.contributions.filter(payment_status="completed")

    # Pourcentage collecté
    if campaign.goal_amount > 0:
        campaign.progress_percent = round(campaign.collected_amount / campaign.goal_amount * 100, 2)
    else:
        campaign.progress_percent = 0

    # ✅ Ne pas toucher à campaign.remaining_days ici
    # Django la calcule automatiquement via @property

    context = {
        "campaign": campaign,
        "contributions": contributions,
    }

    return render(request, "ngo/campaign/campaign_detail.html", context)



# -------------------
# Liste des LoanCampaigns
# -------------------
def loan_campaign_list(request):
    """
    Affiche la liste de toutes les campagnes de prêt actives
    avec le pourcentage collecté et les jours restants.
    """
    campaigns = LoanCampaign.objects.filter(
        status="active",
        end_date__gt=timezone.now()
    ).order_by("-start_date")

    campaigns_data = []
    for c in campaigns:
        # Pourcentage collecté
        progress_percent = round(c.collected_amount / c.goal_amount * 100, 2) if c.goal_amount > 0 else 0

        # Jours restants
        remaining_days = (c.end_date - timezone.now()).days if c.end_date else None
        if remaining_days is not None:
            remaining_days = max(remaining_days, 0)

        campaigns_data.append({
            "campaign": c,
            "progress_percent": progress_percent,
            "remaining_days": remaining_days,
        })

    context = {
        "campaigns_data": campaigns_data,
    }
    return render(request, "ngo/loan/loan_campaign_list.html", context)


def loan_campaign_detail(request, pk):
    # Récupération de la campagne de prêt
    loan_campaign = get_object_or_404(LoanCampaign, pk=pk)

    # Récupérer les contributions complétées
    contributions = loan_campaign.contributions.filter(payment_status="completed")

    # Calcul du pourcentage collecté
    progress_percent = 0
    if loan_campaign.goal_amount > 0:
        progress_percent = round((loan_campaign.collected_amount / loan_campaign.goal_amount) * 100, 2)

    # Calcul des jours restants
    remaining_days = None
    if loan_campaign.end_date:
        remaining_days = max((loan_campaign.end_date - timezone.now()).days, 0)

    context = {
        "loan_campaign": loan_campaign,
        "contributions": contributions,
        "progress_percent": progress_percent,
        "remaining_days": remaining_days,
    }

    return render(request, "ngo/loan/loan_campaign_detail.html", context)



# ---------------------------
# Contributions (liste simple - pas de compte utilisateur)
# ---------------------------
def contribution_list(request, campaign_id):
    campaign = get_object_or_404(Campaign, pk=campaign_id)
    contributions = campaign.contributions.filter(payment_status="completed")
    return render(request, "ngo/contribution/contribution_list.html", {
        "campaign": campaign,
        "contributions": contributions,
    })


# ---------------------------
# Countries (liste des pays d’intervention)
# ---------------------------
def country_list(request):
    countries = Country.objects.filter(active=True).order_by("name")
    return render(request, "ngo/country/country_list.html", {"countries": countries})

def country_detail(request, slug):
    """Affiche les détails d’un pays."""
    country = get_object_or_404(Country, slug=slug, active=True)
    return render(request, "ngo/country/country_detail.html", {"country": country})

# -------------------------------------------------
# catégories de projets financés dans un pays donné
# -------------------------------------------------
def funded_categories_for_country(request, country_slug):
    # Récupérer le pays
    country = get_object_or_404(Country, slug=country_slug, active=True)

    # Filtrer les catégories liées à des projets financés dans ce pays
    categories = Category.objects.filter(
        projects__country=country,
        projects__status__in=["approved", "completed"],
        projects__collected_amount__gt=0
    ).annotate(
        total_collected=Sum('projects__collected_amount')
    ).distinct()

    context = {
        "country": country,
        "categories": categories,
    }

    return render(request, "ngo/country/funded_categories.html", context)

# -------------------------------------------------------
# projets financés dans une catégorie donnée pour ce pays
# ------------------------------------------------------
def projects_by_category(request, country_slug, category_slug):
    country = get_object_or_404(Country, slug=country_slug, active=True)
    category = get_object_or_404(Category, slug=category_slug)

    projects = Project.objects.filter(
        country=country,
        category=category,
        status__in=["approved", "completed"],
        collected_amount__gt=0
    ).annotate(
        funding_percentage=100 * (Sum("collected_amount") / Sum("target_amount"))
    )

    context = {
        "country": country,
        "category": category,
        "projects": projects,
    }
    return render(request, "ngo/country/projects_by_category.html", context)

# ---------------------------
# Partners
# ---------------------------
def partner_list(request):
    partners = Partner.objects.filter(active=True)
    return render(request, "ngo/partner/partner_list.html", {"partners": partners})


# ---------------------------
# Team
# ---------------------------
def team_list(request):
    team = TeamMember.objects.all().order_by("order")
    return render(request, "ngo/team/team_list.html", {"team": team})


# ---------------------------
# Testimonials
# ---------------------------
def testimonial_list(request):
    testimonials = Testimonial.objects.all().order_by("-created_at")
    return render(request, "ngo/testimonial/testimonial_list.html", {"testimonials": testimonials})


# ---------------------------
# Contact (formulaire simple - pas encore avec Form Django)
# ---------------------------
def contact(request):
    form = ContactForm(request.POST or None)
    success = False
    if request.method == "POST":
        if form.is_valid():
            form.save()
            messages.success(request, "Merci ! Votre message a été envoyé avec succès.")
            success = True
            form = ContactForm()
    return render(request, "ngo/contact/contact.html", {"form": form, "success": success})

# ---------------------------
# About-us
# ---------------------------
def about_us(request):
    return render(request, "ngo/info/about_us.html")

# ---------------------------
# Que faisons nous
# ---------------------------

def que_faisons_nous(request):
    steps = [
        {"title": _("Dépôt du dossier de projet"), 
         "actors": _("Porteur de projet"), 
         "desc": _("Soumission du projet avec business plan, besoin de financement et pièces administratives."), 
         "image": "assets/img/etude/steps/depot.jpg"},
        {"title": _("Étude de recevabilité"), 
         "actors": _("Cabinet d’accompagnement"), 
         "desc": _("Analyse de la complétude et cohérence du dossier avant instruction."), 
         "image": "assets/img/etude/steps/recevabilite.jpeg"},
        {"title": _("Analyse technique et économique"), 
         "actors": _("Experts IGIA"), 
         "desc": _("Étude du modèle économique et de la faisabilité du projet."), 
         "image": "assets/img/etude/steps/analyse.jpg"},
        {"title": _("Contrôle de conformité légale"), 
         "actors": _("Cabinet juridique"), 
         "desc": _("Vérification de la conformité réglementaire et administrative."), 
         "image": "assets/img/etude/steps/legal.jpg"},
        {"title": _("Validation financière"), 
         "actors": _("Comité financier"), 
         "desc": _("Évaluation financière et recommandation du mode de financement."), 
         "image": "assets/img/etude/steps/financier.jpg"},
        {"title": _("Comité d’agrément"), 
         "actors": _("Comité d’investissement"), 
         "desc": _("Décision finale sur le financement du projet."), 
         "image": "assets/img/etude/steps/agrement.jpg"},
        {"title": _("Mise en ligne sur IGIA"), 
         "actors": _("Équipe IT & Com"), 
         "desc": _("Publication du projet sur la plateforme pour levée de fonds."), 
         "image": "assets/img/etude/steps/mise_en_ligne.jpg"},
        {"title": _("Suivi post-validation"), 
         "actors": _("Cabinet de suivi"), 
         "desc": _("Accompagnement et évaluation trimestrielle du projet."), 
         "image": "assets/img/etude/steps/suivi.jpg"},
    ]

    domaines = [
        {"title": _("Entrepreneuriat & Innovation"), 
         "subtitle": _("Soutenir les jeunes et startups à fort potentiel."), 
         "image": "assets/img/etude/domains/entrepreneurship.jpg", 
         "points": [_("Financement de startups"), _("Incubation de projets"), _("Création de TPE/PME"), _("Innovation sociale")]},
        {"title": _("Agriculture & Développement rural"), 
         "subtitle": _("Appuyer la sécurité alimentaire et l’économie verte."), 
         "image": "assets/img/etude/domains/agriculture.jpg", 
         "points": [_("Agriculture durable"), _("Élevage et pisciculture"), _("Transformation agroalimentaire")]},
        {"title": _("Technologie & Numérique"), 
         "subtitle": _("Encourager l’innovation technologique."), 
         "image": "assets/img/etude/domains/tech.jpg", 
         "points": [_("Startups tech"), _("Solutions fintech"), _("Cybersécurité"), _("E-learning")]},
        {"title": _("Éducation & Emploi"), 
         "subtitle": _("Former et insérer les jeunes."), 
         "image": "assets/img/etude/domains/education.jpg", 
         "points": [_("Formation professionnelle"), _("Éducation financière"), _("Mentorat")]},
        {"title": _("Énergie & Environnement"), 
         "subtitle": _("Favoriser la transition écologique."), 
         "image": "assets/img/etude/domains/energy.jpg", 
         "points": [_("Énergies renouvelables"), _("Recyclage"), _("Reboisement")]},
        {"title": _("Santé & Bien-être"), 
         "subtitle": _("Promouvoir l’accès équitable à la santé."), 
         "image": "assets/img/etude/domains/health.jpg", 
         "points": [_("Centres communautaires"), _("Télé-médecine"), _("Nutrition")]},
        {"title": _("Transport & Petits Métiers"), 
         "subtitle": _("Soutenir les acteurs du quotidien et les petits entrepreneurs."), 
         "image": "assets/img/etude/domains/transport.jpg", 
         "points": [_("Moto-taxi, taxi, transport local"), _("Call-box et salons de coiffure"), _("Bars, cafés et petits commerces"), _("Artisanat et ateliers mécaniques")]},
    ]

    return render(request, 'ngo/info/what_we_do.html', {'steps': steps, 'domaines': domaines})

# ---------------------------
# Agrement securite
# ---------------------------
def agrement_securite(request):
    sections = [
        {"title": _("Plateforme agréée DNB"),
         "desc": _("IGIA est enregistrée auprès des autorités financières et agréée par l’Autorité des Marchés Financiers."),
         "image": "assets/img/lever/agrement.png"},
        {"title": _("Label Croissance Verte"),
         "desc": _("IGIA est reconnue pour son engagement envers la durabilité et la transparence des financements."),
         "image": "assets/img/lever/ABN-AMRO.png"},
        {"title": _("Confiance et transparence"),
         "desc": _("Nous veillons à ce que chaque projet respecte les exigences éthiques et environnementales."),
         "image": "assets/img/lever/dok.png"},
    ]

    securite_points = [
        {"title": _("Environnement sécurisé"),
         "desc": _("L’ensemble du site IGIA est protégé par le protocole HTTPS pour garantir la sécurité des échanges.")},
        {"title": _("Transactions sécurisées"),
         "desc": _("Les opérations sont gérées via des protocoles de paiement semi-automatiques pour éviter tout risque de fraude.")},
        {"title": _("Accès crypté"),
         "desc": _("Votre mot de passe reste confidentiel et vos données ne sont jamais partagées avec des tiers.")},
        {"title": _("Protection des transactions"),
         "desc": _("Nos partenaires bancaires et opérateurs assurent la continuité et la sécurité des opérations même en cas d’incident.")},
    ]

    return render(request, 'ngo/info/agrement_securite.html', {
        'sections': sections,
        'securite_points': securite_points,
    })

# ---------------------------
# Financement inclusif
# ---------------------------
def financement_igia(request):
    """
    Vue combinée : Financement participatif et inclusif IGIA.
    """

    # -----------------------
    # Contenu 1 : financement participatif
    # -----------------------
    types_financement = [
        {
            "title": _("Financement Corporate / Bridge / Mezzanine"),
            "desc": _(
                "IGIA structure des financements participatifs allant jusqu'à 10 M€, "
                "en associant notre plateforme et nos partenaires financiers. "
                "Nous adaptons les solutions corporate, bridge ou mezzanine selon le stade de développement des projets."
            ),
            "image": "assets/img/lever/corporate.jpg",
        },
        {
            "title": _("Financements à vocation territoriale"),
            "desc": _(
                "IGIA favorise l’adhésion des citoyens dès la phase de développement des projets. "
                "Nous proposons des modalités sur-mesure et une communication spécifique pour les territoires et riverains."
            ),
            "image": "assets/img/lever/territorial.jpg",
        },
        {
            "title": _("Financements liés aux AO / AMI"),
            "desc": _(
                "Pour les appels d’offres nationaux et territoriaux, IGIA accompagne les projets afin d’optimiser leur sélection "
                "grâce à l’expertise en financement participatif et à la structuration de dossiers complets."
            ),
            "image": "assets/img/lever/ami.png",
        },
    ]

    accompagnement = [
        _("Analyse financière complète du projet"),
        _("Rédaction et vérification de la documentation contractuelle"),
        _("Présentation du projet à notre communauté d'investisseurs"),
        _("Communication adaptée avant, pendant et après la collecte"),
        _("Suivi des souscriptions et clôture de l’opération"),
        _("Suivi des transactions et reporting aux investisseurs"),
    ]

    tarifs = [
        _("IGIA ne prélève aucun frais aux investisseurs."),
        _("Pour chaque levée de fonds réussie, un pourcentage compris entre 2 %% et 6 %% du montant collecté est facturé au porteur de projet."),
        _("Frais de mise en ligne détaillés par devis selon le projet."),
        _("Frais de communication éventuels, également détaillés par devis."),
    ]

    realisations = [
        {
            "title": _("Opérations à enjeu local"),
            "desc": _(
                "IGIA associe les citoyens et riverains au financement des projets, créant une appropriation locale et "
                "favorisant le développement territorial. "
                "Nous atteignons jusqu'à 100%% des objectifs de collecte grâce aux investisseurs locaux."
            ),
            "image": "assets/img/lever/local.jpg",
        },
        {
            "title": _("Opérations d’envergure jusqu’à 10 M€"),
            "desc": _(
                "Avec notre communauté d’investisseurs et nos partenaires financiers, IGIA structure des financements jusqu'à 10 M€. "
                "Nous accompagnons chaque projet dans la structuration, la documentation contractuelle et la visibilité de l’opération."
            ),
            "image": "assets/img/lever/envergure.jpg",
        },
    ]

    # -----------------------
    # Contenu 2 : financement inclusif
    # -----------------------
    models = [
        {
            "title": _("Financement d’Amorçage Solidaire"),
            "desc": _(
                "Ce modèle s’adresse aux porteurs d’idées ou micro-projets à fort impact local. "
                "Il permet de recevoir un micro-capital (0 à 2 000 €) grâce à des dons ou micro-investissements, "
                "débloqués progressivement selon l’avancement du projet. "
                "L’entrepreneur bénéficie d’un accompagnement obligatoire par un mentor IGIA."
            ),
            "image": "assets/img/lever/seed.jpg",
        },
        {
            "title": _("Financement Communautaire Garanti"),
            "desc": _(
                "Le porteur de projet mobilise son entourage ou sa communauté (amis, famille, diaspora) "
                "pour garantir symboliquement son projet. "
                "Une fois un seuil atteint, IGIA ou un partenaire complète le montant restant. "
                "C’est un modèle de solidarité encadrée, où la réussite du projet profite à tous."
            ),
            "image": "assets/img/lever/community.png",
        },
        {
            "title": _("Financement par Mise à Disposition d’Actif"),
            "desc": _(
                "IGIA ou un investisseur achète un bien productif (voiture, moto, fauteuil, matériel). "
                "Le bénéficiaire l’utilise via une location avec option d’achat ou un micro-crédit souple. "
                "Les revenus générés servent à rembourser l’actif, menant à une autonomie complète en 12 à 36 mois."
            ),
            "image": "assets/img/lever/asset.png",
        },
        {
            "title": _("Financement par Tiers de Confiance"),
            "desc": _(
                "IGIA collabore avec des intermédiaires locaux agréés (ONG, incubateurs, coopératives). "
                "Ces partenaires reçoivent les fonds et accompagnent les porteurs de projets sur le terrain. "
                "Ce modèle réduit les risques et garantit un suivi éthique et durable."
            ),
            "image": "assets/img/lever/trusted.png",
        },
    ]

    avantages = [
        {"title": _("Accessibilité"), "desc": _("Ouvert à tous les porteurs d’idées, même sans capital initial.")},
        {"title": _("Encadrement"), "desc": _("Chaque bénéficiaire est accompagné par un mentor ou un partenaire agréé.")},
        {"title": _("Transparence"), "desc": _("Les fonds sont débloqués étape par étape, selon les résultats concrets.")},
        {"title": _("Autonomisation"), "desc": _("Les modèles visent à créer de véritables propriétaires et entrepreneurs.")},
    ]

    # -----------------------
    # Devise IGIA
    # -----------------------
    devise = _(
        "IGIA combine mobilisation collective et financement solidaire (Crowdlending) et "
        "financement participatif (Crowdfunding) pour que chaque idée, qu’elle vienne d’un entrepreneur "
        "avec ou sans capital, ait une chance de devenir réalité."
    )

    return render(request, 'ngo/info/financement_igia.html', {
        'types_financement': types_financement,
        'accompagnement': accompagnement,
        'tarifs': tarifs,
        'realisations': realisations,
        'models': models,
        'avantages': avantages,
        'devise': devise,
    })

# ---------------------------
# Guide d'utilisation
# ---------------------------
def guide_utilisation(request):
    # Données pour chaque profil
    profiles = [
        {
            "role": _("Entrepreneur"),
            "steps": [
                _("Connectez-vous au Dashboard."),
                _("Cliquez sur 'Créer un projet'."),
                _("Remplissez le formulaire : titre, description, montant, durée, type de financement (crowdfunding/crowdlending), contreparties."),
                _("Acquittez-vous des frais de soumission."),
                _("Après approbation, votre projet sera visible sur la plateforme.")
            ],
            "note": [
                _("Facilités de paiement disponibles selon votre région et votre pays de résidence."),
                _("Crowdfunding : contrepartie ou produit."),
                _("Crowdlending : remboursement avec intérêts.")
            ],
            "warnings": [
                _("Projets visibles uniquement après validation : tous les projets doivent être soumis et validés par IGIA avant de pouvoir recevoir des fonds."),
                _("Recevoir des fonds directement d’investisseurs en dehors de la plateforme peut entraîner la suspension du projet et l'exclusion définitive."),
                _("La plateforme ne pourra pas gérer les remboursements ni calculer les intérêts si c’est fait en dehors du site.")
            ] 
        },
        {
            "role": _("Investisseur"),
            "steps": [
                _("Connectez-vous au Dashboard."),
                _("Cliquez sur 'Explorer les projets'."),
                _("Filtrez selon vos critères : montant minimal, type de financement, durée, secteur."),
                _("Consultez la page détaillée : taux, durée, montant minimum, risques, modalités de remboursement."),
                _("Cliquez sur 'Investir maintenant', choisissez le montant et confirmez le paiement.")
            ],
            "note": [
                _("Crowdfunding : soutien et contrepartie."),
                _("Crowdlending : prêt avec intérêts.")
            ],
            "warnings": [
                _("Toujours passer par la plateforme IGIA : les investissements doivent être effectués via le site."),
                _("Ne jamais verser directement de l’argent à l’entrepreneur sans passer par la plateforme.")
            ],
            "reason": [
                _("Sécurisation des transactions."),
                _("Suivi des remboursements et intérêts dans le cadre du crowdlending."),
                _("Garantie de conformité aux conditions de financement.")
            ]
        },
        {
            "role": _("Intermédiaire"),
            "steps": [
                _("Connectez-vous au Dashboard."),
                _("Cliquez sur 'Mes Intermédiaires'."),
                _("Ajoutez les projets que vous représentez et les entrepreneurs que vous accompagnez."),
                _("Soumettez les projets pour le compte de l’entrepreneur si nécessaire."),
                _("Suivez l’avancement des investissements et recevez vos commissions automatiquement.")
            ],
            "note": [
                _("Facilite la collecte de fonds et simplifie le processus pour les entrepreneurs et investisseurs.")
            ],
            "warnings": [
                _("Respect strict du processus IGIA : les intermédiaires ne doivent pas contourner la plateforme."),
                _("Toutes les transactions doivent passer par IGIA."),
                _("Les commissions sont calculées uniquement sur les investissements effectués via la plateforme.")
            ]
        }
    ]

    # Sécurité et prévention des scams
    security = {
        "title": _("Protection contre les emails frauduleux"),
        "message": [
            _("Tous les emails officiels IGIA proviennent du domaine @igia.com."),
            _("Tout email venant d’une adresse différente doit être considéré comme suspect."),
            _("IGIA ne demande jamais de transférer de l’argent en dehors de la plateforme ni vos identifiants de compte par email."),
            _("Suivant chaque région et pays IGIA ne fait des transactions qu'avec ses partenaires agréés et ses partenaires sont communiqués lors des paiements."),
            _("Vérifiez toujours le Dashboard IGIA pour confirmer toute demande d’investissement ou transaction."),
            _("Ne transférez jamais d’argent ni ne communiquez vos identifiants en dehors de la plateforme."),
            _("Ne cliquez jamais sur des liens ou téléchargez des fichiers provenant de sources inconnues."),
            _("En cas de suspicion, signalez immédiatement l'email à contact@igia.com."),
            _("Vérifiez toujours votre Dashboard IGIA avant de confirmer toute transaction.")
        ]
    }

    contact_info = {
        "email": "contact@igia.com",
        "phone": "01.82.83.97.52"
    }

    return render(request, "ngo/info/guide_utilisation.html", {
        "profiles": profiles,
        "contact_info": contact_info,
        "security": security
    })

# ---------------------------
# Mention Legale
# ---------------------------
def mentions_legales(request):
    """Page des mentions légales IGIA avec gestion des risques internationaux"""

    categories = [
        "politique",
        "economique",
        "infrastructures",
        "social",
        "environnement",
        "gouvernance",
    ]

    context = {
        "company": {
            "name": "Infinity Global Investment & Aid (IGIA) NV",
            "capital": "300 000 000 €",
            "siren": "805 178 860",
            "tva": "NE09805178860",
            "ape": "7022Z",
            "address": "94 rue de la Victoria, 75009 Utrecht, Pays-Bas",
            "email": "contact@igia.com",
            "phone": "+33 1 82 83 97 52",
            "director": "Amaury Blais",
            "amf_number": "PSFP 2012-22",
        },
        "bank": {
            "name": "ABN AMRO BANK NV",
            "address": "Gustav Mahlerlaan 10, 1082 PP Amsterdam, Pays-Bas",
            "email": "customercare@be.abnamro.com",
            "rcs": "500 486 915",
            "agrement": "ACPR du 1 avril 2018",
        },
        "host": {
            "name": "Heroku, Inc.",
            "address": "650 7th Street, San Francisco, CA 94103",
            "contact_url": "https://www.heroku.com/contact",
            "security_url": "https://www.heroku.com/policy/security",
        },
        "risks": [
            {"type": _("Politique & Juridique"), "solutions": _("Assurances MIGA, arbitrage international, partenaires certifiés.")},
            {"type": _("Économique & Monétaire"), "solutions": _("Couverture de change, diversification, devises fortes.")},
            {"type": _("Infrastructures & Logistique"), "solutions": _("Plan logistique, zones viabilisées, technologie verte.")},
            {"type": _("Social & Culturel"), "solutions": _("Dialogue communautaire, emploi local, RSE.")},
            {"type": _("Environnement & Climat"), "solutions": _("Études d’impact, technologies durables, plans de résilience.")},
            {"type": _("Gouvernance & Transparence"), "solutions": _("Audit externe, suivi digital IGIA, normes ISO 37001.")},
        ],
        "categories": categories,
    }

    return render(request, "ngo/info/mentions_legales.html", context)

# ---------------------------
# Confidentialite
# ---------------------------
def confidentialite(request):
    """Page de politique de confidentialité IGIA"""
    
    context = {
        "sections": [
            {
                "title": _("1. Protection des données personnelles"),
                "content": _(
                    "IGIA respecte la législation en matière de protection des données (loi Informatique et Libertés du 6 janvier 1978). "
                    "Le site est déclaré auprès du Department of Constitutional Affairs and Legislation (DCAL) sous le numéro 1807840. "
                    "Les données collectées ne sont jamais utilisées à des fins publicitaires. "
                    "Les utilisateurs disposent de droits d’accès, de rectification et d’opposition (articles 26, 34 à 38 et 36). "
                    "Ces droits peuvent être exercés via le compte IGIA ou à l’adresse : contact@igia.com."
                ),
            },
            {
                "title": _("2. Sécurité et confidentialité des comptes"),
                "content": _(
                    "IGIA ne demandera jamais de mot de passe par téléphone ou e-mail. "
                    "L’utilisateur doit se déconnecter après chaque session, en particulier sur un poste partagé. "
                    "Les informations relatives aux projets financiers sont strictement confidentielles et ne doivent pas être divulguées. "
                    "L’utilisateur s’engage à ne pas les utiliser à d’autres fins que l’étude des projets."
                ),
            },
            {
                "title": _("3. Politique de cookies"),
                "content": _(
                    "Le site IGIA utilise des cookies pour améliorer la navigation et collecter des statistiques d’utilisation. "
                    "Les cookies ne contiennent aucune donnée personnelle et servent uniquement à identifier plus rapidement l’utilisateur. "
                    "L’utilisateur peut désactiver les cookies via les paramètres de son navigateur, mais cela peut altérer certaines fonctionnalités."
                ),
            },
        ],
        "contact_email": "contact@igia.com",
    }

    return render(request, "ngo/info/confidentialite.html", context)

# ---------------------------
# Reclamation
# ---------------------------
def reclamations(request):
    """Page de gestion des réclamations IGIA conformément au règlement européen"""

    context = {
        "contact": {
            "email": "reclamation@igia.com",
            "address": "94 rue de la Victoire, 75009 Paris",
            "phone": "+33 1 82 83 97 52",
        },
        "procedure": [
            {
                "title": _("Dépôt d’une réclamation"),
                "details": _(
                    "La réclamation peut être envoyée par email, courrier ou via le modèle PDF disponible sur le site. "
                    "IGIA accuse réception sous 10 jours ouvrables."
                ),
            },
            {
                "title": _("Examen et traitement"),
                "details": _(
                    "IGIA évalue la clarté, la complétude et la recevabilité de la réclamation. "
                    "Des informations complémentaires peuvent être demandées pour un traitement optimal."
                ),
            },
            {
                "title": _("Décision et communication"),
                "details": _(
                    "Une réponse motivée est adressée dans un délai maximum de 30 jours ouvrés. "
                    "Toute décision inclut les voies de recours possibles."
                ),
            },
            {
                "title": _("Médiation"),
                "details": _(
                    "En cas de désaccord, le réclamant peut saisir le Médiateur WTW : "
                    "formulaire en ligne sur wtwco.com, téléphone +31 (0) 88 541 3000, "
                    "ou courrier à l’Autorité des marchés financiers d’Amsterdam."
                ),
            },
        ],
        "mediator": {
            "name": "WTW Médiation",
            "website": "https://www.wtwco.com/fr-fr/about-us/office-locations",
            "phone": "+31 (0) 88 541 3000",
            "address": "Autorité des marchés financiers – Médiation, Prof. E.M. Meijerslaan 5, Amstelveen 1183 AV, Amsterdam",
        },
    }

    return render(request, "ngo/info/reclamations.html", context)

# --------------------------------
# Condition generale d'utilisation
# --------------------------------
def conditions_generales_utilisation(request):
    """
    Page complète des Conditions Générales d’Utilisation (CGU) du site IGIA.
    Inclut le contenu textuel du document juridique stocké dans /static/docs/cgu_igia_LANG.txt
    et les informations de l’entreprise.
    """

    # Langue active
    lang = get_language()  # ex: "fr", "en", "es","nl"
    filename = f"cgu_igia_{lang}.txt"
    cgu_path = os.path.join(settings.BASE_DIR, "ngo", "static", "docs", filename)

    # Lecture sécurisée du fichier CGU traduit
    try:
        with open(cgu_path, "r", encoding="utf-8") as f:
            cgu_text = f.read()
    except FileNotFoundError:
        # Message alternatif si le fichier n’existe pas pour la langue donnée
        cgu_text = _(
            "Le document officiel des Conditions Générales d’Utilisation est temporairement "
            "indisponible dans votre langue. Veuillez réessayer ultérieurement ou contacter "
            "notre support à contact@igia.com."
        )

    # Informations sur l’entreprise IGIA
    company = {
        "name": "Infinity Global Investment & Aid (IGIA)",
        "address": "94 rue de la Victoria, 75009 Utrecht, Pays-Bas",
        "email": "contact@igia.com",
        "phone": "+33 1 82 83 97 52",
        "siren": "KVB 805 168 860",
        "tva": "NE 09805178860",
        "capital": "300 000 000 €",
        "rcs": "RCS de Utrecht",
        "psfp": "n°2012-22 (AMF)",
    }

    # Contexte transmis au template
    context = {
        "title": _("Conditions Générales d’Utilisation"),
        "meta_description": _(
            "Découvrez les conditions générales d'utilisation de la plateforme IGIA : sécurité, "
            "transparence et conformité AMF."
        ),
        "company": company,
        "cgu_text": cgu_text,
        "last_update": _("Applicables depuis le 9 novembre 2023"),
        "hero": {
            "title": _("Conditions Générales d’Utilisation"),
            "subtitle": _("Sécurité, transparence et responsabilité pour chaque investisseur IGIA."),
            "background": "assets/img/about/hero-bg.jpg",
        },
    }

    return render(request, "ngo/info/conditions_generales_utilisation.html", context)

# --------------------------------
# Donnees personelles
# --------------------------------
def donnees_personnelles(request):
    """
    Page Politique de Protection des Données Personnelles (RGPD).
    Le contenu est chargé dynamiquement selon la langue active (FR, EN, etc.).
    """

    # 🔹 Langue active
    lang = get_language()  # Exemple : "fr", "en"
    filename = f"donnees_personnelles_{lang}.txt"
    file_path = os.path.join(settings.BASE_DIR, "ngo", "static", "docs/donner", filename)

    # 🔹 Lecture du texte RGPD
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            rgpd_text = f.read()
    except FileNotFoundError:
        rgpd_text = _(
            "La politique de protection des données personnelles est temporairement indisponible. "
            "Veuillez réessayer plus tard ou contacter notre équipe à contact@igia.com."
        )

    # 🔹 Contexte envoyé au template
    context = {
        "title": _("Politique de protection des données personnelles"),
        "meta_description": _(
            "Découvrez comment IGIA protège vos données personnelles conformément au RGPD."
        ),
        "rgpd_text": rgpd_text,
        "last_update": _("Dernière mise à jour : 9 novembre 2023"),
        "hero": {
            "title": _("Données personnelles"),
            "subtitle": _("Sécurité, transparence et confidentialité de vos informations avec IGIA."),
            "background": "assets/img/about/hero-bg.jpg",
        },
    }

    return render(request, "ngo/info/donnees_personnelles.html", context)

# --------------------------------
# Actualite
# --------------------------------
def actualite_list(request):
    """
    Page des actualités IGIA.
    Contenu entièrement statique dans le template.
    """
    context = {
        "title": _("Actualités IGIA"),
        "meta_description": _("Restez informé des dernières actualités et projets d'IGIA."),
    }
    return render(request, "ngo/info/actualite.html", context)

# --------------------------------
# Message
# --------------------------------

# --------------------------
# Fonctions utilitaires
# --------------------------
def get_role_inbox_template(role):
    """
    Retourne le chemin du template inbox selon le rôle utilisateur.
    """
    return f"ngo/dashboard/messages/{role}/inbox.html"

def get_role_detail_template(role):
    """
    Retourne le template du détail du message selon le rôle.
    """
    return f"ngo/dashboard/messages/{role}/message_detail.html"

def get_role_send_template(role):
    """
    Retourne le template d'envoi de message selon le rôle.
    """
    return f"ngo/dashboard/messages/{role}/send_message.html"

# --------------------------
# Inbox par rôle
# --------------------------
@login_required
def inbox_entrepreneur(request):
    user = request.user

    # 📬 Messages de l'entrepreneur
    messages_qs = Message.objects.filter(recipient=user).order_by('-created_at')

    # 🕒 Préparation des données pour le template
    for msg in messages_qs:
        msg.time_since = timesince(msg.created_at)
        msg.sender_image = (
            msg.sender.profile_image.url
            if hasattr(msg.sender, "profile_image") and msg.sender.profile_image
            else "/static/assets/img/team/default.png"
        )
        msg.sender_name = msg.sender.full_name or msg.sender.email

    form = MessageForm()

    # 🧑‍💼 Avatar et nom de l’entrepreneur connecté
    if hasattr(user, "entrepreneur_profile"):
        profile = user.entrepreneur_profile
        user_profile_image = profile.get_avatar_url()
    else:
        user_profile_image = user.profile_image.url if user.profile_image else "/static/assets/img/team/default.png"
    user_full_name = user.full_name or user.email

    context = {
        'messages': messages_qs,
        'role': 'entrepreneur',
        'form': form,
        'user_profile_image': user_profile_image,
        'user_full_name': user_full_name,
    }

    return render(request, get_role_inbox_template('entrepreneur'), context)

@login_required
def inbox_investisseur(request):
    user = request.user

    # 📬 Messages reçus par l’investisseur
    messages_qs = Message.objects.filter(recipient=user).order_by('-created_at')

    # 🕒 Ajout des infos complémentaires pour chaque message
    for msg in messages_qs:
        msg.time_since = timesince(msg.created_at)
        msg.sender_image = (
            msg.sender.profile_image.url
            if hasattr(msg.sender, "profile_image") and msg.sender.profile_image
            else "/static/assets/img/team/default.png"
        )
        msg.sender_name = msg.sender.full_name or msg.sender.email

    # 📨 Formulaire de nouveau message (pour le bouton "Nouveau message")
    form = MessageForm(sender=user)

    # 👤 Avatar et nom de l’investisseur connecté
    if hasattr(user, "investisseur_profile"):
        profile = user.investisseur_profile
        user_profile_image = profile.get_avatar_url()
    else:
        user_profile_image = (
            user.profile_image.url
            if hasattr(user, "profile_image") and user.profile_image
            else "/static/assets/img/team/default.png"
        )
    user_full_name = user.full_name or user.email

    # 📝 Préparer un formulaire reply pour chaque message
    reply_forms = {msg.pk: MessageForm(sender=user) for msg in messages_qs}

    context = {
        'messages': messages_qs,
        'role': 'investisseur',
        'form': form,
        'reply_forms': reply_forms,
        'user_profile_image': user_profile_image,
        'user_full_name': user_full_name,
    }

    return render(request, get_role_inbox_template('investisseur'), context)


@login_required
def inbox_intermediaire(request):
    # Profil de l’intermédiaire
    profile = get_object_or_404(IntermediaireProfile, user=request.user)

    # 🔹 Informations profil
    full_name = profile.get_full_name()
    avatar = profile.get_avatar_url()

    # Messages reçus
    messages_list = Message.objects.filter(recipient=request.user).order_by('-created_at')

    context = {
        'messages': messages_list,
        'role': 'intermediaire',
        'profile': profile,
        'full_name': full_name,  # ✅ nom complet
        'avatar': avatar,        # ✅ photo de profil
    }

    return render(request, get_role_inbox_template('intermediaire'), context)


# --------------------------
# Lecture d'un message
# --------------------------
@login_required
def message_detail(request, message_id):
    message = get_object_or_404(Message, id=message_id, recipient=request.user)
    if not message.is_read:
        message.is_read = True
        message.save()

    role = request.user.role
    context = {'message': message, 'role': role}
    return render(request, get_role_detail_template(role), context)


# --------------------------
# Envoi d'un message
# --------------------------
@login_required
def send_message(request):
    """Vue unifiée d’envoi de message selon le rôle utilisateur."""
    user = request.user
    role = getattr(user, 'role', None)

    if request.method == "POST":
        # ✅ on injecte le sender dans le formulaire
        form = MessageForm(request.POST, sender=user)
        if form.is_valid():
            msg = form.save(commit=False)
            msg.sender = user

            # ✅ on définit le destinataire comme l’admin
            admin_user = User.objects.filter(is_superuser=True).first()
            msg.recipient = admin_user

            msg.save()

            messages.success(request, "Message envoyé avec succès.")

            # ✅ Redirection selon le rôle
            if role == 'entrepreneur':
                return redirect('inbox_entrepreneur')
            elif role == 'investisseur':
                return redirect('inbox_investisseur')
            elif role == 'intermediaire':
                return redirect('inbox_intermediaire')
            else:
                return redirect('inbox')

        # ⚠️ Si formulaire invalide
        else:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'errors': form.errors})
            messages.error(request, "Veuillez corriger les erreurs dans le formulaire.")

    else:
        form = MessageForm(sender=user)

    # ✅ Support du chargement AJAX ou normal
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'success': True})

    return render(request, get_role_send_template(role), {'form': form, 'role': role})


# --------------------------
# Répondre à un message
# --------------------------
@login_required
def reply_message(request, pk):
    """Permet de répondre à un message reçu (AJAX only)."""
    original_msg = get_object_or_404(Message, pk=pk, recipient=request.user)

    if request.method == "POST":
        # ✅ On passe l’expéditeur pour appliquer les restrictions du rôle
        form = MessageForm(request.POST, sender=request.user)
        if form.is_valid():
            reply = form.save(commit=False)

            # ✅ Sécurisation des champs automatiques
            reply.sender = request.user
            reply.recipient = original_msg.sender
            reply.subject = f"RE: {original_msg.subject}"

            # ✅ Si le message original est lié à un projet, on le conserve
            if original_msg.project and not reply.project:
                reply.project = original_msg.project

            reply.save()

            return JsonResponse({'success': True, 'message': str(_("Message envoyé avec succès."))})
        else:
            return JsonResponse({
                'success': False,
                'errors': form.errors,
                'message': str(_("Veuillez corriger les erreurs du formulaire."))
            })

    # ❌ On bloque toute tentative GET
    return JsonResponse({'success': False, 'error': str(_("Méthode GET non supportée."))})

# --------------------------
# Archiver / Supprimer
# --------------------------
@login_required
def archive_message(request, pk):
    msg = get_object_or_404(Message, pk=pk, recipient=request.user)
    msg.archived = True
    msg.save()
    return JsonResponse({'success': True})

@login_required
def delete_message(request, pk):
    msg = get_object_or_404(Message, pk=pk, recipient=request.user)
    msg.delete()
    return JsonResponse({'success': True})

# -----------------------------------
# Liste des projets de l'entrepreneur
# -----------------------------------
@login_required
def entrepreneur_project_list(request):
    """
    Vue privée affichant les projets de l'entrepreneur connecté (max 5).
    - Accès réservé aux entrepreneurs et intermédiaires.
    - Filtrage par statut possible.
    - Message si la limite de 5 projets est atteinte.
    - Compatible i18n via gettext (_)
    """
    user = request.user
    max_projects = 5
    current_lang = get_language()  # 🌐 Récupération de la langue active

    # ✅ Vérification du rôle autorisé
    if not getattr(user, "is_entrepreneur", False) and not getattr(user, "is_intermediaire", False):
        messages.error(
            request,
            _("⛔ Accès refusé : cette page est réservée aux entrepreneurs et intermédiaires.")
        )
        return redirect("home")

    # 🧭 Filtrage de base selon le rôle
    if getattr(user, "is_intermediaire", False):
        all_projects = Project.objects.filter(submitted_by=user).order_by("-created_at")
    else:
        all_projects = Project.objects.filter(entrepreneur=user).order_by("-created_at")

    # 🔍 Filtrage optionnel par statut
    status_filter = request.GET.get("status")
    if status_filter and status_filter != "all":
        all_projects = all_projects.filter(status=status_filter)

    # ⚠️ Limite stricte à 5 projets
    projects = all_projects[:max_projects]
    total_projects = all_projects.count()

    if total_projects >= max_projects:
        messages.warning(
            request,
            _("⚠️ Vous avez atteint la limite maximale de 5 projets. "
              "Veuillez en supprimer un avant d’en créer un nouveau.")
        )

    # 📊 Comptage global par statut
    status_counts = (
        Project.objects.filter(
            submitted_by=user if getattr(user, "is_intermediaire", False) else user
        )
        .values("status")
        .annotate(total=Count("id"))
    )
    counts_dict = {item["status"]: item["total"] for item in status_counts}

    STATUS_CHOICES = [
        ("all", _("Tous les statuts")),
        ("pending_payment", _("En attente de paiement")),
        ("pending_review", _("En cours de révision")),
        ("approved", _("Validé")),
        ("rejected", _("Rejeté")),
        ("completed", _("Terminé")),
    ]

    # 🧑‍💼 Avatar et nom de l’entrepreneur connecté
    if hasattr(user, "entrepreneur_profile"):
        profile = user.entrepreneur_profile
        user_profile_image = profile.get_avatar_url()
    else:
        user_profile_image = user.profile_image.url if user.profile_image else "/static/assets/img/team/default.png"

    user_full_name = user.full_name or user.email

    context = {
        "projects": projects,
        "status_filter": status_filter or "all",
        "status_choices": STATUS_CHOICES,
        "counts": counts_dict,
        "total_projects": total_projects,
        "max_projects": max_projects,
        "current_lang": current_lang,
        "title": _("Mes Projets (max 5)"),
        "user_profile_image": user_profile_image,
        "user_full_name": user_full_name,
    }

    return render(
        request,
        "ngo/dashboard/entrepreneur/pages/projet/project_list.html",
        context,
    )

# ---------------------------
# Créer un projet (Entrepreneur uniquement)
# ---------------------------
@login_required
def project_create(request):
    user = request.user

    if not (user.is_entrepreneur or user.is_intermediaire):
        messages.error(request, "Seuls les entrepreneurs ou intermédiaires validés peuvent créer un projet.")
        return redirect("home")

    # 🔍 Vérifie que l'utilisateur a un pays
    if not user.country:
        messages.error(request, "Veuillez définir votre pays dans votre profil avant de soumettre un projet.")
        return redirect("dashboard_entrepreneur")

    country = user.country
    fee = country.project_submission_fee
    currency = country.currency.code

    if request.method == "POST":
        form = ProjectForm(request.POST, request.FILES)
        payment_form = ProjectPaymentForm(request.POST, request.FILES)

        # 🔑 Valide les deux formulaires
        if form.is_valid() and payment_form.is_valid():
            project = form.save(commit=False)

            # ✅ Si c'est un intermédiaire, il doit choisir l'entrepreneur bénéficiaire
            if user.is_intermediaire:
                entrepreneur_id = request.POST.get("entrepreneur_id")
                if not entrepreneur_id:
                    messages.error(request, "Veuillez sélectionner l'entrepreneur bénéficiaire.")
                    return render(
                        request,
                        "ngo/dashboard/entrepreneur/pages/projet/project_create_form.html",
                        {"form": form, "payment_form": payment_form, "fee": fee, "currency": currency}
                    )
                project.entrepreneur = get_object_or_404(User, pk=entrepreneur_id, role="entrepreneur")
            else:
                project.entrepreneur = user  # entrepreneur soumet pour lui-même

            project.submitted_by = user
            project.country = country
            project.status = "pending_payment"
            project.save()
            form.save_m2m()

            # Création du paiement lié
            payment = payment_form.save(commit=False)
            payment.user = user
            payment.project = project
            payment.amount = fee
            payment.currency = currency
            payment.payment_type = "project_submission"
            payment.is_successful = False  # à valider par l'admin
            payment.save()

            messages.success(
                request,
                f"Projet soumis avec succès 💡 (Frais à payer : {fee} {currency}). Veuillez soumettre la preuve de paiement."
            )
            return redirect("project_payment_verify", project_slug=project.slug)
    else:
        form = ProjectForm()
        payment_form = ProjectPaymentForm()

    # 🧑‍💼 Avatar et nom de l’entrepreneur connecté
    if hasattr(user, "entrepreneur_profile"):
        profile = user.entrepreneur_profile
        user_profile_image = profile.get_avatar_url()
    else:
        user_profile_image = user.profile_image.url if user.profile_image else "/static/assets/img/team/default.png"

    user_full_name = user.full_name or user.email

    context = {
        "form": form,
        "payment_form": payment_form,
        "fee": fee,
        "currency": currency,
        "title": "Créer un Projet",
        "user_profile_image": user_profile_image,
        "user_full_name": user_full_name,
    }

    return render(
        request,
        "ngo/dashboard/entrepreneur/pages/projet/project_create_form.html",
        context
    )


# ---------------------------
# Modifier un projet
# ---------------------------
@login_required
def project_update(request, slug):
    project = get_object_or_404(Project, slug=slug, entrepreneur=request.user)

    if request.method == "POST":
        form = ProjectForm(request.POST, request.FILES, instance=project)
        if form.is_valid():
            form.save()

            # ✅ Envoi d'une notification à l'admin (ou superuser)
            admin_users = User.objects.filter(is_staff=True)
            for admin in admin_users:
                Notification.objects.create(
                    recipient=admin,
                    sender=request.user,
                    type="project_updated",
                    title="🔄 Projet mis à jour",
                    message=f"L'entrepreneur {request.user.full_name or request.user.email} "
                            f"a mis à jour le projet « {project.title} ». ",
                    related_project=project
                )

            # ✅ Message de succès utilisateur
            messages.success(request, "Projet mis à jour avec succès ✅")
            return redirect("dashboard_entrepreneur")
    else:
        form = ProjectForm(instance=project)

    # 🧑‍💼 Avatar et nom de l’entrepreneur connecté
    user = request.user
    if hasattr(user, "entrepreneur_profile"):
        profile = user.entrepreneur_profile
        user_profile_image = profile.get_avatar_url()
    else:
        user_profile_image = user.profile_image.url if user.profile_image else "/static/assets/img/team/default.png"

    user_full_name = user.full_name or user.email

    context = {
        "form": form,
        "title": "Modifier le Projet",
        "user_profile_image": user_profile_image,
        "user_full_name": user_full_name,
    }

    return render(
        request,
        "ngo/dashboard/entrepreneur/pages/projet/project_update_form.html",
        context
    )

# ---------------------------
# Supprimer un projet
# ---------------------------
@login_required
def project_delete(request, slug):
    project = get_object_or_404(Project, slug=slug, entrepreneur=request.user)

    if request.method == "POST":
        project_title = project.title  # on garde le titre avant suppression
        project.delete()

        # ✅ Envoi d'une notification à l'admin
        admin_users = User.objects.filter(is_superuser=True)
        for admin in admin_users:
            Notification.objects.create(
                recipient=admin,
                sender=request.user,
                type="project_update",
                title="🗑️ Projet supprimé par un entrepreneur",
                message=f"L'entrepreneur {request.user.full_name or request.user.email} "
                        f"a supprimé le projet « {project_title} ». ",
            )

        messages.success(request, f"Le projet « {project_title} » a été supprimé avec succès 🗑️")
        return redirect("dashboard_entrepreneur")

    # 🧑‍💼 Avatar et nom de l’entrepreneur connecté
    user = request.user
    if hasattr(user, "entrepreneur_profile"):
        profile = user.entrepreneur_profile
        user_profile_image = profile.get_avatar_url()
    else:
        user_profile_image = user.profile_image.url if user.profile_image else "/static/assets/img/team/default.png"

    user_full_name = user.full_name or user.email

    context = {
        "project": project,
        "user_profile_image": user_profile_image,
        "user_full_name": user_full_name,
    }

    return render(
        request,
        "ngo/dashboard/entrepreneur/pages/projet/project_confirm_delete.html",
        context
    )

# ---------------------------
# soumettre la preuve de paiement
# ---------------------------
@login_required
def project_payment_verify(request, project_slug):
    """
    Vue pour soumettre le screenshot de paiement pour un projet.
    """
    user = request.user
    project = get_object_or_404(Project, slug=project_slug, entrepreneur=user)

    # Vérifier si un paiement a déjà été initié
    payment_qs = Payment.objects.filter(user=user, project=project)
    payment = payment_qs.last() if payment_qs.exists() else None

    if request.method == "POST":
        form = ProjectPaymentForm(request.POST, request.FILES, instance=payment)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.user = user
            payment.project = project
            payment.is_successful = False  # ⚠️ l'admin devra valider
            payment.save()

            # Marquer le projet comme en attente de validation paiement
            project.status = "pending_payment"
            project.save()

            messages.success(
                request,
                "Votre preuve de paiement a été envoyée ✅. L'administrateur validera votre paiement sous peu."
            )
            return redirect("dashboard_entrepreneur")
    else:
        form = ProjectPaymentForm(instance=payment)

    # 🧑‍💼 Avatar et nom de l’entrepreneur connecté
    if hasattr(user, "entrepreneur_profile"):
        profile = user.entrepreneur_profile
        user_profile_image = profile.get_avatar_url()
    else:
        user_profile_image = user.profile_image.url if user.profile_image else "/static/assets/img/team/default.png"

    user_full_name = user.full_name or user.email

    context = {
        "form": form,
        "project": project,
        "title": f"Soumettre le paiement pour {project.title}",
        "user_profile_image": user_profile_image,
        "user_full_name": user_full_name,
    }

    return render(
        request,
        "ngo/dashboard/entrepreneur/pages/projet/project_payment_verify.html",
        context
    )

# ---------------------------------
# Projet Valider Envoi Notification
# ---------------------------------
@login_required
def validate_project(request, project_id):
    """
    Valide un projet (étape finale du processus) et notifie l'entrepreneur.
    """
    project = get_object_or_404(Project, id=project_id)

    # ✅ Validation du projet
    project.status = "approved"
    project.save()

    # 🔔 Notification automatique
    Notification.objects.create(
        recipient=project.entrepreneur,
        sender=request.user,
        type="project_validated",
        title="🎉 Projet validé !",
        message=f"Votre projet '{project.title}' a été validé et est désormais visible sur la plateforme.",
        related_project=project
    )

    # 🧑‍💼 Avatar et nom de l’entrepreneur connecté
    user = request.user
    if hasattr(user, "entrepreneur_profile"):
        profile = user.entrepreneur_profile
        user_profile_image = profile.get_avatar_url()
    else:
        user_profile_image = user.profile_image.url if user.profile_image else "/static/assets/img/team/default.png"

    user_full_name = user.full_name or user.email

    context = {
        "project": project,
        "user_profile_image": user_profile_image,
        "user_full_name": user_full_name,
    }

    return render(
        request,
        "ngo/dashboard/entrepreneur/pages/projet/project_validation_confirmation.html",
        context
    )

# ---------------------------
# Registrer Entrepreneur
# ---------------------------
def register_entrepreneur(request):
    if request.method == "POST":
        form = EntrepreneurRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("dashboard_entrepreneur")
    else:
        form = EntrepreneurRegisterForm()
    return render(request, "ngo/auth/1/register_entrepreneur.html", {"form": form})

# ---------------------------
# Registrer Investisseur
# ---------------------------
def register_investisseur(request):
    if request.method == "POST":
        form = InvestisseurRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("dashboard_investisseur")
    else:
        form = InvestisseurRegisterForm()

    return render(request, "ngo/auth/2/register_investisseur.html", {"form": form})

# ---------------------------
# Registrer Intermediaire
# ---------------------------
def register_intermediaire(request):
    if request.method == "POST":
        form = IntermediaireRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("dashboard_intermediaire")
    else:
        form = IntermediaireRegisterForm()
    return render(request, "ngo/auth/3/register_intermediaire.html", {"form": form})

# ---------------------------
# Fonction utilitaire : redirection selon rôle
# ---------------------------
def get_dashboard_url_for_role(user):
    """Retourne le dashboard selon le rôle de l'utilisateur."""
    if user.is_entrepreneur:
        return reverse_lazy("dashboard_entrepreneur")
    elif user.is_investisseur:
        return reverse_lazy("dashboard_investisseur")
    elif user.is_intermediaire:
        return reverse_lazy("dashboard_intermediaire")
    return reverse_lazy("home")


# ---------------------------
# Login Générique
# ---------------------------
def _login_view(request, role, template_name):
    """
    Vue générique de connexion selon le rôle.
    """

    # 🔹 Si l'utilisateur est déjà connecté → rediriger automatiquement
    if request.user.is_authenticated:
        return redirect(get_dashboard_url_for_role(request.user))

    if request.method == "POST":
        form = CustomLoginForm(request, data=request.POST)
        if form.is_valid():
            email = form.cleaned_data.get("username")
            password = form.cleaned_data.get("password")
            user = authenticate(request, email=email, password=password)

            if user is not None:
                if user.role == role:
                    login(request, user)
                    messages.success(request, f"Bienvenue {user.display_name()} 👋")
                    return redirect(get_dashboard_url_for_role(user))
                else:
                    messages.error(request, "Vous ne pouvez pas vous connecter ici avec ce rôle.")
            else:
                messages.error(request, "Adresse e-mail ou mot de passe incorrect.")
    else:
        form = CustomLoginForm()

    return render(request, template_name, {"form": form})


# ---------------------------
# Login Entrepreneur
# ---------------------------
def login_entrepreneur(request):
    return _login_view(request, "entrepreneur", "ngo/auth/1/login_entrepreneur.html")


# ---------------------------
# Login Investisseur
# ---------------------------
def login_investisseur(request):
    return _login_view(request, "investisseur", "ngo/auth/2/login_investisseur.html")


# ---------------------------
# Login Intermédiaire
# ---------------------------
def login_intermediaire(request):
    return _login_view(request, "intermediaire", "ngo/auth/3/login_intermediaire.html")


# ---------------------------
# Dashboard Generique
# ---------------------------
@login_required
def dashboard(request):
    role = request.user.role  # 'entrepreneur', 'investisseur', 'intermediaire'
    
    if role == 'entrepreneur':
        template = "ngo/dashboard/dashboard_entrepreneur.html"
    elif role == 'investisseur':
        template = "ngo/dashboard/dashboard_investisseur.html"
    elif role == 'intermediaire':
        template = "ngo/dashboard/dashboard_intermediaire.html"
    else:
        template = "ngo/dashboard/base_user.html"
    
    return render(request, template, {"role": role})

# ---------------------------
# Dashboard Entrepreneur
# ---------------------------
@login_required
def dashboard_entrepreneur(request):
    user = request.user

    # 🔐 Vérification du rôle
    if not getattr(user, "is_entrepreneur", False) and not getattr(user, "is_intermediaire", False):
        messages.error(request, _("⛔ Accès réservé aux entrepreneurs et intermédiaires."))
        return redirect("home")

    # -----------------------------
    # Messages récents
    # -----------------------------
    all_messages = Message.objects.filter(recipient=user, archived=False).order_by("-created_at")
    unread_count = all_messages.filter(is_read=False).count()
    recent_messages = all_messages[:5]

    for msg in recent_messages:
        msg.time_since = timesince(msg.created_at)
        msg.sender_image = (
            getattr(msg.sender, "profile_image.url", None)
            or "/static/assets/img/team/default.png"
        )

    # -----------------------------
    # Notifications
    # -----------------------------
    all_notifications = Notification.objects.filter(recipient=user).order_by('-created_at')
    unread_notifications_count = all_notifications.filter(is_read=False).count()
    recent_notifications = all_notifications[:5]

    for notif in recent_notifications:
        notif.time_since = timesince(notif.created_at)

    # -----------------------------
    # Projets
    # -----------------------------
    if getattr(user, "is_intermediaire", False):
        all_projects = Project.objects.filter(submitted_by=user).order_by("-created_at")
    else:
        all_projects = Project.objects.filter(entrepreneur=user).order_by("-created_at")

    projects = all_projects[:5]
    total_projects = all_projects.count()
    approved = all_projects.filter(status="approved").count()
    pending = all_projects.filter(status="pending").count()
    rejected = all_projects.filter(status="rejected").count()
    completed = all_projects.filter(status="completed").count()

    total_collected = all_projects.aggregate(Sum("collected_amount"))["collected_amount__sum"] or 0
    total_target = all_projects.aggregate(Sum("target_amount"))["target_amount__sum"] or 0
    progress_global = round((total_collected / total_target) * 100, 2) if total_target else 0

    for project in projects:
        project.progress = project.progress_percentage()
        project.total_collected_display = project.collected_amount or 0
        project.contributions = Contribution.objects.filter(
            project=project, payment_status="completed"
        ).order_by("-created_at")

        for c in project.contributions:
            c.percentage = c.percentage_of_project
            c.investor_name = getattr(c.investor, "full_name", c.contributor_name)

    # -----------------------------
    # Retraits
    # -----------------------------
    withdrawal_requests = WithdrawalRequest.objects.filter(entrepreneur=user)
    total_requested = withdrawal_requests.aggregate(Sum("amount"))["amount__sum"] or 0
    total_pending = withdrawal_requests.filter(status="pending").count()
    total_approved = withdrawal_requests.filter(status="approved").count()
    total_rejected = withdrawal_requests.filter(status="rejected").count()

    # -----------------------------
    # Profil utilisateur
    # -----------------------------
    if hasattr(user, "entrepreneur_profile"):
        profile = user.entrepreneur_profile
        user_profile_image = profile.get_avatar_url()
    else:
        user_profile_image = getattr(user, "profile_image.url", "/static/assets/img/team/default.png")

    user_full_name = getattr(user, "full_name", None) or user.email

    # -----------------------------
    # Contexte complet
    # -----------------------------
    context = {
        "projects": projects,
        "total_projects": total_projects,
        "approved": approved,
        "pending": pending,
        "rejected": rejected,
        "completed": completed,
        "total_collected": total_collected,
        "total_target": total_target,
        "progress_global": progress_global,
        "withdrawal_requests": withdrawal_requests,
        "total_requested": total_requested,
        "total_pending": total_pending,
        "total_approved": total_approved,
        "total_rejected": total_rejected,
        "recent_messages": recent_messages,
        "unread_count": unread_count,
        "notifications": recent_notifications,
        "unread_notifications_count": unread_notifications_count,
        "user_profile_image": user_profile_image,
        "user_full_name": user_full_name,
        "title": _("Tableau de bord Entrepreneur"),
    }

    return render(request, "ngo/dashboard/entrepreneur/entrepreneur.html", context)


# ---------------------------
# Dashboard Investisseur
# ---------------------------
@login_required
def dashboard_investisseur(request):
    # Vérifie que l'utilisateur est bien un investisseur
    if not getattr(request.user, "is_investisseur", False):
        return redirect("home")

    # Récupère ou crée le profil investisseur
    profile, created = InvestisseurProfile.objects.get_or_create(
        user=request.user,
        defaults={"capital_available": 0, "company": ""}
    )

    # Contributions complétées de l'investisseur
    contributions = Contribution.objects.filter(
        investor=request.user,
        payment_status="completed"
    )

    # Statistiques globales
    total_invested = sum(c.amount for c in contributions)
    projects_supported = set(c.project for c in contributions)

    stats = {
        "total_invested": total_invested,
        "projects_supported_count": len(projects_supported),
        "capital_available": profile.capital_available,
    }

    # Profil utilisateur et image de profil sécurisée
    user_profile_image = profile.get_avatar_url()
    user_full_name = profile.get_full_name()

    # -------------------------------
    # Dropdown messages (5 derniers messages)
    # -------------------------------
    recent_messages_qs = Message.objects.filter(recipient=request.user).order_by('-created_at')[:5]
    recent_messages = []
    for msg in recent_messages_qs:
        recent_messages.append({
            "id": msg.id,
            "sender_name": msg.sender.full_name or msg.sender.email,
            "avatar_url": msg.get_sender_avatar(),
            "subject": msg.subject,
            "preview": msg.display_preview(),
            "time_ago": msg.time_since(),
            "is_read": msg.is_read,
        })

    # Nombre total de messages non lus
    unread_messages_count = Message.objects.filter(recipient=request.user, is_read=False).count()

    context = {
        "profile": profile,
        "stats": stats,
        "contributions": contributions,
        "projects_supported": projects_supported,
        "user_profile_image": user_profile_image,
        "user_full_name": user_full_name,
        "recent_messages": recent_messages,
        "unread_messages_count": unread_messages_count,
    }

    return render(
        request,
        "ngo/dashboard/investisseur/investisseur.html",
        context
    )


# -------------------------------
# Décorateur commun : restreindre aux intermédiaires
# -------------------------------
def intermediaire_required(view_func):
    """Décorateur pour restreindre l’accès aux comptes intermédiaires."""
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, "Veuillez vous connecter pour accéder à cette page.")
            return redirect("login")
        if not request.user.is_intermediaire:
            messages.error(request, "⛔ Accès réservé aux intermédiaires.")
            return redirect("home")
        return view_func(request, *args, **kwargs)
    return _wrapped_view

# -------------------------------
# Dashboard Intermediaire
# -------------------------------
@login_required
@intermediaire_required
def dashboard_intermediaire(request):
    # Notification et Message sont déjà importés depuis ngo.models
    profile = get_object_or_404(IntermediaireProfile, user=request.user)

    if not profile.subscription_paid:
        messages.warning(request, "Vous devez payer votre abonnement pour accéder aux fonctionnalités.")
        return redirect("intermediaire_payment")

    # Données principales
    entrepreneurs = profile.get_entrepreneurs()
    projects = Project.objects.filter(entrepreneur__in=entrepreneurs).order_by("-created_at")
    payments = IntermediairePayment.objects.filter(intermediaire=request.user).order_by("-created_at")
    campaigns = Campaign.objects.filter(project__in=projects).order_by("-created_at")
    contributions = Contribution.objects.filter(
        Q(campaign__project__in=projects) | Q(loan_campaign__project__in=projects)
    ).select_related("investor", "campaign", "loan_campaign").order_by("-created_at")

    stats = {
        "total_projects": projects.count(),
        "total_collected": projects.aggregate(Sum("collected_amount"))["collected_amount__sum"] or 0,
        "active_campaigns": campaigns.filter(status="active").count(),
        "completed_campaigns": campaigns.filter(status="completed").count(),
        "failed_campaigns": campaigns.filter(status="failed").count(),
        "total_payments": payments.aggregate(Sum("amount"))["amount__sum"] or 0,
        "total_contributions": contributions.count(),
    }

    # Notifications et messages récents
    notifications = Notification.objects.filter(recipient=request.user).order_by("-created_at")[:5]
    unread_count = Notification.objects.filter(recipient=request.user, is_read=False).count()
    messages_received = Message.objects.filter(recipient=request.user, archived=False).order_by("-created_at")[:5]
    unread_messages_count = Message.objects.filter(recipient=request.user, is_read=False).count()

    # Préparer images
    projects_images = [p.image.url for p in projects if p.image][:5]
    contributions_images = []
    for c in contributions:
        if c.campaign and hasattr(c.campaign, "image") and c.campaign.image:
            contributions_images.append(c.campaign.image.url)
        elif c.loan_campaign and hasattr(c.loan_campaign, "image") and c.loan_campaign.image:
            contributions_images.append(c.loan_campaign.image.url)
        if len(contributions_images) >= 5:
            break
    entrepreneurs_images = [e.avatar.url for e in entrepreneurs if e.avatar][:5]

    full_name = profile.get_full_name()
    avatar = profile.get_avatar_url()

    context = {
        "profile": profile,
        "full_name": full_name,
        "avatar": avatar,
        "stats": stats,
        "entrepreneurs": entrepreneurs[:5],
        "projects": projects[:5],
        "campaigns": campaigns[:5],
        "contributions": contributions[:5],
        "payments": payments[:5],
        "projects_images": projects_images,
        "contributions_images": contributions_images,
        "entrepreneurs_images": entrepreneurs_images,
        "notifications": notifications,
        "unread_count": unread_count,
        "messages_received": messages_received,
        "unread_messages_count": unread_messages_count,
    }

    return render(request, "ngo/dashboard/intermediaire/intermediaire.html", context)



# ---------------------------
# Password Reset Entrepreneur
# ---------------------------
class EntrepreneurPasswordResetView(auth_views.PasswordResetView):
    template_name = "ngo/auth/1/password_reset.html"
    email_template_name = "ngo/auth/1/password_reset_email.html"
    subject_template_name = "ngo/auth/1/password_reset_subject.txt"
    success_url = reverse_lazy("entrepreneur_password_reset_done")

# ---------------------------
# Password Reset Investisseur
# ---------------------------
class InvestisseurPasswordResetView(auth_views.PasswordResetView):
    template_name = "ngo/auth/2/password_reset.html"
    email_template_name = "ngo/2/auth/password_reset_email.html"
    subject_template_name = "ngo/2/auth/password_reset_subject.txt"
    success_url = reverse_lazy("investisseur_password_reset_done")

# ---------------------------
# Password Reset Intermediaire
# ---------------------------
class IntermediairePasswordResetView(auth_views.PasswordResetView):
    template_name = "ngo/auth/3/password_reset.html"
    email_template_name = "ngo/auth/3/password_reset_email.html"
    subject_template_name = "ngo/auth/3/password_reset_subject.txt"
    success_url = reverse_lazy("intermediaire_password_reset_done")


# ---------------------------------
# Password Reset Redirect Universal
# ---------------------------------
class UniversalPasswordResetView(PasswordResetView):
    """
    Vue unique de réinitialisation du mot de passe.
    Détecte automatiquement le rôle (entrepreneur/investisseur/intermédiaire)
    et applique le bon template sans révéler d'informations.
    """
    form_class = UniversalPasswordResetForm
    template_name = "ngo/auth/universal/password_reset.html"
    email_template_name = "ngo/auth/universal/password_reset_email.html"
    subject_template_name = "ngo/auth/universal/password_reset_subject.txt"
    success_url = reverse_lazy("password_reset_done")

    ROLE_TEMPLATES = {
        "entrepreneur": {
            "email": "ngo/auth/1/password_reset_email.html",
            "subject": "Réinitialisation de votre mot de passe - IGIA Entrepreneurs",
        },
        "investisseur": {
            "email": "ngo/auth/2/password_reset_email.html",
            "subject": "Réinitialisation de votre mot de passe - IGIA Investisseurs",
        },
        "intermediaire": {
            "email": "ngo/auth/3/password_reset_email.html",
            "subject": "Réinitialisation de votre mot de passe - IGIA Intermédiaires",
        },
    }

    def post(self, request, *args, **kwargs):
        email = request.POST.get("email")
        try:
            user = User.objects.get(email=email)
            role = getattr(user, "role", None)

            if role in self.ROLE_TEMPLATES:
                self.email_template_name = self.ROLE_TEMPLATES[role]["email"]
                self.subject_template_name = None
                self.extra_email_context = {
                    "role_subject": self.ROLE_TEMPLATES[role]["subject"],
                    "user_role": role,
                }
        except User.DoesNotExist:
            # Ne jamais révéler si le compte existe
            pass

        messages.info(
            request,
            "Si un compte est associé à cet e-mail, un lien de réinitialisation vous a été envoyé."
        )

        return super().post(request, *args, **kwargs)

# ---------------------------------
# Logout
# ---------------------------------
@login_required
def user_logout(request):
    """
    Déconnecte l'utilisateur et redirige vers la page d'accueil avec un message.
    """
    logout(request)
    messages.success(request, "Vous avez été déconnecté avec succès.")
    return redirect("home")


# -----------------------------------------------
# Demande de Retrait des fonds par l'entrepreneur
# -----------------------------------------------
@login_required
def request_withdrawal(request, project_id):
    """
    Permet à l'entrepreneur de faire une demande de retrait sur un projet.
    """
    project = get_object_or_404(Project, id=project_id, entrepreneur=request.user)

    if request.method == "POST":
        form = WithdrawalRequestForm(request.POST, project=project)
        if form.is_valid():
            amount = form.cleaned_data["amount"]

            # Vérifie si le projet a assez de fonds
            if amount > project.collected_amount:
                messages.error(request, _("❌ Montant supérieur aux fonds disponibles."))
                return redirect("dashboard_entrepreneur")

            # Vérifie s'il existe déjà une demande en attente
            if WithdrawalRequest.objects.filter(project=project, status="pending").exists():
                messages.warning(request, _("⚠️ Une demande de retrait est déjà en attente pour ce projet."))
                return redirect("dashboard_entrepreneur")

            withdrawal = form.save(commit=False)
            withdrawal.entrepreneur = request.user
            withdrawal.project = project
            withdrawal.save()

            messages.success(request, _("✅ Votre demande de retrait a été soumise avec succès."))
            return redirect("dashboard_entrepreneur")
    else:
        form = WithdrawalRequestForm(project=project)

    # 🧑‍💼 Avatar et nom de l’entrepreneur connecté
    user = request.user
    if hasattr(user, "entrepreneur_profile"):
        profile = user.entrepreneur_profile
        user_profile_image = profile.get_avatar_url()
    else:
        user_profile_image = user.profile_image.url if user.profile_image else "/static/assets/img/team/default.png"

    user_full_name = user.full_name or user.email

    context = {
        "form": form,
        "project": project,
        "user_profile_image": user_profile_image,
        "user_full_name": user_full_name,
    }

    return render(
        request,
        "ngo/dashboard/entrepreneur/pages/retrait/withdrawal_request_form.html",
        context
    )

# -----------------------------------------------
# Contribution au projet de l'entrepreneur
# -----------------------------------------------
@login_required
def project_contributions(request, slug):
    """
    Affiche toutes les contributions pour un projet donné.
    - Accès réservé à l'entrepreneur propriétaire du projet ou à son intermédiaire.
    - Affiche le nom de l'investisseur, le montant, le pourcentage par rapport à l'objectif,
      la date et le statut du paiement.
    """
    user = request.user

    # Récupère le projet
    project = get_object_or_404(Project, slug=slug)

    # Vérification des droits
    if not (project.entrepreneur == user or (user.is_intermediaire and project.submitted_by == user)):
        messages.error(request, _("⛔ Accès refusé : vous n'êtes pas autorisé à voir ce projet."))
        return redirect("dashboard_entrepreneur")

    # Récupère les contributions liées au projet (dons + prêts)
    contributions = Contribution.objects.filter(
        Q(campaign__project=project) | Q(loan_campaign__project=project)
    ).order_by("-created_at")

    # Prépare les données pour le template
    contributions_data = []
    for c in contributions:
        contributions_data.append({
            "investor_name": c.investor.full_name if c.investor else c.contributor_name,
            "amount": c.amount,
            "percentage": c.percentage_of_project,
            "payment_status": c.payment_status,
            "created_at": c.created_at,
        })

    # 🧑‍💼 Avatar et nom de l’entrepreneur connecté
    if hasattr(user, "entrepreneur_profile"):
        profile = user.entrepreneur_profile
        user_profile_image = profile.get_avatar_url()
    else:
        user_profile_image = user.profile_image.url if user.profile_image else "/static/assets/img/team/default.png"

    user_full_name = user.full_name or user.email

    context = {
        "project": project,
        "contributions": contributions_data,
        "total_collected": project.collected_amount,
        "target_amount": project.target_amount,
        "progress_percentage": project.progress_percentage(),
        "title": _("Contributions du projet"),
        "user_profile_image": user_profile_image,
        "user_full_name": user_full_name,
    }

    return render(
        request,
        "ngo/dashboard/entrepreneur/pages/projet/project_contributions.html",
        context
    )

# ----------------------------------------
#  Profil de l'entrepreneur 
# ----------------------------------------
@login_required
def entrepreneur_profile_view(request, user_id=None):
    """
    Affiche le profil de l'entrepreneur connecté ou d'un autre entrepreneur.
    """
    if user_id:
        profile = get_object_or_404(EntrepreneurProfile, user__id=user_id)
    else:
        profile = get_object_or_404(EntrepreneurProfile, user=request.user)

    user = profile.user

    # 🧑‍💼 Avatar et nom de l’entrepreneur
    if hasattr(user, "entrepreneur_profile"):
        entrepreneur_profile = user.entrepreneur_profile
        user_profile_image = entrepreneur_profile.get_avatar_url()
    else:
        user_profile_image = user.profile_image.url if user.profile_image else "/static/assets/img/team/default.png"

    user_full_name = user.full_name or user.email

    # 🔹 Contexte complet
    context = {
        "profile": profile,
        "user": user,
        "user_profile_image": user_profile_image,
        "user_full_name": user_full_name,
        "title": _("Profil de l’entrepreneur"),
    }

    return render(request, "ngo/dashboard/entrepreneur/pages/profil/entrepreneur_profile.html", context)

# ----------------------------------------
# Mise a jour du profil de l'entrepreneur 
# ----------------------------------------
@login_required
def update_entrepreneur_profile(request):
    """
    Permet à un entrepreneur de modifier son profil.
    """
    user = request.user

    # 🔒 Vérifie le rôle de l’utilisateur
    if not getattr(user, "is_entrepreneur", False):
        messages.error(request, _("⛔ Accès réservé aux entrepreneurs."))
        return redirect("home")

    # 🧾 Récupère ou crée le profil associé
    profile, created = EntrepreneurProfile.objects.get_or_create(user=user)

    if request.method == "POST":
        # ⚙️ Passe l’utilisateur au formulaire (utile si le form dépend du rôle)
        form = EntrepreneurProfileForm(request.POST, request.FILES, instance=profile, user=user)
        if form.is_valid():
            form.save()
            messages.success(request, _("✅ Vos informations ont été mises à jour avec succès !"))
            return redirect("update_entrepreneur_profile")
        else:
            messages.error(request, _("❌ Une erreur est survenue. Veuillez vérifier les champs."))
    else:
        form = EntrepreneurProfileForm(instance=profile, user=user)

    # 🧑‍💼 Avatar et nom de l’entrepreneur
    if hasattr(user, "entrepreneur_profile"):
        entrepreneur_profile = user.entrepreneur_profile
        user_profile_image = entrepreneur_profile.get_avatar_url()
    else:
        user_profile_image = user.profile_image.url if user.profile_image else "/static/assets/img/team/default.png"

    user_full_name = user.full_name or user.email

    # 📦 Contexte complet
    context = {
        "form": form,
        "profile": profile,
        "user_profile_image": user_profile_image,
        "user_full_name": user_full_name,
        "title": _("Mettre à jour le profil"),
    }

    return render(
        request,
        "ngo/dashboard/entrepreneur/pages/profil/profile_update.html",
        context
    )

# ----------------------------------------
# Desactivation du Compte de  l'entrepreneur 
# ----------------------------------------
@login_required
def entrepreneur_deactivate_account(request):
    """
    Permet à un entrepreneur de désactiver son compte.
    """
    user = request.user

    # 🔒 Vérifie le rôle
    if not getattr(user, "is_entrepreneur", False):
        messages.error(request, _("⛔ Accès réservé aux entrepreneurs."))
        return redirect("home")

    # 🧑‍💼 Avatar et nom de l’entrepreneur
    if hasattr(user, "entrepreneur_profile"):
        profile = user.entrepreneur_profile
        user_profile_image = profile.get_avatar_url()
    else:
        user_profile_image = user.profile_image.url if user.profile_image else "/static/assets/img/team/default.png"

    user_full_name = user.full_name or user.email

    if request.method == "POST":
        user.is_active = False
        user.is_deleted = True
        user.save()
        logout(request)
        messages.success(
            request,
            _("📴 Votre compte a été désactivé avec succès. "
              "Vous pouvez le réactiver en contactant le support.")
        )
        return redirect("home")

    context = {
        "user_profile_image": user_profile_image,
        "user_full_name": user_full_name,
        "title": _("Désactiver mon compte"),
    }

    return render(
        request,
        "ngo/dashboard/entrepreneur/pages/profil/deactivate_account.html",
        context
    )

# ----------------------------------------
# Suppression du Compte de  l'entrepreneur 
# ----------------------------------------
@login_required
def entrepreneur_delete_account(request):
    """
    Permet à un utilisateur (entrepreneur) de supprimer définitivement son compte.
    Une confirmation SweetAlert sera affichée avant la suppression.
    """
    user = request.user

    # 🔒 Vérifie le rôle
    if not getattr(user, "is_entrepreneur", False):
        messages.error(request, _("⛔ Accès réservé aux entrepreneurs."))
        return redirect("home")

    # 🧑‍💼 Avatar et nom de l’entrepreneur
    if hasattr(user, "entrepreneur_profile"):
        profile = user.entrepreneur_profile
        user_profile_image = profile.get_avatar_url()
    else:
        user_profile_image = user.profile_image.url if user.profile_image else "/static/assets/img/team/default.png"

    user_full_name = user.full_name or user.email

    if request.method == "POST":
        user.delete()
        messages.success(request, _("😢 Votre compte a été supprimé avec succès."))
        return redirect("home")

    context = {
        "user_profile_image": user_profile_image,
        "user_full_name": user_full_name,
        "title": _("Supprimer mon compte"),
    }

    return render(
        request,
        "ngo/dashboard/entrepreneur/pages/profil/delete_account.html",
        context
    )

# ----------------------------
# Vue de Redirection 
# ----------------------------
def login_redirect(request):
    """
    Redirige l'utilisateur non connecté vers la page de login appropriée,
    en conservant la langue et la page d'origine (paramètre ?next=...).
    """
    lang = get_language() or 'fr'
    next_url = request.GET.get('next', '')

    # Base dynamique selon la langue
    base = f'/{lang}/login'

    if 'entrepreneur' in next_url:
        login_url = f'{base}/entrepreneur/'
    elif 'investisseur' in next_url:
        login_url = f'{base}/investisseur/'
    elif 'intermediaire' in next_url:
        login_url = f'{base}/intermediaire/'
    else:
        # Par défaut (si la vue protégée ne contient pas d'indice)
        login_url = f'{base}/entrepreneur/'

    # ✅ Préserve le paramètre next, pour retourner à la bonne page après login
    if next_url:
        return redirect(f'{login_url}?next={next_url}')
    return redirect(login_url)


# -------------------------------
# Notifications Entrepreneurs
# -------------------------------
@login_required
def notification_entrepreneur(request):
    if not getattr(request.user, "is_entrepreneur", False) and not getattr(request.user, "is_intermediaire", False):
        messages.error(request, "⛔ Accès réservé aux entrepreneurs et intermédiaires.")
        return redirect("home")

    notifications = Notification.objects.filter(
        recipient=request.user
    ).order_by('-created_at')

    # Marquer toutes comme lues si demandé
    if request.GET.get('mark_all_read') == '1':
        for n in notifications.filter(is_read=False):
            n.mark_as_read()

    context = {
        "notifications": notifications,
        "title": "Toutes les notifications",
    }
    return render(request, "ngo/dashboard/entrepreneur/pages/notification/notifications.html", context)

# ------------------------------------
# Notifications detaille Entrepreneurs
# ------------------------------------

@login_required
def notification_detail_entrepreneur(request, pk):
    notif = get_object_or_404(Notification, pk=pk, recipient=request.user)
    
    # Marquer la notification comme lue si ce n'est pas déjà fait
    if not notif.is_read:
        notif.mark_as_read()

    context = {
        "notification": notif,
        "title": f"Détails - {notif.title}"
    }
    return render(request, "ngo/dashboard/entrepreneur/notification/notification_detail.html", context)

# -------------------------------
# Notifications Investisseurs
# -------------------------------
@login_required
def notification_investisseur(request):
    if not getattr(request.user, "is_investisseur", False) and not getattr(request.user, "is_intermediaire", False):
        messages.error(request, "⛔ Accès réservé aux investisseurs et intermédiaires.")
        return redirect("home")

    notifications = Notification.objects.filter(
        recipient=request.user
    ).order_by('-created_at')

    if request.GET.get('mark_all_read') == '1':
        for n in notifications.filter(is_read=False):
            n.mark_as_read()
        messages.success(request, "✅ Toutes vos notifications ont été marquées comme lues.")

    context = {
        "notifications": notifications,
        "title": "Toutes les notifications - Investisseur",
    }

    return render(
        request,
        "ngo/dashboard/investisseur/pages/notification/notifications.html",
        context
    )


# ------------------------------------
# Notifications detaille Investisseur
# ------------------------------------
@login_required
def notification_detail_investisseur(request, pk):
    notif = get_object_or_404(Notification, pk=pk, recipient=request.user)

    # Marquer la notification comme lue si ce n’est pas déjà fait
    if not notif.is_read:
        notif.mark_as_read()

    context = {
        "notification": notif,
        "title": f"Détails - {notif.title}",
    }
    return render(
        request,
        "ngo/dashboard/investisseur/pages/notification/notification_detail.html",
        context,
    )


# -------------------------------
# Notifications Intermédiaires
# -------------------------------
@login_required
@intermediaire_required
def notification_intermediaire(request):
    # Profil de l’intermédiaire
    profile = get_object_or_404(IntermediaireProfile, user=request.user)

    # 🔹 Informations profil
    full_name = profile.get_full_name()
    avatar = profile.get_avatar_url()

    # Notifications
    notifications = Notification.objects.filter(recipient=request.user).order_by("-created_at")
    notifications.filter(is_read=False).update(is_read=True, read_at=timezone.now())
    unread_count = Notification.objects.filter(recipient=request.user, is_read=False).count()

    context = {
        "notifications": notifications,
        "profile": profile,
        "full_name": full_name,   # ✅ nom complet
        "avatar": avatar,         # ✅ photo de profil
        "unread_count": unread_count,
    }

    return render(
        request,
        "ngo/dashboard/intermediaire/pages/notification/notifications.html",
        context,
    )



# ------------------------------------
# Notifications detaille Intermediaire
# ------------------------------------
@login_required
@intermediaire_required
def intermediaire_notifications_detail(request, pk):
    """
    Affiche le détail d'une notification spécifique pour un intermédiaire.
    """
    from notifications.models import Notification  # Import local pour éviter les conflits circulaires

    profile = get_object_or_404(IntermediaireProfile, user=request.user)

    # ✅ On vérifie que la notification appartient bien à l’utilisateur connecté
    notification = get_object_or_404(Notification, pk=pk, recipient=request.user)

    # ✅ Marquer comme lue si ce n’est pas déjà fait
    if not notification.is_read:
        notification.is_read = True
        notification.read_at = timezone.now()
        notification.save(update_fields=["is_read", "read_at"])

    # ✅ Compter les non-lues pour la navbar ou le badge
    unread_count = Notification.objects.filter(
        recipient=request.user, is_read=False
    ).count()

    context = {
        "notification": notification,
        "profile": profile,
        "unread_count": unread_count,
    }

    return render(
        request,
        "ngo/dashboard/intermediaire/pages/notification/notification_detail.html",
        context,
    )


# ---------------------------
# Supprimer une Notification
# ---------------------------
@login_required
@intermediaire_required
def intermediaire_notification_delete(request, pk):
    """Supprime une notification spécifique pour un intermédiaire."""
    from notifications.models import Notification  # Import local pour éviter les conflits circulaires

    notification = get_object_or_404(Notification, pk=pk, recipient=request.user)

    try:
        notification.delete()
        messages.success(request, "✅ Notification supprimée avec succès.")
    except Exception:
        messages.error(request, "❌ Impossible de supprimer cette notification.")

    return redirect("intermediaire_notifications")


# -------------------------------------------------------------
#                        Investisseur
# -------------------------------------------------------------

# --------------------------
# Liste des Projets Disponibles
# --------------------------
@login_required
def projects_available_investisseur(request):
    # Vérifie que l'utilisateur est bien un investisseur
    if not hasattr(request.user, "is_investisseur") or not request.user.is_investisseur:
        messages.error(request, "⛔ Accès réservé aux investisseurs.")
        return redirect("home")

    # Récupération des projets approuvés
    projects = Project.objects.filter(status="approved").order_by("-created_at")
    categories = Category.objects.all()

    # Récupération ou création du profil investisseur
    profile, created = InvestisseurProfile.objects.get_or_create(
        user=request.user,
        defaults={"capital_available": 0, "company": ""}
    )

    # Profil utilisateur et image de profil sécurisée
    user_profile_image = profile.get_avatar_url()
    user_full_name = profile.get_full_name()

    context = {
        "projects": projects,
        "categories": categories,
        "user_profile_image": user_profile_image,
        "user_full_name": user_full_name,
    }

    return render(
        request,
        "ngo/dashboard/investisseur/pages/projet/projects_available.html",
        context
    )


# --------------------------
# Détail d’un Projet
# --------------------------
@login_required
def project_detail_investisseur(request, slug):
    # Vérifie que l'utilisateur est bien un investisseur
    if not hasattr(request.user, "is_investisseur") or not request.user.is_investisseur:
        messages.error(request, "⛔ Accès réservé aux investisseurs.")
        return redirect("home")

    # Récupération ou création du profil investisseur
    profile, created = InvestisseurProfile.objects.get_or_create(
        user=request.user,
        defaults={"capital_available": 0, "company": ""}
    )

    # Profil utilisateur et image de profil sécurisée
    user_profile_image = profile.get_avatar_url()
    user_full_name = profile.get_full_name()

    # Récupère le projet demandé
    project = get_object_or_404(Project, slug=slug)

    # Récupère les campagnes associées au projet
    campaigns = project.campaigns.filter(status="active")
    loan_campaigns = project.loan_campaigns.filter(status="active")

    context = {
        "project": project,
        "campaigns": campaigns,
        "loan_campaigns": loan_campaigns,
        "user_profile_image": user_profile_image,
        "user_full_name": user_full_name,
    }

    return render(
        request,
        "ngo/dashboard/investisseur/pages/projet/project_detail.html",
        context,
    )


# --------------------------
# Liste des Contributions
# --------------------------
@login_required
def contributions_list_investisseur(request):
    # Vérifie que l'utilisateur est bien un investisseur
    if not hasattr(request.user, "is_investisseur") or not request.user.is_investisseur:
        messages.error(request, "⛔ Accès réservé aux investisseurs.")
        return redirect("home")

    # Récupération ou création du profil investisseur
    profile, created = InvestisseurProfile.objects.get_or_create(
        user=request.user,
        defaults={"capital_available": 0, "company": ""}
    )

    # Profil utilisateur et image de profil sécurisée
    user_profile_image = profile.get_avatar_url()
    user_full_name = profile.get_full_name()

    # Récupération des contributions de l'investisseur
    contributions = Contribution.objects.filter(
        investor=request.user
    ).order_by('-created_at')
    total_invested = sum(c.amount for c in contributions)

    context = {
        "contributions": contributions,
        "title": "Mes contributions",
        "total_invested": total_invested,
        "user_profile_image": user_profile_image,
        "user_full_name": user_full_name,
    }

    return render(
        request,
        "ngo/dashboard/investisseur/pages/contribution/contributions_list.html",
        context
    )


# --------------------------
# Detail des Contributions
# --------------------------
@login_required
def contribution_detail_investisseur(request, pk):
    # Vérifie que l'utilisateur est bien un investisseur
    if not hasattr(request.user, "is_investisseur") or not request.user.is_investisseur:
        messages.error(request, "⛔ Accès réservé aux investisseurs.")
        return redirect("home")

    # Récupération ou création du profil investisseur
    profile, created = InvestisseurProfile.objects.get_or_create(
        user=request.user,
        defaults={"capital_available": 0, "company": ""}
    )

    # Profil utilisateur et image de profil sécurisée
    user_profile_image = profile.get_avatar_url()
    user_full_name = profile.get_full_name()

    # Récupère la contribution de cet investisseur uniquement
    contribution = get_object_or_404(
        Contribution.objects.select_related("campaign", "loan_campaign", "investor"),
        pk=pk,
        investor=request.user
    )

    # Déterminer la campagne associée (classique ou prêt)
    campaign = contribution.campaign or contribution.loan_campaign

    # Calcul du rendement estimé si taux d'intérêt disponible
    estimated_return = None
    if hasattr(campaign, "interest_rate") and campaign.interest_rate:
        estimated_return = contribution.amount * (1 + (campaign.interest_rate / 100))

    context = {
        "contribution": contribution,
        "campaign": campaign,
        "estimated_return": estimated_return,
        "user_profile_image": user_profile_image,
        "user_full_name": user_full_name,
    }

    return render(
        request,
        "ngo/dashboard/investisseur/pages/contribution/contribution_detail.html",
        context,
    )


# --------------------------
# Liste des Campagnes de Prêt
# --------------------------
@login_required
def loan_campaigns_list_investisseur(request):
    # Vérifie que l'utilisateur est bien un investisseur
    if not hasattr(request.user, "is_investisseur") or not request.user.is_investisseur:
        messages.error(request, "⛔ Accès réservé aux investisseurs.")
        return redirect("home")

    # Récupération ou création du profil investisseur
    profile, created = InvestisseurProfile.objects.get_or_create(
        user=request.user,
        defaults={"capital_available": 0, "company": ""}
    )

    # Profil utilisateur et image de profil sécurisée
    user_profile_image = profile.get_avatar_url()
    user_full_name = profile.get_full_name()

    # Récupère toutes les campagnes de prêt actives
    loan_campaigns = LoanCampaign.objects.filter(status="active").select_related("project")

    context = {
        "loan_campaigns": loan_campaigns,
        "user_profile_image": user_profile_image,
        "user_full_name": user_full_name,
    }

    return render(
        request,
        "ngo/dashboard/investisseur/pages/campagne/loan_campaigns_list.html",
        context,
    )


# --------------------------
# Détail d’une Campagne
# --------------------------
@login_required
def loan_campaign_detail_investisseur(request, pk):
    # Vérifie que l'utilisateur est bien un investisseur
    if not hasattr(request.user, "is_investisseur") or not request.user.is_investisseur:
        messages.error(request, "⛔ Accès réservé aux investisseurs.")
        return redirect("home")

    # Récupération ou création du profil investisseur
    profile, created = InvestisseurProfile.objects.get_or_create(
        user=request.user,
        defaults={"capital_available": 0, "company": ""}
    )

    # Profil utilisateur et image de profil sécurisée
    user_profile_image = profile.get_avatar_url()
    user_full_name = profile.get_full_name()

    # Récupère la campagne
    loan_campaign = get_object_or_404(LoanCampaign, pk=pk)
    contributions = loan_campaign.contributions.filter(payment_status="completed")

    # Calcul des statistiques
    total_contributed = sum(c.amount for c in contributions)
    progress = (
        (total_contributed / loan_campaign.target_amount) * 100
        if loan_campaign.target_amount
        else 0
    )

    context = {
        "loan_campaign": loan_campaign,
        "contributions": contributions,
        "progress": round(progress, 2),
        "total_contributed": total_contributed,
        "user_profile_image": user_profile_image,
        "user_full_name": user_full_name,
    }

    return render(
        request,
        "ngo/dashboard/investisseur/pages/campagne/loan_campaign_detail.html",
        context,
    )


# --------------------------
# Profil Investisseur (Vue affichage)
# --------------------------
@login_required
def profile_investisseur(request):
    """
    Affiche le profil de l'investisseur connecté.
    Crée le profil si nécessaire et sécurise l'accès aux images.
    """
    # Vérifie que l'utilisateur est bien un investisseur
    if not request.user.is_investisseur:
        messages.error(request, "⛔ Accès réservé aux investisseurs.")
        return redirect("home")

    # Crée le profil s'il n'existe pas encore
    profile, created = InvestisseurProfile.objects.get_or_create(
        user=request.user,
        defaults={
            "capital_available": 0,
            "company": "",
        }
    )

    # Assure que get_avatar_url() ne plante jamais
    avatar_url = profile.get_avatar_url()  # Méthode sécurisée dans le modèle

    # Profil utilisateur et image de profil sécurisée
    user_profile_image = profile.get_avatar_url()
    user_full_name = profile.get_full_name()

    context = {
        "profile": profile,
        "avatar_url": avatar_url,
        "user_profile_image": user_profile_image,
        "user_full_name": user_full_name,
    }

    return render(
        request,
        "ngo/dashboard/investisseur/pages/profile/profile.html",
        context
    )

# ------------------------------
# Édition du Profil Investisseur
# ------------------------------
@login_required
def edit_investisseur_profile(request):
    """
    Permet à un investisseur de modifier son profil.
    """
    # Vérifie que l'utilisateur est bien un investisseur
    if not request.user.is_investisseur:
        messages.error(request, "⛔ Accès réservé aux investisseurs.")
        return redirect("home")

    # Récupère ou crée le profil de l’investisseur
    profile, created = InvestisseurProfile.objects.get_or_create(
        user=request.user,
        defaults={"capital_available": 0, "company": ""}
    )

    if request.method == "POST":
        form = InvestisseurProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "✅ Profil mis à jour avec succès !")
            return redirect("profile_investisseur")
        else:
            messages.error(request, "❌ Erreurs dans le formulaire. Veuillez vérifier les champs.")
    else:
        # Préremplir avec les données de l’utilisateur
        initial_data = {
            "full_name": request.user.full_name,
            "email": request.user.email,
            "phone": request.user.phone,
            "country": request.user.country,
            "city": request.user.city,
            "bio": request.user.bio,
            "profile_image": request.user.profile_image,
        }
        form = InvestisseurProfileForm(instance=profile, initial=initial_data)

    # Profil utilisateur et image de profil sécurisée
    user_profile_image = profile.get_avatar_url()
    user_full_name = profile.get_full_name()

    context = {
        "form": form,
        "profile": profile,
        "user_profile_image": user_profile_image,
        "user_full_name": user_full_name,
    }

    return render(
        request,
        "ngo/dashboard/investisseur/pages/profile/edit_profile.html",
        context
    )

    """
    Permet à un investisseur de modifier son profil.
    """
    if not request.user.is_investisseur:
        messages.error(request, "⛔ Accès réservé aux investisseurs.")
        return redirect("home")

    # Récupère ou crée le profil de l’investisseur
    profile, created = InvestisseurProfile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        form = InvestisseurProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "✅ Profil mis à jour avec succès !")
            return redirect("profile_investisseur")
        else:
            messages.error(request, "❌ Erreurs dans le formulaire. Veuillez vérifier les champs.")
    else:
        # Préremplir avec les données de l’utilisateur
        initial_data = {
            "full_name": request.user.full_name,
            "email": request.user.email,
            "phone": request.user.phone,
            "country": request.user.country,
            "city": request.user.city,
            "bio": request.user.bio,
            "profile_image": request.user.profile_image,
        }
        form = InvestisseurProfileForm(instance=profile, initial=initial_data)

    # Profil utilisateur et image de profil sécurisée
    user_profile_image = profile.get_avatar_url()
    user_full_name = profile.get_full_name()

    context = {
        "form": form, 
        "profile": profile,
        "user_profile_image": user_profile_image,
        "user_full_name": user_full_name,
    }

    return render(
        request,
        "ngo/dashboard/investisseur/pages/profile/edit_profile.html",
        context
    )

# ------------------------------------
# Désactivation du compte Investisseur
# ------------------------------------
@login_required
def deactivate_investisseur(request):
    """
    Permet à un investisseur de désactiver son compte.
    """
    # Vérifie que l'utilisateur est bien un investisseur
    if not hasattr(request.user, "is_investisseur") or not request.user.is_investisseur:
        messages.error(request, "⛔ Accès réservé aux investisseurs.")
        return redirect("home")

    # Récupère ou crée le profil pour sécuriser l'accès aux informations
    profile, created = InvestisseurProfile.objects.get_or_create(
        user=request.user,
        defaults={"capital_available": 0, "company": ""}
    )

    # Profil utilisateur et image de profil sécurisée
    user_profile_image = profile.get_avatar_url()
    user_full_name = profile.get_full_name()

    if request.method == "POST":
        # Désactive le compte
        request.user.is_active = False
        request.user.save()
        logout(request)
        messages.warning(
            request,
            "⚠️ Votre compte a été désactivé. Vous pouvez le réactiver plus tard en contactant le support."
        )
        return redirect("home")

    context = {
        "profile": profile,
        "user_profile_image": user_profile_image,
        "user_full_name": user_full_name,
    }

    return render(
        request,
        "ngo/dashboard/investisseur/pages/profile/deactivate_confirm.html",
        context
    )

# ---------------------------------------------
# Suppression définitive du compte Investisseur
# ---------------------------------------------
@login_required
def delete_account_investisseur(request):
    """
    Permet à un investisseur de supprimer définitivement son compte.
    """
    # Vérifie que l'utilisateur est bien un investisseur
    if not hasattr(request.user, "is_investisseur") or not request.user.is_investisseur:
        messages.error(request, "⛔ Accès réservé aux investisseurs.")
        return redirect("home")

    # Récupère ou crée le profil pour sécuriser l'accès aux informations
    profile, created = InvestisseurProfile.objects.get_or_create(
        user=request.user,
        defaults={"capital_available": 0, "company": ""}
    )

    # Profil utilisateur et image de profil sécurisée
    user_profile_image = profile.get_avatar_url()
    user_full_name = profile.get_full_name()

    if request.method == "POST":
        user = request.user
        logout(request)
        user.delete()
        messages.success(request, "🗑️ Votre compte a été supprimé définitivement avec succès.")
        return redirect("home")

    context = {
        "profile": profile,
        "user_profile_image": user_profile_image,
        "user_full_name": user_full_name,
    }

    return render(
        request,
        "ngo/dashboard/investisseur/pages/profile/delete_confirm.html",
        context
    )


# -------------------------------
# Notifications Investisseurs
# -------------------------------
@login_required
def notification_investisseur(request):
    user = request.user

    # 🔒 Vérification du rôle
    if not getattr(user, "is_investisseur", False) and not getattr(user, "is_intermediaire", False):
        messages.error(request, "⛔ Accès réservé aux investisseurs et intermédiaires.")
        return redirect("home")

    # 📬 Récupération des notifications
    notifications = Notification.objects.filter(
        recipient=user
    ).order_by('-created_at')

    # ✅ Marquer toutes comme lues si demandé
    if request.GET.get('mark_all_read') == '1':
        for n in notifications.filter(is_read=False):
            n.mark_as_read()
        messages.success(request, "✅ Toutes vos notifications ont été marquées comme lues.")

    # 👤 Profil utilisateur et image sécurisée
    if hasattr(user, "investisseur_profile"):
        profile = user.investisseur_profile
    else:
        profile = getattr(user, "profile", None)

    user_profile_image = profile.get_avatar_url() if profile else "/static/assets/img/team/default.png"
    user_full_name = profile.get_full_name() if profile else (user.full_name or user.email)

    context = {
        "notifications": notifications,
        "title": "Toutes les notifications - Investisseur",
        "user_profile_image": user_profile_image,
        "user_full_name": user_full_name,
    }

    return render(
        request,
        "ngo/dashboard/investisseur/pages/notification/notifications.html",
        context
    )


# -------------------------------
# Notification detail Investisseur
# -------------------------------
@login_required
def notification_detail_investisseur(request, pk):
    user = request.user

    # 🔒 Vérification du rôle
    if not getattr(user, "is_investisseur", False) and not getattr(user, "is_intermediaire", False):
        messages.error(request, "⛔ Accès réservé aux investisseurs et intermédiaires.")
        return redirect("home")

    # 📄 Récupération de la notification
    notification = get_object_or_404(Notification, pk=pk, recipient=user)

    # ✅ Marquer comme lue si nécessaire
    if not notification.is_read:
        notification.mark_as_read()

    # 👤 Profil utilisateur et image sécurisée
    if hasattr(user, "investisseur_profile"):
        profile = user.investisseur_profile
    else:
        profile = getattr(user, "profile", None)

    user_profile_image = profile.get_avatar_url() if profile else "/static/assets/img/team/default.png"
    user_full_name = profile.get_full_name() if profile else (user.full_name or user.email)

    context = {
        "notification": notification,
        "title": notification.title,
        "user_profile_image": user_profile_image,
        "user_full_name": user_full_name,
    }

    return render(
        request,
        "ngo/dashboard/investisseur/pages/notification/notification_detail.html",
        context
    )




# --------------------------------------------------------
#                     Intermediaire
# --------------------------------------------------------

# -------------------------------
# Profil Intermédiaire
# -------------------------------
@login_required
@intermediaire_required
def intermediaire_profile(request):
    profile = get_object_or_404(IntermediaireProfile, user=request.user)

    if request.method == "POST":
        organization = request.POST.get("organization")
        profile.organization = organization
        profile.save()
        messages.success(request, "Profil mis à jour avec succès ✅")
        return redirect("intermediaire_profile")

    # 🔹 Ajout : nom complet + photo
    full_name = profile.get_full_name()
    avatar = profile.get_avatar_url()

    context = {
        "profile": profile,
        "full_name": full_name,  # ✅ Nom complet
        "avatar": avatar,        # ✅ Photo de profil
    }
    return render(request, "ngo/dashboard/intermediaire/pages/profile/profile.html", context)



# --------------------------------
# Profil Intermédiaire mise a jour
# --------------------------------
@login_required
@intermediaire_required
def edit_intermediaire_profile(request):
    profile = request.user.intermediaire_profile

    if request.method == "POST":
        form = IntermediaireProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "✅ Profil mis à jour avec succès.")
            return redirect("intermediaire_dashboard")
    else:
        form = IntermediaireProfileForm(instance=profile)

    # 🔹 Ajout : nom complet + avatar
    full_name = profile.get_full_name()
    avatar = profile.get_avatar_url()

    context = {
        "form": form,
        "profile": profile,
        "full_name": full_name,  # ✅ Nom complet de l’intermédiaire
        "avatar": avatar,        # ✅ Photo de profil
    }

    return render(request, "ngo/dashboard/intermediaire/pages/profile/profile_form.html", context)


# --------------------------------
# Profil Intermédiaire Desactiver
# --------------------------------
@login_required
def desactiver_compte_intermediaire(request):
    if not request.user.is_intermediaire:
        messages.error(request, "⛔ Action réservée aux intermédiaires.")
        return redirect("home")

    if request.method == "POST":
        form = ConfirmIntermediaireDisableAccountForm(request.POST)
        if form.is_valid():
            request.user.mark_deleted()
            messages.warning(
                request,
                "🛑 Votre compte a été désactivé. Vous pouvez le réactiver plus tard en contactant l’administration."
            )
            return redirect("logout")  # déconnexion immédiate
    else:
        form = ConfirmIntermediaireDisableAccountForm()

    # 🔹 Ajout : récupération du profil, nom complet et avatar
    profile = request.user.intermediaire_profile
    full_name = profile.get_full_name()
    avatar = profile.get_avatar_url()

    context = {
        "form": form,
        "profile": profile,
        "full_name": full_name,  # ✅ Nom complet de l’intermédiaire
        "avatar": avatar,        # ✅ Photo de profil
    }

    return render(request, "ngo/dashboard/intermediaire/pages/profile/confirm_disable.html", context)



# --------------------------------
# Profil Intermédiaire Supprimer
# --------------------------------
@login_required
def supprimer_compte_intermediaire(request):
    if not request.user.is_intermediaire:
        messages.error(request, "⛔ Action réservée aux intermédiaires.")
        return redirect("home")

    if request.method == "POST":
        form = ConfirmDeleteAccountForm(request.POST)
        if form.is_valid():
            email = request.user.email
            request.user.delete_permanently()
            messages.success(request, f"✅ Le compte {email} a été supprimé définitivement.")
            return redirect("home")
    else:
        form = ConfirmDeleteAccountForm()

    # 🔹 Ajout : profil + nom complet + avatar
    profile = request.user.intermediaire_profile
    full_name = profile.get_full_name()
    avatar = profile.get_avatar_url()

    context = {
        "form": form,
        "profile": profile,
        "full_name": full_name,  # ✅ Nom complet de l’intermédiaire
        "avatar": avatar,        # ✅ Photo de profil
    }

    return render(request, "ngo/dashboard/intermediaire/pages/profile/confirm_delete.html", context)


# ---------------------------
# Intermediaire paiement
# ---------------------------
@login_required
@intermediaire_required
def intermediaire_payment(request):
    user = request.user
    profile = user.intermediaire_profile

    # Récupérer tous les paiements de l’intermédiaire
    payments = IntermediairePayment.objects.filter(intermediaire=user).order_by("-created_at")

    if request.method == "POST":
        form = IntermediairePaymentForm(request.POST, request.FILES)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.intermediaire = user
            payment.status = "pending"
            payment.save()
            messages.success(
                request,
                "✅ Preuve de paiement envoyée avec succès. Veuillez attendre la validation par l’administration."
            )
            return redirect("intermediaire_payment")
    else:
        form = IntermediairePaymentForm()

    context = {
        "form": form,
        "payments": payments,
        "profile": profile,
        "full_name": profile.get_full_name(),
        "avatar": profile.get_avatar_url(),
    }
    return render(
        request,
        "ngo/dashboard/intermediaire/pages/payment/intermediaire_payment.html",
        context
    )


# -------------------------------
# Paiements de l’intermédiaire
# -------------------------------
@login_required
@intermediaire_required
def intermediaire_payments(request):
    """Affiche la liste des paiements effectués par l’intermédiaire."""
    profile = get_object_or_404(IntermediaireProfile, user=request.user)
    payments = IntermediairePayment.objects.filter(intermediaire=request.user).order_by("-created_at")

    # 🔹 Ajout du nom complet et de la photo de profil
    full_name = profile.get_full_name()
    avatar = profile.get_avatar_url()

    context = {
        "profile": profile,
        "payments": payments,
        "full_name": full_name,  # ✅ Nom complet de l’intermédiaire
        "avatar": avatar,        # ✅ Photo de profil
    }

    return render(
        request,
        "ngo/dashboard/intermediaire/pages/payment/payments_list.html",
        context
    )



@login_required
@intermediaire_required
def intermediaire_payment_upload(request):
    """Permet à un intermédiaire d’envoyer une preuve de paiement."""
    profile = get_object_or_404(IntermediaireProfile, user=request.user)

    if request.method == "POST":
        amount = request.POST.get("amount")
        currency_id = request.POST.get("currency_id")
        proof = request.FILES.get("proof")

        # 🛡️ Validation basique
        if not amount or not currency_id or not proof:
            messages.error(request, "⚠️ Veuillez remplir tous les champs obligatoires.")
            return redirect("intermediaire_payment_upload")

        # 💾 Enregistrement du paiement
        IntermediairePayment.objects.create(
            intermediaire=request.user,
            amount=amount,
            currency_id=currency_id,
            proof=proof,
            status="pending",
        )

        messages.success(request, "✅ Preuve de paiement envoyée avec succès. En attente de validation.")
        return redirect("intermediaire_payments")

    # 🔹 Informations pour le template
    currencies = Currency.objects.all().order_by("code")
    full_name = profile.get_full_name()
    avatar = profile.get_avatar_url()

    context = {
        "profile": profile,
        "currencies": currencies,
        "full_name": full_name,
        "avatar": avatar,
    }

    return render(request, "ngo/dashboard/intermediaire/pages/payment/payment_upload.html", context)


@login_required
@intermediaire_required
def delete_intermediaire_payment(request, pk):
    """
    Supprime un paiement d'intermédiaire de manière sécurisée.
    Affiche un message de succès ou d'erreur.
    """
    payment = get_object_or_404(IntermediairePayment, pk=pk, intermediaire=request.user)

    if request.method == "POST":
        payment.delete()
        messages.success(request, _("✅ Paiement supprimé avec succès."))
        return redirect("intermediaire_payments")
    else:
        messages.warning(request, _("⛔ Action non autorisée."))
        return redirect("intermediaire_payments")


# ---------------------------------
# Associer un entrepreneur existant
# ---------------------------------
@login_required
@intermediaire_required
def intermediaire_add_entrepreneur(request):
    """Associer un entrepreneur existant à l'intermédiaire connecté"""
    if not hasattr(request.user, "intermediaire_profile"):
        messages.error(request, "⛔ Vous devez être un intermédiaire pour accéder à cette page.")
        return redirect("home")

    profile = request.user.intermediaire_profile

    if request.method == "POST":
        entrepreneur_id = request.POST.get("entrepreneur_id")
        entrepreneur = get_object_or_404(User, id=entrepreneur_id, role="entrepreneur")
        profile.represented_entrepreneurs.add(entrepreneur)
        messages.success(
            request,
            _(f"{entrepreneur.full_name} a été ajouté à vos entrepreneurs représentés ✅")
        )
        return redirect("intermediaire_entrepreneurs")

    # Exclure les entrepreneurs déjà associés à cet intermédiaire
    entrepreneurs = User.objects.filter(role="entrepreneur").exclude(
        id__in=profile.represented_entrepreneurs.all()
    )

    # 🔹 Ajout : nom complet + avatar
    full_name = profile.get_full_name()
    avatar = profile.get_avatar_url()

    context = {
        "entrepreneurs": entrepreneurs,
        "profile": profile,
        "full_name": full_name,  # ✅ Nom complet de l’intermédiaire
        "avatar": avatar,        # ✅ Photo de profil
    }

    return render(request, "ngo/dashboard/intermediaire/pages/action/add_entrepreneur.html", context)


# ----------------------------------------
# Créer un nouvel entrepreneur (si vérifié
# ----------------------------------------
@login_required
@intermediaire_required
def intermediaire_create_entrepreneur(request):
    """Permet à un intermédiaire vérifié de créer un nouvel entrepreneur avec profil complet."""
    
    if not hasattr(request.user, "intermediaire_profile"):
        messages.error(request, "⛔ Vous devez être un intermédiaire pour accéder à cette page.")
        return redirect("home")

    profile = request.user.intermediaire_profile

    if not profile.verified:
        messages.warning(request, "⚠️ Votre compte doit être vérifié avant de pouvoir enregistrer un entrepreneur.")
        return redirect("dashboard_intermediaire")

    if request.method == "POST":
        form = EntrepreneurProfileForm(request.POST, request.FILES)
        if form.is_valid():
            # Créer un utilisateur entrepreneur
            email = form.cleaned_data.get("email")
            if User.objects.filter(email=email).exists():
                messages.error(request, _("Un utilisateur avec cet email existe déjà."))
                return redirect("intermediaire_create_entrepreneur")

            entrepreneur_user = User.objects.create_user(
                email=email,
                password=User.objects.make_random_password(),
                full_name=form.cleaned_data.get("full_name"),
                phone=form.cleaned_data.get("phone"),
                city=form.cleaned_data.get("city"),
                role="entrepreneur",
            )

            # Créer le profil EntrepreneurProfile
            form.instance.user = entrepreneur_user
            form.save()

            # Associer cet entrepreneur à l’intermédiaire
            profile.represented_entrepreneurs.add(entrepreneur_user)

            messages.success(
                request,
                _(f"L'entrepreneur {entrepreneur_user.full_name} a été créé et vous est associé ✅")
            )
            return redirect("intermediaire_entrepreneurs")
    else:
        form = EntrepreneurProfileForm()

    context = {
        "form": form,
        "profile": profile,
        "full_name": profile.get_full_name(),
        "avatar": profile.get_avatar_url(),
    }

    return render(
        request,
        "ngo/dashboard/intermediaire/pages/action/create_entrepreneur.html",
        context
    )

# -------------------------------
# Liste des entrepreneurs représentés
# -------------------------------
@login_required
@intermediaire_required
def intermediaire_entrepreneurs(request):
    """Affiche la liste des entrepreneurs représentés par l'intermédiaire connecté"""
    profile = get_object_or_404(IntermediaireProfile, user=request.user)
    entrepreneurs = profile.get_entrepreneurs()

    # 🔹 Ajout : informations d’en-tête du profil
    full_name = profile.get_full_name()
    avatar = profile.get_avatar_url()

    context = {
        "entrepreneurs": entrepreneurs,
        "profile": profile,
        "full_name": full_name,  # ✅ nom complet affiché dans l’en-tête
        "avatar": avatar,        # ✅ photo de profil
    }

    return render(
        request,
        "ngo/dashboard/intermediaire/pages/action/entrepreneurs_list.html",
        context
    )


@login_required
@intermediaire_required
def intermediaire_entrepreneur_detail(request, entrepreneur_id):
    """Affiche les détails d’un entrepreneur représenté et ses projets."""
    entrepreneur = get_object_or_404(User, id=entrepreneur_id, role="entrepreneur")
    projects = Project.objects.filter(entrepreneur=entrepreneur)

    # 🔹 Informations de l’intermédiaire connecté
    profile = get_object_or_404(IntermediaireProfile, user=request.user)
    full_name = profile.get_full_name()
    avatar = profile.get_avatar_url()

    context = {
        "entrepreneur": entrepreneur,
        "projects": projects,
        "profile": profile,
        "full_name": full_name,  # ✅ pour l’en-tête
        "avatar": avatar,        # ✅ pour la photo de profil
    }

    return render(
        request,
        "ngo/dashboard/intermediaire/pages/action/entrepreneur_detail.html",
        context
    )

# --------------------------------------------
# l’intermédiaire se détache d’un entrepreneur
# --------------------------------------------
@login_required
@intermediaire_required
def retirer_entrepreneur(request, entrepreneur_id):
    """Permet à un intermédiaire de retirer un entrepreneur de sa liste de représentés."""
    profile = get_object_or_404(IntermediaireProfile, user=request.user)
    full_name = profile.get_full_name()
    avatar = profile.get_avatar_url()

    try:
        association = IntermediaireEntrepreneur.objects.get(
            intermediaire=request.user,
            entrepreneur_id=entrepreneur_id
        )
        association.delete()
        messages.success(request, "✅ Association supprimée avec succès.")
    except IntermediaireEntrepreneur.DoesNotExist:
        messages.error(request, "❌ Association introuvable.")

    context = {
        "profile": profile,
        "full_name": full_name,
        "avatar": avatar,
    }

    return redirect("intermediaire_entrepreneurs")



# --------------------------------------------------------
# Liste et détails des projets manager par l'intermediaire
# --------------------------------------------------------
@login_required
@intermediaire_required
def intermediaire_projects(request):
    """Affiche la liste des projets des entrepreneurs représentés par l'intermédiaire connecté."""
    profile = get_object_or_404(IntermediaireProfile, user=request.user)
    entrepreneurs = profile.get_entrepreneurs()
    projects = Project.objects.filter(entrepreneur__in=entrepreneurs).order_by("-created_at")

    # 🔹 Ajout des infos du profil intermédiaire
    full_name = profile.get_full_name()
    avatar = profile.get_avatar_url()

    context = {
        "profile": profile,
        "projects": projects,
        "full_name": full_name,  # ✅ Nom complet de l’intermédiaire
        "avatar": avatar,        # ✅ Photo de profil
    }

    return render(request, "ngo/dashboard/intermediaire/pages/projet/projects_list.html", context)


@login_required
@intermediaire_required
def intermediaire_project_detail(request, slug):
    """Affiche les détails d’un projet appartenant à un entrepreneur représenté par l’intermédiaire."""
    project = get_object_or_404(Project, slug=slug)
    campaigns = Campaign.objects.filter(project=project)
    loan_campaigns = LoanCampaign.objects.filter(project=project)

    # 🔹 Ajout du profil intermédiaire
    profile = get_object_or_404(IntermediaireProfile, user=request.user)
    full_name = profile.get_full_name()
    avatar = profile.get_avatar_url()

    context = {
        "profile": profile,
        "full_name": full_name,        # ✅ Nom complet de l’intermédiaire
        "avatar": avatar,              # ✅ Photo de profil
        "project": project,
        "campaigns": campaigns,
        "loan_campaigns": loan_campaigns,
    }

    return render(
        request,
        "ngo/dashboard/intermediaire/pages/projet/project_detail.html",
        context
    )

# -------------------------------
# Campagnes de financement
# -------------------------------
@login_required
@intermediaire_required
def intermediaire_campaigns(request):
    """Liste toutes les campagnes liées aux projets des entrepreneurs représentés par l’intermédiaire."""
    profile = get_object_or_404(IntermediaireProfile, user=request.user)
    entrepreneurs = profile.get_entrepreneurs()
    projects = Project.objects.filter(entrepreneur__in=entrepreneurs)
    campaigns = Campaign.objects.filter(project__in=projects).order_by("-created_at")

    # 🔹 Ajout du nom complet et de l’avatar
    full_name = profile.get_full_name()
    avatar = profile.get_avatar_url()

    context = {
        "profile": profile,
        "campaigns": campaigns,
        "full_name": full_name,  # ✅ Nom complet de l’intermédiaire
        "avatar": avatar,        # ✅ Photo de profil
    }

    return render(
        request,
        "ngo/dashboard/intermediaire/pages/campagne/campaigns_list.html",
        context
    )


@login_required
@intermediaire_required
def intermediaire_campaigns_detail(request, campaign_id):
    """Affiche les détails d’une campagne appartenant à un entrepreneur représenté par l’intermédiaire."""
    profile = get_object_or_404(IntermediaireProfile, user=request.user)
    entrepreneurs = profile.get_entrepreneurs()
    projects = Project.objects.filter(entrepreneur__in=entrepreneurs)

    # Vérifie que la campagne fait partie des projets représentés
    campaign = get_object_or_404(Campaign, id=campaign_id, project__in=projects)

    # Calculs et statistiques de base
    total_collected = campaign.collected_amount or 0
    goal_amount = campaign.goal_amount or 0
    completion_rate = (total_collected / goal_amount * 100) if goal_amount > 0 else 0

    # 🔹 Informations d'en-tête
    full_name = profile.get_full_name()
    avatar = profile.get_avatar_url()

    context = {
        "profile": profile,
        "campaign": campaign,
        "project": campaign.project,
        "entrepreneur": campaign.project.entrepreneur,
        "total_collected": total_collected,
        "goal_amount": goal_amount,
        "completion_rate": round(completion_rate, 2),
        "full_name": full_name,
        "avatar": avatar,
    }

    return render(
        request,
        "ngo/dashboard/intermediaire/pages/campagne/campaign_detail.html",
        context
    )


@login_required
@intermediaire_required
def intermediaire_loan_campaigns(request):
    """Liste toutes les campagnes de prêt liées aux projets des entrepreneurs représentés par l’intermédiaire."""
    profile = get_object_or_404(IntermediaireProfile, user=request.user)
    entrepreneurs = profile.get_entrepreneurs()
    projects = Project.objects.filter(entrepreneur__in=entrepreneurs)
    loan_campaigns = LoanCampaign.objects.filter(project__in=projects).order_by("-created_at")

    # 🔹 Ajout du nom complet et de la photo de profil
    full_name = profile.get_full_name()
    avatar = profile.get_avatar_url()

    context = {
        "profile": profile,
        "loan_campaigns": loan_campaigns,
        "full_name": full_name,  # ✅ Nom complet de l’intermédiaire
        "avatar": avatar,        # ✅ Photo de profil
    }

    return render(
        request,
        "ngo/dashboard/intermediaire/pages/campagne/loan_campaigns_list.html",
        context
    )


@login_required
@intermediaire_required
def intermediaire_loan_campaigns_detail(request, loan_campaign_id):
    """Affiche les détails d’une campagne de prêt liée à un entrepreneur représenté par l’intermédiaire."""
    profile = get_object_or_404(IntermediaireProfile, user=request.user)
    entrepreneurs = profile.get_entrepreneurs()
    projects = Project.objects.filter(entrepreneur__in=entrepreneurs)

    # Vérifie que la campagne de prêt appartient bien à un projet représenté
    loan_campaign = get_object_or_404(LoanCampaign, id=loan_campaign_id, project__in=projects)

    # Statistiques de la campagne
    total_collected = loan_campaign.collected_amount or 0
    goal_amount = loan_campaign.goal_amount or 0
    completion_rate = (total_collected / goal_amount * 100) if goal_amount > 0 else 0

    # 🔹 Informations d'en-tête
    full_name = profile.get_full_name()
    avatar = profile.get_avatar_url()

    context = {
        "profile": profile,
        "loan_campaign": loan_campaign,
        "project": loan_campaign.project,
        "entrepreneur": loan_campaign.project.entrepreneur,
        "total_collected": total_collected,
        "goal_amount": goal_amount,
        "completion_rate": round(completion_rate, 2),
        "full_name": full_name,
        "avatar": avatar,
    }

    return render(
        request,
        "ngo/dashboard/intermediaire/pages/campagne/loan_campaign_detail.html",
        context
    )


# -------------------------------
# Statistiques / Rapports
# -------------------------------
@login_required
@intermediaire_required
def intermediaire_reports(request):
    """Tableau des statistiques et rapports de performance de l’intermédiaire."""
    profile = get_object_or_404(IntermediaireProfile, user=request.user)
    entrepreneurs = profile.get_entrepreneurs()
    projects = Project.objects.filter(entrepreneur__in=entrepreneurs)

    # 🔹 Récupération des stats principales
    stats = {
        "total_projects": projects.count(),
        "total_collected": projects.aggregate(Sum("collected_amount"))["collected_amount__sum"] or 0,
        "active_campaigns": Campaign.objects.filter(project__in=projects, status="active").count(),
        "completed_campaigns": Campaign.objects.filter(project__in=projects, status="completed").count(),
        "failed_campaigns": Campaign.objects.filter(project__in=projects, status="failed").count(),
    }

    # 🔹 Nom complet + avatar (pour affichage global)
    full_name = profile.get_full_name()
    avatar = profile.get_avatar_url()

    context = {
        "profile": profile,
        "stats": stats,
        "full_name": full_name,
        "avatar": avatar,
    }

    return render(
        request,
        "ngo/dashboard/intermediaire/pages/stat/reports.html",
        context,
    )


@login_required
@intermediaire_required
def intermediaire_reports_detail(request, project_id):
    """Affiche le rapport détaillé d’un projet représenté par l’intermédiaire."""
    profile = get_object_or_404(IntermediaireProfile, user=request.user)
    entrepreneurs = profile.get_entrepreneurs()

    # Vérification que le projet appartient bien à un entrepreneur représenté
    project = get_object_or_404(Project, id=project_id, entrepreneur__in=entrepreneurs)

    # Campagnes associées
    campaigns = Campaign.objects.filter(project=project)
    loan_campaigns = LoanCampaign.objects.filter(project=project)

    # Statistiques détaillées
    total_collected = campaigns.aggregate(Sum("collected_amount"))["collected_amount__sum"] or 0
    total_goal = campaigns.aggregate(Sum("goal_amount"))["goal_amount__sum"] or 0
    completion_rate = (total_collected / total_goal * 100) if total_goal > 0 else 0

    stats = {
        "total_campaigns": campaigns.count(),
        "loan_campaigns": loan_campaigns.count(),
        "total_goal": total_goal,
        "total_collected": total_collected,
        "completion_rate": round(completion_rate, 2),
        "active": campaigns.filter(status="active").count(),
        "completed": campaigns.filter(status="completed").count(),
        "failed": campaigns.filter(status="failed").count(),
    }

    # Infos de profil (pour en-tête)
    full_name = profile.get_full_name()
    avatar = profile.get_avatar_url()

    context = {
        "profile": profile,
        "full_name": full_name,
        "avatar": avatar,
        "project": project,
        "campaigns": campaigns,
        "loan_campaigns": loan_campaigns,
        "stats": stats,
    }

    return render(
        request,
        "ngo/dashboard/intermediaire/pages/stat/reports_detail.html",
        context,
    )



@login_required
@intermediaire_required
def intermediaire_project_delete(request, project_id):
    """Permet à l’intermédiaire de supprimer un projet représenté."""
    profile = get_object_or_404(IntermediaireProfile, user=request.user)
    project = get_object_or_404(Project, id=project_id, entrepreneur__in=profile.get_entrepreneurs())

    # Supprimer toutes les campagnes liées au projet
    Campaign.objects.filter(project=project).delete()
    LoanCampaign.objects.filter(project=project).delete()

    project.delete()
    messages.success(request, _("✅ Projet et toutes ses campagnes supprimés avec succès."))
    return redirect("intermediaire_reports")

@login_required
@intermediaire_required
def intermediaire_project_complete(request, project_id):
    """Permet à l’intermédiaire de marquer un projet comme terminé."""
    profile = get_object_or_404(IntermediaireProfile, user=request.user)
    project = get_object_or_404(Project, id=project_id, entrepreneur__in=profile.get_entrepreneurs())

    # Mettre à jour le statut de toutes les campagnes liées
    Campaign.objects.filter(project=project, status="active").update(status="completed")
    LoanCampaign.objects.filter(project=project, status="active").update(status="completed")

    project.status = "completed"
    project.save(update_fields=["status"])

    messages.success(request, _("✅ Projet marqué comme terminé avec succès."))
    return redirect("intermediaire_reports")

# -------------------------------
# Contribution
# -------------------------------
@login_required
@intermediaire_required
def intermediaire_contributions_list(request):
    """Liste toutes les contributions liées aux campagnes et campagnes de prêt des entrepreneurs représentés par l’intermédiaire."""
    profile = get_object_or_404(IntermediaireProfile, user=request.user)

    # 🔹 Entrepreneurs représentés par cet intermédiaire
    entrepreneurs = profile.get_entrepreneurs()

    # 🔹 Tous les projets appartenant à ces entrepreneurs
    projects = Project.objects.filter(entrepreneur__in=entrepreneurs)

    # 🔹 Récupère toutes les contributions liées aux campagnes et campagnes de prêt de ces projets
    contributions = Contribution.objects.filter(
        Q(campaign__project__in=projects) | Q(loan_campaign__project__in=projects)
    ).select_related("investor", "campaign", "loan_campaign").order_by("-created_at")

    # 🔹 Informations profil
    full_name = profile.get_full_name()
    avatar = profile.get_avatar_url()

    context = {
        "profile": profile,
        "contributions": contributions,
        "full_name": full_name,
        "avatar": avatar,
    }

    return render(
        request,
        "ngo/dashboard/intermediaire/pages/contribution/contributions_list.html",
        context
    )



@login_required
@intermediaire_required
def intermediaire_contribution_detail(request, contribution_id):
    """Affiche les détails d’une contribution (don ou prêt) pour l’intermédiaire."""
    profile = get_object_or_404(IntermediaireProfile, user=request.user)
    contribution = get_object_or_404(Contribution, id=contribution_id)

    # ✅ Vérifie que cette contribution appartient à un projet représenté par cet intermédiaire
    entrepreneurs = profile.get_entrepreneurs()
    projects = Project.objects.filter(entrepreneur__in=entrepreneurs)

    if not (contribution.project in projects):
        messages.error(request, "⛔ Vous n’avez pas accès à cette contribution.")
        return redirect("intermediaire_contributions_list")

    # 🔹 Informations complémentaires
    project = contribution.project
    campaign = contribution.campaign or contribution.loan_campaign
    investor = contribution.investor

    full_name = profile.get_full_name()
    avatar = profile.get_avatar_url()

    context = {
        "profile": profile,
        "contribution": contribution,
        "project": project,
        "campaign": campaign,
        "investor": investor,
        "full_name": full_name,
        "avatar": avatar,
    }

    return render(
        request,
        "ngo/dashboard/intermediaire/pages/contribution/contribution_detail.html",
        context
    )



@login_required
@intermediaire_required
def intermediaire_contribution_delete(request, contribution_id):
    """
    Permet à un intermédiaire de supprimer une contribution (don ou prêt)
    liée à un projet qu'il représente.
    """
    profile = get_object_or_404(IntermediaireProfile, user=request.user)
    contribution = get_object_or_404(Contribution, id=contribution_id)

    # Vérifie que la contribution appartient bien à un projet représenté
    entrepreneurs = profile.get_entrepreneurs()
    projects = Project.objects.filter(entrepreneur__in=entrepreneurs)

    if contribution.project not in projects:
        messages.error(request, _("⛔ Vous n’avez pas l’autorisation de supprimer cette contribution."))
        return redirect("intermediaire_contributions_list")

    contribution.delete()
    messages.success(request, _("✅ Contribution supprimée avec succès."))
    return redirect("intermediaire_contributions_list")