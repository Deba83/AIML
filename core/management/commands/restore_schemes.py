from django.core.management.base import BaseCommand
from core.services.undo_service import restore_schemes

class Command(BaseCommand):
    help = "Restore all schemes from a JSON backup file."

    def add_arguments(self, parser):
        parser.add_argument('filepath', type=str, help="Path to the JSON backup file.")

    def handle(self, *args, **options):
        filepath = options['filepath']
        try:
            restore_schemes(filepath)
            self.stdout.write(self.style.SUCCESS(f"Successfully restored schemes from {filepath}"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Failed to restore schemes: {str(e)}"))
