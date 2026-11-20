from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect
from django.views.static import serve
from halaqat import views as halaqat_views


urlpatterns = [
    path('', halaqat_views.home_view, name='home'),
    path('home/', halaqat_views.home_view, name='root'),
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('halaqat/', include('halaqat.urls')),
    path('sessions/', include('halaqa_sessions.urls')),
    path('attendance/', include('attendance.urls')),
    path('recitations/', include('recitations.urls')),
    path('chat/', include('chat.urls')),
    path('notifications/', include('notifications.urls')),
    path('dashboard/', include('dashboard.urls')),
    path('subscriptions/', include('subscriptions.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
else:
    # Production fallback: ensures uploaded avatars and media are always served seamlessly
    urlpatterns += [
        re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
    ]
