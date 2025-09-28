"""
Django management command to set up S3 folder structure
"""
from django.core.management.base import BaseCommand
from django.conf import settings
from warborne_tools.s3_utils import s3_manager

class Command(BaseCommand):
    help = 'Set up S3 folder structure with dev/ and prod/ folders'

    def add_arguments(self, parser):
        parser.add_argument(
            '--bucket-name',
            type=str,
            help='S3 bucket name (overrides settings)',
        )
        parser.add_argument(
            '--create-placeholders',
            action='store_true',
            help='Create placeholder files to establish folder structure',
        )

    def handle(self, *args, **options):
        bucket_name = options.get('bucket_name') or settings.AWS_STORAGE_BUCKET_NAME
        
        if not bucket_name:
            self.stdout.write(
                self.style.ERROR('No S3 bucket name provided. Set AWS_STORAGE_BUCKET_NAME in settings or use --bucket-name')
            )
            return
        
        self.stdout.write(f'Setting up S3 structure for bucket: {bucket_name}')
        
        # Update bucket name in s3_manager if provided via command line
        if options.get('bucket_name'):
            s3_manager.bucket_name = bucket_name
        
        try:
            # Test S3 connection
            s3_manager.s3_client.head_bucket(Bucket=bucket_name)
            self.stdout.write(
                self.style.SUCCESS(f'Successfully connected to S3 bucket: {bucket_name}')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Failed to connect to S3 bucket {bucket_name}: {e}')
            )
            return
        
        # Create folder structure
        if options.get('create_placeholders'):
            self.stdout.write('Creating folder structure with placeholder files...')
            success = s3_manager.create_folder_structure()
            
            if success:
                self.stdout.write(
                    self.style.SUCCESS('Successfully created S3 folder structure!')
                )
                self.stdout.write('Folder structure:')
                self.stdout.write('  - dev/images/')
                self.stdout.write('  - prod/images/')
            else:
                self.stdout.write(
                    self.style.ERROR('Failed to create S3 folder structure')
                )
        else:
            self.stdout.write('S3 folder structure will be created automatically when first file is uploaded.')
            self.stdout.write('Use --create-placeholders to create the structure now.')
        
        # Display current environment
        self.stdout.write(f'Current environment: {settings.ENVIRONMENT}')
        self.stdout.write(f'Images folder: {settings.S3_IMAGES_FOLDER}')
        
        # List existing images if any
        existing_images = s3_manager.list_images()
        if existing_images:
            self.stdout.write(f'Existing images in {settings.S3_IMAGES_FOLDER}:')
            for image in existing_images[:10]:  # Show first 10
                self.stdout.write(f'  - {image}')
            if len(existing_images) > 10:
                self.stdout.write(f'  ... and {len(existing_images) - 10} more')
        else:
            self.stdout.write('No existing images found.')
