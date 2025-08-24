from django.apps import AppConfig


class Savings52WeeksConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'savings_52_weeks'
    
    def ready(self):
        """Import signals when the app is ready"""
        import savings_52_weeks.signals
