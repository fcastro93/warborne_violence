from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.db import transaction

class Command(BaseCommand):
    help = 'Create a default admin user for the guild system'

    def add_arguments(self, parser):
        parser.add_argument(
            '--username',
            type=str,
            default='admin',
            help='Username for the admin user (default: admin)'
        )
        parser.add_argument(
            '--password',
            type=str,
            default='admin',
            help='Password for the admin user (default: admin)'
        )
        parser.add_argument(
            '--email',
            type=str,
            default='admin@violenceguild.com',
            help='Email for the admin user (default: admin@violenceguild.com)'
        )

    def handle(self, *args, **options):
        username = options['username']
        password = options['password']
        email = options['email']

        try:
            with transaction.atomic():
                # Check if user already exists
                if User.objects.filter(username=username).exists():
                    self.stdout.write(
                        self.style.WARNING(f'User "{username}" already exists. Skipping creation.')
                    )
                    return

                # Create the admin user
                user = User.objects.create_user(
                    username=username,
                    password=password,
                    email=email,
                    is_staff=True,
                    is_superuser=True,
                    first_name='Admin',
                    last_name='User'
                )

                self.stdout.write(
                    self.style.SUCCESS(
                        f'Successfully created admin user "{username}" with email "{email}"'
                    )
                )
                self.stdout.write(
                    self.style.SUCCESS(
                        f'You can now log in with username: {username} and password: {password}'
                    )
                )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error creating admin user: {str(e)}')
            )
