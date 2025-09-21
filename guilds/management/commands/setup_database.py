from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.db import connection
import os


class Command(BaseCommand):
    help = 'Configura la base de datos PostgreSQL para Warborne Tools'

    def handle(self, *args, **options):
        self.stdout.write('Configurando base de datos PostgreSQL...')
        
        # Verificar conexión a la base de datos
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                self.stdout.write(
                    self.style.SUCCESS('✓ Conexión a PostgreSQL establecida correctamente')
                )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'✗ Error de conexión a PostgreSQL: {e}')
            )
            return
        
        # Ejecutar migraciones
        self.stdout.write('Ejecutando migraciones...')
        try:
            call_command('migrate', verbosity=0)
            self.stdout.write(
                self.style.SUCCESS('✓ Migraciones ejecutadas correctamente')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'✗ Error en migraciones: {e}')
            )
            return
        
        # Crear superusuario si no existe
        from django.contrib.auth.models import User
        if not User.objects.filter(username='admin').exists():
            self.stdout.write('Creando superusuario...')
            try:
                User.objects.create_superuser(
                    username='admin',
                    email='admin@warborne.com',
                    password='admin123'
                )
                self.stdout.write(
                    self.style.SUCCESS('✓ Superusuario creado: admin/admin123')
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'✗ Error creando superusuario: {e}')
                )
        else:
            self.stdout.write(
                self.style.WARNING('⚠ Superusuario ya existe')
            )
        
        # Crear datos de muestra
        self.stdout.write('Creando datos de muestra...')
        try:
            call_command('create_sample_data', verbosity=0)
            self.stdout.write(
                self.style.SUCCESS('✓ Datos de muestra creados')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'✗ Error creando datos de muestra: {e}')
            )
        
        # Mostrar información de la base de datos
        self.stdout.write('\n' + '='*50)
        self.stdout.write(self.style.SUCCESS('CONFIGURACIÓN COMPLETADA'))
        self.stdout.write('='*50)
        self.stdout.write(f'Base de datos: {connection.settings_dict["NAME"]}')
        self.stdout.write(f'Host: {connection.settings_dict["HOST"]}')
        self.stdout.write(f'Puerto: {connection.settings_dict["PORT"]}')
        self.stdout.write(f'Usuario: {connection.settings_dict["USER"]}')
        self.stdout.write('='*50)
        self.stdout.write('Acceso al admin: /admin/')
        self.stdout.write('Usuario: admin')
        self.stdout.write('Contraseña: admin123')
        self.stdout.write('='*50)
