from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import User, EntrepreneurProfile, InvestisseurProfile, IntermediaireProfile

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Crée automatiquement le profil correspondant à l'utilisateur selon son rôle.
    """
    if created:
        if instance.role == "entrepreneur":
            EntrepreneurProfile.objects.get_or_create(user=instance)
        elif instance.role == "investisseur":
            InvestisseurProfile.objects.get_or_create(user=instance,defaults={"capital_available": 0, "company": ""})
        elif instance.role == "intermediaire":
            IntermediaireProfile.objects.get_or_create(user=instance)

