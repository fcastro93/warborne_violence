"""
URL configuration for warborne_tools project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponseRedirect
from guilds import views as guilds_views

def redirect_to_dashboard(request):
    return HttpResponseRedirect('/dashboard/')

urlpatterns = [
    path('', redirect_to_dashboard, name='home'),
    path('admin/', admin.site.urls),
    
    # Direct dashboard URLs
    path('dashboard/', guilds_views.staff_dashboard, name='dashboard'),
    path('players/', guilds_views.players_management, name='players'),
    path('events/', guilds_views.events_management, name='events'),
    path('guilds/', guilds_views.guild_analytics, name='guilds'),
    path('analytics/', guilds_views.event_analytics, name='analytics'),
    path('bot/', guilds_views.bot_analytics, name='bot'),
    
    # Legacy guilds URLs (for backward compatibility)
    path('guilds-legacy/', include('guilds.urls')),
]

# Servir archivos estáticos y media en desarrollo
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)