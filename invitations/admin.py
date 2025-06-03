from django.contrib import admin
from .models import SystemInvitation, CaseInvitation, InvitationHistory

@admin.register(SystemInvitation)
class SystemInvitationAdmin(admin.ModelAdmin):
    list_display = ('invitee_email', 'inviter', 'status', 'created_at', 'expires_at')
    list_filter = ('status', 'created_at')
    search_fields = ('invitee_email', 'inviter__full_name')

@admin.register(CaseInvitation)
class CaseInvitationAdmin(admin.ModelAdmin):
    list_display = ('invitee_email', 'case', 'access_level', 'status', 'invited_at')
    list_filter = ('access_level', 'status', 'invited_at')
    search_fields = ('invitee_email', 'case__court_case_number')

@admin.register(InvitationHistory)
class InvitationHistoryAdmin(admin.ModelAdmin):
    list_display = ('invitee_email', 'invitation_type', 'action', 'created_at')
    list_filter = ('invitation_type', 'action', 'created_at')