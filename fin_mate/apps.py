from django.apps import AppConfig


class FinMateConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "fin_mate"

    def ready(self):
        import fin_mate.signals
