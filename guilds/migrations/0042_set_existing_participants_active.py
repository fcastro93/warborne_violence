# Generated manually

from django.db import migrations


def set_existing_participants_active(apps, schema_editor):
    """Set all existing participants as active"""
    EventParticipant = apps.get_model('guilds', 'EventParticipant')
    EventParticipant.objects.all().update(is_active=True)


def reverse_set_existing_participants_active(apps, schema_editor):
    """Reverse migration - set all participants as inactive"""
    EventParticipant = apps.get_model('guilds', 'EventParticipant')
    EventParticipant.objects.all().update(is_active=False)


class Migration(migrations.Migration):

    dependencies = [
        ('guilds', '0041_eventparticipant_is_active'),
    ]

    operations = [
        migrations.RunPython(
            set_existing_participants_active,
            reverse_set_existing_participants_active
        ),
    ]
