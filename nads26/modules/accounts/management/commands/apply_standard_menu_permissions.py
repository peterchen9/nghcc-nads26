from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from modules.accounts.models import UserProfile
from modules.menu.permissions import (
    STANDARD_USER_MENU_ROUTES,
    standard_user_menu_items,
)


class Command(BaseCommand):
    help = 'Apply the standard menu whitelist to every non-superuser account.'

    def handle(self, *args, **options):
        menu_items = list(standard_user_menu_items().order_by('id'))
        found_routes = {item.route for item in menu_items}
        missing_routes = [
            route for route in STANDARD_USER_MENU_ROUTES
            if route not in found_routes
        ]
        if missing_routes:
            raise CommandError(
                'Missing active menu routes: ' + ', '.join(missing_routes)
            )

        users = list(User.objects.filter(is_superuser=False).order_by('id'))
        with transaction.atomic():
            for user in users:
                profile, _ = UserProfile.objects.get_or_create(
                    user=user,
                    defaults={'worker_ename': user.username},
                )
                profile.allowed_menu_items.set(menu_items)

        self.stdout.write(
            self.style.SUCCESS(
                f'Applied {len(menu_items)} menu permissions to '
                f'{len(users)} non-superuser accounts.'
            )
        )
