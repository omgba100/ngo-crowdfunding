from django.urls import path, include, reverse_lazy
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from . import admin_views
from .views import (
    EntrepreneurPasswordResetView,
    InvestisseurPasswordResetView,
    IntermediairePasswordResetView,
    UniversalPasswordResetView,
    user_logout,notification_detail_entrepreneur,
)
from . import views


urlpatterns = [
    path('login/redirect/', views.login_redirect, name='login_redirect'),
    path('admin/message/<int:pk>/reply/', admin_views.admin_reply_message, name='admin_reply_message'),
    # Accueil
    path('', views.home, name='home'),

    # Dashboards
    path('dashboard/', login_required(views.dashboard), name='dashboard'),
    path("dashboard/entrepreneur/", views.dashboard_entrepreneur, name="dashboard_entrepreneur"),
    path("dashboard/investisseur/", views.dashboard_investisseur, name="dashboard_investisseur"),
    path("dashboard/intermediaire/", views.dashboard_intermediaire, name="dashboard_intermediaire"),

    #About-us
    path("about-us/", views.about_us, name="about_us"),
    path("que-faisons-nous/", views.que_faisons_nous, name="que_faisons_nous"),
    path('agrement-securite/', views.agrement_securite, name='agrement_securite'),
    path('financement-igia/', views.financement_igia, name='financement_igia'),
    path('guide-utilisation/', views.guide_utilisation, name='guide_utilisation'),
    path("mentions-legales/", views.mentions_legales, name="mentions_legales"),
    path("confidentialite/", views.confidentialite, name="confidentialite"),
    path("reclamations/", views.reclamations, name="reclamations"),
    path("conditions-generales-utilisation/", views.conditions_generales_utilisation, name="conditions_generales_utilisation"),
    path("donnees-personnelles/",views.donnees_personnelles,name="donnees_personnelles"),
    path("actualites/", views.actualite_list, name="actualite_list"),

    #Categorie
    path("categories/", views.category_list, name="category_list"),
    path("categories/<slug:slug>/", views.category_detail, name="category_detail"),

    # Projects
    path("projets/nouveau/", views.project_create, name="project_create"),  # avant <slug>
    path("projets/", views.project_list, name="project_list"),
    path("projets/<slug:slug>/modifier/", views.project_update, name="project_update"),
    path("projets/<slug:slug>/supprimer/", views.project_delete, name="project_delete"),
    path("projets/<slug:slug>/", views.project_detail, name="project_detail"),  # toujours en dernier

    # Campaigns
    path("campaigns/", views.campaign_list, name="campaign_list"),
    path("campaigns/<int:pk>/", views.campaign_detail, name="campaign_detail"),

    #loan
    path("campaigns/loan", views.loan_campaign_list, name="campaign_liste"),
    path("campaigns/loan/<int:pk>/", views.loan_campaign_detail, name="loan_campaign_detail"),

    # Contributions
    path("campaigns/<int:campaign_id>/contributions/", views.contribution_list, name="contribution_list"),

    # Partners
    path("partners/", views.partner_list, name="partner_list"),

    # Representativite
    path('countries/', views.country_list, name='country_list'),
    path("countries/<slug:slug>/", views.country_detail, name="country_detail"),
    path("country/<slug:country_slug>/categories-financees/", views.funded_categories_for_country, name="funded_categories_for_country"),
    path("country/<slug:country_slug>/category/<slug:category_slug>/projects/", views.projects_by_category, name="projects_by_category"),

    # Team
    path("team/", views.team_list, name="team_list"),

    # Testimonials
    path("testimonials/", views.testimonial_list, name="testimonial_list"),

    # Contact
    path("contact/", views.contact, name="contact"),

    #Register
    path("register/entrepreneur/", views.register_entrepreneur, name="register_entrepreneur"),
    path("register/investisseur/", views.register_investisseur, name="register_investisseur"),
    path("register/intermediaire/", views.register_intermediaire, name="register_intermediaire"),

    #Login
    path("login/entrepreneur/", views.login_entrepreneur, name="login_entrepreneur"),
    path("login/investisseur/", views.login_investisseur, name="login_investisseur"),
    path("login/intermediaire/", views.login_intermediaire, name="login_intermediaire"),

    #Logout
    path("logout/", user_logout, name="logout"),

    

    # ==========================================================================
    # 🔹 ENTREPRENEUR PASSWORD RESET
    # ==========================================================================
    path("entrepreneur/password_reset/",EntrepreneurPasswordResetView.as_view(),name="entrepreneur_password_reset",),
    path("entrepreneur/password_reset_done/",auth_views.PasswordResetDoneView.as_view(template_name="ngo/auth/1/password_reset_done.html"),name="entrepreneur_password_reset_done",),
    path("entrepreneur/reset/<uidb64>/<token>/",auth_views.PasswordResetConfirmView.as_view(template_name="ngo/auth/1/password_reset_confirm.html",success_url=reverse_lazy("entrepreneur_password_reset_complete"),),name="entrepreneur_password_reset_confirm",),
    path("entrepreneur/reset/done/",auth_views.PasswordResetCompleteView.as_view(template_name="ngo/auth/1/password_reset_complete.html"),name="entrepreneur_password_reset_complete",),

    # ==========================================================================
    # 🔹 INVESTISSEUR PASSWORD RESET
    # ==========================================================================
    path("investisseur/password_reset/",InvestisseurPasswordResetView.as_view(),name="investisseur_password_reset",),
    path("investisseur/password_reset_done/",auth_views.PasswordResetDoneView.as_view(template_name="ngo/auth/2/password_reset_done.html"),name="investisseur_password_reset_done",),
    path("investisseur/reset/<uidb64>/<token>/",auth_views.PasswordResetConfirmView.as_view(template_name="ngo/auth/2/password_reset_confirm.html",success_url=reverse_lazy("investisseur_password_reset_complete"),),name="investisseur_password_reset_confirm",),
    path("investisseur/reset/done/",auth_views.PasswordResetCompleteView.as_view(template_name="ngo/auth/2/password_reset_complete.html"),name="investisseur_password_reset_complete",),

    # ==========================================================================
    # 🔹 INTERMEDIAIRE PASSWORD RESET
    # ==========================================================================
    path("intermediaire/password_reset/",IntermediairePasswordResetView.as_view(),name="intermediaire_password_reset",),
    path("intermediaire/password_reset_done/",auth_views.PasswordResetDoneView.as_view(template_name="ngo/auth/3/password_reset_done.html"),name="intermediaire_password_reset_done",),
    path("intermediaire/reset/<uidb64>/<token>/",auth_views.PasswordResetConfirmView.as_view(template_name="ngo/auth/3/password_reset_confirm.html",success_url=reverse_lazy("intermediaire_password_reset_complete"),),name="intermediaire_password_reset_confirm",),
    path("intermediaire/reset/done/",auth_views.PasswordResetCompleteView.as_view(template_name="ngo/auth/3/password_reset_complete.html"),name="intermediaire_password_reset_complete",),

    # ==========================================================================
    # 🔹 GENERIC / COMMUN PASSWORD RESET (admin ou global)
    # ==========================================================================
    path("password_reset/", UniversalPasswordResetView.as_view(), name="password_reset"),
    path("password_reset_done/", auth_views.PasswordResetDoneView.as_view(template_name="ngo/auth/universal/password_reset_done.html"), name="password_reset_done"),
    path("reset/<uidb64>/<token>/", auth_views.PasswordResetConfirmView.as_view(template_name="ngo/auth/universal/password_reset_confirm.html",success_url=reverse_lazy("password_reset_complete")), name="password_reset_confirm"),
    path("reset/done/", auth_views.PasswordResetCompleteView.as_view(template_name="ngo/auth/universal/password_reset_complete.html"), name="password_reset_complete"),

    #Message
    path('inbox/entrepreneur/', views.inbox_entrepreneur, name='inbox_entrepreneur'),
    path('inbox/investisseur/', views.inbox_investisseur, name='inbox_investisseur'),
    path('inbox/intermediaire/', views.inbox_intermediaire, name='inbox_intermediaire'),

    path('message/<int:message_id>/', views.message_detail, name='message_detail'),
    path('message/send/', views.send_message, name='send_message'),
    path('message/<int:pk>/reply/', views.reply_message, name='reply_message'),
    path('message/<int:pk>/archive/', views.archive_message, name='archive_message'),
    path('message/<int:pk>/delete/', views.delete_message, name='delete_message'),

    #Notifications
    path('dashboard/entrepreneur/notifications/',views.notification_entrepreneur,name='notification_entrepreneur'),
    path('notifications/entrepreneur/<int:pk>/', notification_detail_entrepreneur, name='notification_detail'),
    path("dashboard/investisseur/notifications/",views.notification_investisseur,name="notification_investisseur"),
    path('inbox/notification/<int:pk>/',views.notification_detail_investisseur,name='notification_detail_investisseur'),
    path("dashboard/investisseur/notifications/<int:pk>/",views.notification_detail_investisseur,name="notification_detail_investisseur"),
    path('dashboard/intermediaire/notifications/',views.notification_intermediaire,name='notification_intermediaire'),
    path("dashboard/intermediaire/notifications/<int:pk>/",views.intermediaire_notifications_detail,name="intermediaire_notifications_detail"),
    path("dashboard/intermediaire/notifications/<int:pk>/delete/",views.intermediaire_notification_delete,name="intermediaire_notification_delete",),

    #Entrepreneur action
    path("entrepreneur/delete-account/", views.entrepreneur_delete_account, name="ent_delete_account"),
    path("entrepreneur/profile/deactivate/", views.entrepreneur_deactivate_account, name="ent_deactivate_account"),
    path("entrepreneur/profile/update/",views.update_entrepreneur_profile,name="update_entrepreneur_profile"),
    path('entrepreneur/profile/', views.entrepreneur_profile_view, name='entrepreneur_profile'),
    path("dashboard/entrepreneur/projets/<slug:slug>/contributions/",views.project_contributions,name="project_contributions"),
    path("dashboard/entrepreneur/projets/<int:project_id>/retrait/",views.request_withdrawal,name="request_withdrawal"),
    path("dashboard/entrepreneur/projets/<int:project_id>/valider/",views.validate_project,name="validate_project"),
    path("dashboard/entrepreneur/projets/",views.entrepreneur_project_list,name="entrepreneur_project_list" ),

    # 🔹 Investisseur action
    path("dashboard/investisseur/projets-disponibles/",views.projects_available_investisseur,name="projects_available_investisseur",),
    path("dashboard/investisseur/projet/<slug:slug>/",views.project_detail_investisseur,name="project_detail_investisseur",),
    path("dashboard/investisseur/contributions/",views.contributions_list_investisseur,name="contributions_list_investisseur",),
    path("dashboard/investisseur/contribution/<int:pk>/",views.contribution_detail_investisseur,name="contribution_detail_investisseur",),
    path("dashboard/investisseur/loan-campaigns/",views.loan_campaigns_list_investisseur,name="loan_campaigns_list_investisseur",),
    path("dashboard/investisseur/loan-campaign/<int:pk>/",views.loan_campaign_detail_investisseur,name="loan_campaign_detail_investisseur",),
    path("dashboard/investisseur/profile/",views.profile_investisseur,name="profile_investisseur",),
    path("dashboard/investisseur/profile/edit/",views.edit_investisseur_profile,name="edit_investisseur_profile",),
    path("dashboard/investisseur/profile/deactivate/",views.deactivate_investisseur,name="deactivate_investisseur",),
    path("dashboard/investisseur/profile/delete/",views.delete_account_investisseur,name="delete_account_investisseur",),

    # 🔹 Intermediaire action
    path("profile/",views.intermediaire_profile,name="intermediaire_profile"),
    path("profil/modifier/", views.edit_intermediaire_profile, name="edit_intermediaire_profile"),
    path("profil/desactiver/", views.desactiver_compte_intermediaire, name="desactiver_compte_intermediaire"),
    path("profil/supprimer/", views.supprimer_compte_intermediaire, name="supprimer_compte_intermediaire"),
    #paiement intermediaire
    # 1️- Vue combinée : afficher les paiements + soumettre un paiement
    path('intermediaire/payment/',views.intermediaire_payment,name='intermediaire_payment'),

    # 2️- Liste des paiements (séparée si besoin)
    path('intermediaire/payments/',views.intermediaire_payments,name='intermediaire_payments'),

    # 3️- Upload d’une preuve de paiement
    path('intermediaire/payment/upload/',views.intermediaire_payment_upload,name='intermediaire_payment_upload'),

    # 4️- Suppression d’un paiement (optionnel)
    path('intermediaire/payment/delete/<int:pk>/',views.delete_intermediaire_payment,name='intermediaire_payment_delete'),

    # action intermediaire
    path('dashboard/intermediaire/entrepreneurs/', views.intermediaire_entrepreneurs, name='intermediaire_entrepreneurs'),
    path("dashboard/intermediaire/entrepreneur/<int:entrepreneur_id>/",views.intermediaire_entrepreneur_detail,name="intermediaire_entrepreneur_detail",),
    path("entrepreneur/create/",views.intermediaire_create_entrepreneur,name="intermediaire_create_entrepreneur"),
    path('dashboard/intermediaire/entrepreneurs/add/',views.intermediaire_add_entrepreneur, name='intermediaire_add_entrepreneur'),
    path('dashboard/intermediaire/entrepreneurs/retirer/<int:entrepreneur_id>/',views.retirer_entrepreneur,name='retirer_entrepreneur'),
    path('dashboard/intermediaire/projects/', views.intermediaire_projects, name='intermediaire_projects'),
    path("dashboard/intermediaire/project/<slug:slug>/",views.intermediaire_project_detail,name="intermediaire_project_detail"),
    path('dashboard/intermediaire/campaigns/',views.intermediaire_campaigns,name='intermediaire_campaigns'),
    path('dashboard/intermediaire/campaign/<int:campaign_id>/',views.intermediaire_campaigns_detail,name='intermediaire_campaign_detail'),
    path('dashboard/intermediaire/campaigns/loan/', views.intermediaire_loan_campaigns, name='intermediaire_loan_campaigns'),
    path('dashboard/intermediaire/loan-campaign/<int:loan_campaign_id>/',views.intermediaire_loan_campaigns_detail,name='intermediaire_loan_campaign_detail'),
    path('dashboard/intermediaire/reports/', views.intermediaire_reports, name='intermediaire_reports'),
    path('dashboard/intermediaire/reports/<int:project_id>/', views.intermediaire_reports_detail, name='intermediaire_reports_detail'),
    path('dashboard/intermediaire/projects/<int:project_id>/delete/', views.intermediaire_project_delete, name='intermediaire_project_delete'),
    path('dashboard/intermediaire/projects/<int:project_id>/complete/', views.intermediaire_project_complete, name='intermediaire_project_complete'),
    path('dashboard/intermediaire/contributions/',views.intermediaire_contributions_list,name='intermediaire_contributions_list'),
    path('dashboard/intermediaire/contributions/<int:contribution_id>/',views.intermediaire_contribution_detail,name='intermediaire_contribution_detail'),
    path('dashboard/intermediaire/contributions/<int:contribution_id>/delete/',views.intermediaire_contribution_delete,name='intermediaire_contribution_delete'),
    
]
