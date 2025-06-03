from django.contrib import admin
from .models import FinancialTransaction, CaseFinancialSummary

@admin.register(FinancialTransaction)
class FinancialTransactionAdmin(admin.ModelAdmin):
    list_display = ('case', 'transaction_type', 'category', 'amount', 'transaction_date', 'created_by')
    list_filter = ('transaction_type', 'category', 'transaction_date')
    search_fields = ('case__court_case_number', 'description')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(CaseFinancialSummary)
class CaseFinancialSummaryAdmin(admin.ModelAdmin):
    list_display = ('case', 'total_income', 'total_expenses', 'profit', 'last_updated')
    readonly_fields = ('total_income', 'total_expenses', 'profit', 'last_updated')
    search_fields = ('case__court_case_number',)