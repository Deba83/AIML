from django.core.management.base import BaseCommand
from core.services.undo_service import backup_schemes

class Command(BaseCommand):
    help = "Backup all schemes to a JSON file."

    def handle(self, *args, **options):
        filepath = backup_schemes()
        self.stdout.write(self.style.SUCCESS(f"Successfully backed up schemes to {filepath}"))
