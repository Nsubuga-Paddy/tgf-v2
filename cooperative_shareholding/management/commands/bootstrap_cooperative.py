from django.core.management.base import BaseCommand

from accounts.models import Project
from cooperative_shareholding.models import CooperativeGlobalDefaults
from cooperative_shareholding.services import PROJECT_NAME


class Command(BaseCommand):
    help = "Create Cooperative Shareholding project and default settings."

    def handle(self, *args, **options):
        CooperativeGlobalDefaults.get_solo()
        self.stdout.write(self.style.SUCCESS("Cooperative global defaults ready."))
        Project.objects.get_or_create(
            name=PROJECT_NAME,
            defaults={
                "description": "MCS Cooperative (SACCO) shareholding — separate from MESU Academy.",
            },
        )
        self.stdout.write(self.style.SUCCESS(f'Project "{PROJECT_NAME}" ready.'))
