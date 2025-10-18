from django.apps import AppConfig


class NgoConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'ngo'

    def ready(self):
        import ngo.signals
