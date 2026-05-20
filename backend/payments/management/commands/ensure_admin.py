import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Create or reset the default Django admin user for the active database."

    def add_arguments(self, parser):
        parser.add_argument("--username", default=os.environ.get("DJANGO_ADMIN_USERNAME", "demo"))
        parser.add_argument("--password", default=os.environ.get("DJANGO_ADMIN_PASSWORD", "DEMO@12"))
        parser.add_argument("--email", default=os.environ.get("DJANGO_ADMIN_EMAIL", "demo@example.com"))

    def handle(self, *args, **options):
        username = options["username"]
        password = options["password"]
        email = options["email"]

        User = get_user_model()
        user, created = User.objects.get_or_create(username=username, defaults={"email": email})
        user.email = user.email or email
        user.is_active = True
        user.is_staff = True
        user.is_superuser = True
        user.set_password(password)
        user.save()

        action = "Created" if created else "Updated"
        self.stdout.write(self.style.SUCCESS(f"{action} admin user '{username}' for the active database."))
