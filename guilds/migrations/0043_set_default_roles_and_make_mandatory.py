# Generated manually

from django.db import migrations


def set_default_roles_for_null_players(apps, schema_editor):
    """Set a default role for players with null game_role"""
    Player = apps.get_model('guilds', 'Player')
    
    # Set 'ranged_dps' as default for players with null game_role
    Player.objects.filter(game_role__isnull=True).update(game_role='ranged_dps')


def reverse_set_default_roles(apps, schema_editor):
    """Reverse migration - set game_role back to null"""
    Player = apps.get_model('guilds', 'Player')
    
    # Set players with 'ranged_dps' back to null (this is not perfect but acceptable)
    Player.objects.filter(game_role='ranged_dps').update(game_role=None)


class Migration(migrations.Migration):

    dependencies = [
        ('guilds', '0042_set_existing_participants_active'),
    ]

    operations = [
        migrations.RunPython(
            set_default_roles_for_null_players,
            reverse_set_default_roles
        ),
    ]
