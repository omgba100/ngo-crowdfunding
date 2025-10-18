from celery import shared_task
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings

@shared_task
def notify_inactive_entrepreneurs():
    from users.models import User
    inactive_users = User.objects.filter(is_entrepreneur=True, is_active=False)
    for user in inactive_users:
        send_mail(
            "Votre compte est désactivé",
            "Bonjour, votre compte a été désactivé pour inactivité prolongée.",
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=True,
        )
    return f"{inactive_users.count()} notifications envoyées."


