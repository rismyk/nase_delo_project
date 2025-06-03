from django.contrib import admin
from .models import Court, Case, SeparateDispute, CaseAccess

@admin.register(Court)
class CourtAdmin(admin.ModelAdmin):
    list_display = ('name', 'court_type', 'region')
    list_filter = ('court_type', 'region')
    search_fields = ('name', 'region')

class SeparateDisputeInline(admin.TabularInline):
    model = SeparateDispute
    extra = 0

class CaseAccessInline(admin.TabularInline):
    model = CaseAccess
    extra = 0

@admin.register(Case)
class CaseAdmin(admin.ModelAdmin):
    list_display = ('court_case_number', 'court', 'case_type', 'case_status', 'owner', 'created_at')
    list_filter = ('case_type', 'case_status', 'court_instance', 'created_at')
    search_fields = ('court_case_number', 'subject_matter', 'plaintiff', 'defendant')
    readonly_fields = ('created_at', 'updated_at')
    
    inlines = [SeparateDisputeInline, CaseAccessInline]
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('court_case_number', 'court', 'case_type', 'court_instance')
        }),
        ('Детали дела', {
            'fields': ('subject_matter', 'claim_amount', 'case_status', 'received_date', 'judge_name')
        }),
        ('Стороны', {
            'fields': ('plaintiff', 'defendant', 'third_party', 'client_role')
        }),
        ('Дополнительно', {
            'fields': ('subcategory', 'description', 'notes', 'owner'),
            'classes': ('collapse',)
        }),
        ('Служебные поля', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(SeparateDispute)
class SeparateDisputeAdmin(admin.ModelAdmin):
    list_display = ('dispute_name', 'case', 'dispute_status', 'dispute_amount', 'created_at')
    list_filter = ('dispute_status', 'created_at')
    search_fields = ('dispute_name', 'case__court_case_number')

@admin.register(CaseAccess)
class CaseAccessAdmin(admin.ModelAdmin):
    list_display = ('user', 'case', 'access_level', 'granted_by', 'granted_at')
    list_filter = ('access_level', 'granted_at')
    search_fields = ('user__full_name', 'case__court_case_number')