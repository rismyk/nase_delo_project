from django.contrib import admin
from .models import CalendarEvent, EventNotification

@admin.register(CalendarEvent)
class CalendarEventAdmin(admin.ModelAdmin):
    list_display = ('title', 'case', 'start_datetime', 'status', 'created_by')
    list_filter = ('event_type', 'status', 'start_datetime')
    search_fields = ('title', 'case__court_case_number')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(EventNotification)
class EventNotificationAdmin(admin.ModelAdmin):
    list_display = ('event', 'user', 'notification_type', 'notification_time', 'sent')
    list_filter = ('notification_type', 'notification_time', 'sent')