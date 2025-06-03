from django.urls import path
from . import views

# URL маршруты для API календаря
urlpatterns = [
    # События календаря
    path('events/', views.CalendarEventListView.as_view(), name='calendar_event_list'),
    path('events/<int:pk>/', views.CalendarEventDetailView.as_view(), name='calendar_event_detail'),
    
    # Отложение событий
    path('events/<int:event_id>/postpone/', views.postpone_event, name='postpone_event'),
    path('events/<int:event_id>/complete/', views.mark_event_completed, name='complete_event'),
    
    # Уведомления
    path('events/<int:event_id>/notifications/', views.event_notifications, name='event_notifications'),
    
    # Календарное представление
    path('view/', views.calendar_view, name='calendar_view'),
    
    # Статистика
    path('stats/', views.calendar_stats, name='calendar_stats'),
]