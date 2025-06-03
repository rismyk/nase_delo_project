from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # Административная панель Django
    path('admin/', admin.site.urls),
    
    # Основные маршруты приложения
    path('', include('accounts.urls')),
    
    # API маршруты
    path('api/cases/', include('cases.urls')),
    path('api/calendar/', include('calendar_events.urls')),
    # path('api/invitations/', include('invitations.urls')),  # добавим позже
    # path('api/financial/', include('financial.urls')),  # добавим позже
]

# Служим медиа-файлы в режиме разработки
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)