from django.core.management.base import BaseCommand, CommandError
from accounts.models import User


class Command(BaseCommand):
    help = "Safely promotes an existing user to Platform Admin or creates a Platform Admin account."

    def add_arguments(self, parser):
        parser.add_argument('username', type=str, help="Username of the user to promote to Platform Admin")

    def handle(self, *args, **options):
        username = options['username'].strip()
        try:
            user = User.objects.get(username__iexact=username)
        except User.DoesNotExist:
            raise CommandError(f"User with username '{username}' does not exist.")

        user.role = User.ROLE_ADMIN
        user.is_staff = True
        user.is_superuser = True
        user.save(update_fields=['role', 'is_staff', 'is_superuser'])

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully promoted '{user.username}' ({user.display_name}) to Platform Admin (role=ADMIN, is_staff=True, is_superuser=True)."
            )
        )

