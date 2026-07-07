from django.apps import AppConfig


class MainConfig(AppConfig):
    name = 'main'

    def ready(self):
        # Signallarni ro'yxatdan o'tkazamiz — import qilinmasa @receiver ishlamaydi
        from . import signals  # noqa: F401
