from django.db import models
from django.conf import settings

class FinancialTransaction(models.Model):
    """Финансовые операции по делам"""
    
    case = models.ForeignKey('cases.Case', on_delete=models.CASCADE, related_name='financial_transactions', verbose_name='Дело')
    
    TRANSACTION_TYPE_CHOICES = [
        ('income', 'Доход'),
        ('expense', 'Расход'),
    ]
    transaction_type = models.CharField('Тип операции', max_length=20, choices=TRANSACTION_TYPE_CHOICES)
    
    # Категории доходов
    INCOME_CATEGORY_CHOICES = [
        ('fee', 'Гонорар'),
        ('advance', 'Аванс от клиента'),
        ('reimbursement', 'Возмещение расходов'),
        ('other_income', 'Прочий доход'),
    ]
    
    # Категории расходов
    EXPENSE_CATEGORY_CHOICES = [
        ('court_fee', 'Госпошлина'),
        ('expert_fee', 'Расходы на экспертизы'),
        ('travel', 'Командировочные расходы'),
        ('postal', 'Почтовые расходы'),
        ('office', 'Офисные расходы'),
        ('other_expense', 'Прочий расход'),
    ]
    
    category = models.CharField('Категория', max_length=50)
    amount = models.DecimalField('Сумма', max_digits=12, decimal_places=2)
    description = models.CharField('Описание', max_length=300)
    transaction_date = models.DateField('Дата операции')
    
    # Документы
    document_number = models.CharField('Номер документа', max_length=100, blank=True)
    document_file = models.FileField('Файл документа', upload_to='financial_docs/', blank=True)
    
    # Связи
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='financial_transactions',
        verbose_name='Создано пользователем'
    )
    
    # Timestamps
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)
    updated_at = models.DateTimeField('Дата обновления', auto_now=True)
    
    class Meta:
        verbose_name = 'Финансовая операция'
        verbose_name_plural = 'Финансовые операции'
        ordering = ['-transaction_date', '-created_at']
        
    def __str__(self):
        transaction_type_display = 'Доход' if self.transaction_type == 'income' else 'Расход'
        return f"{transaction_type_display}: {self.amount} ₽ по делу {self.case.court_case_number}"
    
    def save(self, *args, **kwargs):
        # Проверяем соответствие категории и типа операции
        if self.transaction_type == 'income':
            income_categories = [choice[0] for choice in self.INCOME_CATEGORY_CHOICES]
            if self.category not in income_categories:
                self.category = 'other_income'
        elif self.transaction_type == 'expense':
            expense_categories = [choice[0] for choice in self.EXPENSE_CATEGORY_CHOICES]
            if self.category not in expense_categories:
                self.category = 'other_expense'
        
        super().save(*args, **kwargs)

class CaseFinancialSummary(models.Model):
    """Финансовая сводка по делу (автоматически обновляемая)"""
    
    case = models.OneToOneField('cases.Case', on_delete=models.CASCADE, related_name='financial_summary')
    
    total_income = models.DecimalField('Общий доход', max_digits=12, decimal_places=2, default=0)
    total_expenses = models.DecimalField('Общие расходы', max_digits=12, decimal_places=2, default=0)
    profit = models.DecimalField('Прибыль', max_digits=12, decimal_places=2, default=0)
    
    last_updated = models.DateTimeField('Последнее обновление', auto_now=True)
    
    class Meta:
        verbose_name = 'Финансовая сводка дела'
        verbose_name_plural = 'Финансовые сводки дел'
        
    def __str__(self):
        return f"Финансы по делу {self.case.court_case_number}"
    
    def update_summary(self):
        """Обновление финансовой сводки"""
        from django.db.models import Sum, Q
        
        # Подсчитываем доходы
        income_sum = FinancialTransaction.objects.filter(
            case=self.case,
            transaction_type='income'
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        # Подсчитываем расходы
        expense_sum = FinancialTransaction.objects.filter(
            case=self.case,
            transaction_type='expense'
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        self.total_income = income_sum
        self.total_expenses = expense_sum
        self.profit = income_sum - expense_sum
        self.save()
        
        return self

# Сигналы для автоматического обновления финансовой сводки
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

@receiver(post_save, sender=FinancialTransaction)
@receiver(post_delete, sender=FinancialTransaction)
def update_case_financial_summary(sender, instance, **kwargs):
    """Автоматическое обновление финансовой сводки при изменении транзакций"""
    summary, created = CaseFinancialSummary.objects.get_or_create(case=instance.case)
    summary.update_summary()