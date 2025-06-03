from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Создаем роутер для ViewSet
router = DefaultRouter()
router.register(r'events', views.CalendarEventViewSet, basename='calendar-events')

urlpatterns = [
    # ViewSet endpoints (основные)
    path('', include(router.urls)),
    
    # Дополнительные API endpoints
    path('stats/', views.calendar_stats, name='calendar_stats'),
    path('calendar-view/', views.calendar_view, name='calendar_view'),
    
    # События - дополнительные действия
    path('events/<int:event_id>/postpone/', views.postpone_event, name='postpone_event'),
    path('events/<int:event_id>/notifications/', views.event_notifications, name='event_notifications'),
    
    # Endpoints для обратной совместимости
    path('events-list/', views.CalendarEventListView.as_view(), name='events_list'),
    path('events-detail/<int:pk>/', views.CalendarEventDetailView.as_view(), name='events_detail'),
]