# offers/management/commands/process_pending_verifications.py
from django.core.management.base import BaseCommand
from offers.utils import process_pending_verifications

class Command(BaseCommand):
    help = 'Process pending mobile number verifications when free tier is available'

    def handle(self, *args, **options):
        self.stdout.write("Processing pending verifications...")
        process_pending_verifications()
        self.stdout.write(self.style.SUCCESS("Done!"))