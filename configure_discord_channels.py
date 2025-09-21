#!/usr/bin/env python
"""
Script para configurar los canales de Discord para el sistema de eventos
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'warborne_tools.settings_production')
django.setup()

from guilds.models import DiscordBotConfig

def configure_channels():
    """Configure Discord channel IDs for the event system"""
    
    print("🔧 Configurando canales de Discord para el sistema de eventos...")
    print()
    print("Necesitas configurar los siguientes canales:")
    print("1. Canal para comandos del bot (violence-bot)")
    print("2. Canal para anuncios de eventos (event-announcements)")
    print()
    
    # Get current config
    config = DiscordBotConfig.objects.first()
    if not config:
        print("❌ No se encontró configuración del bot. Por favor crea una en Django admin primero.")
        return
    
    print("📋 Instrucciones:")
    print("1. Ve a Discord y haz clic derecho en el canal 'violence-bot'")
    print("2. Selecciona 'Copy Channel ID'")
    print("3. Pega el ID aquí")
    print()
    
    # Get command channel ID
    command_channel_id = input("📝 ID del canal 'violence-bot' (o presiona Enter para omitir): ").strip()
    
    if command_channel_id:
        try:
            command_channel_id = int(command_channel_id)
            print(f"✅ Canal de comandos configurado: {command_channel_id}")
        except ValueError:
            print("❌ ID de canal inválido. Debe ser un número.")
            return
    
    print()
    print("📋 Ahora configura el canal de anuncios:")
    print("1. Ve a Discord y haz clic derecho en el canal 'event-announcements'")
    print("2. Selecciona 'Copy Channel ID'")
    print("3. Pega el ID aquí")
    print()
    
    # Get announcements channel ID
    announcements_channel_id = input("📝 ID del canal 'event-announcements' (o presiona Enter para omitir): ").strip()
    
    if announcements_channel_id:
        try:
            announcements_channel_id = int(announcements_channel_id)
            print(f"✅ Canal de anuncios configurado: {announcements_channel_id}")
        except ValueError:
            print("❌ ID de canal inválido. Debe ser un número.")
            return
    
    print()
    print("🔧 Configuración completada!")
    print()
    print("📝 Para usar estos canales, actualiza el archivo 'guilds/discord_bot.py':")
    print(f"   - Línea 117: Cambia '1234567890123456789' por '{announcements_channel_id}'")
    print()
    print("🚀 Comandos disponibles:")
    print("   - /createevent - Crear un nuevo evento")
    print("   - !createplayer [nombre] - Crear jugador")
    print("   - !myplayer - Ver tu jugador")
    print("   - !buildplayer <nombre> - Ver loadout de jugador")
    print("   - !guildinfo - Información de guilds")
    print("   - !ping - Probar bot")
    print()

if __name__ == "__main__":
    configure_channels()
