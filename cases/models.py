from django.db import models
from django.conf import settings

class Court(models.Model):
    """Справочник судов"""
    name = models.CharField('Наименование суда', max_length=500)
    court_type = models.CharField('Тип суда', max_length=50, choices=[
        ('arbitration', 'Арбитражный'),
        ('general', 'Общей юрисдикции'),
        ('supreme', 'Верховный суд РФ'),
        ('constitutional', 'Конституционный суд РФ'),
    ])
    region = models.CharField('Регион', max_length=100, blank=True)
    address = models.TextField('Адрес', blank=True)
    
    class Meta:
        verbose_name = 'Суд'
        verbose_name_plural = 'Суды'
        
    def __str__(self):
        return self.name

class Case(models.Model):
    """Основная модель дела"""
    
    # Основные поля
    court_case_number = models.CharField('Номер дела в суде', max_length=100)
    court = models.ForeignKey(Court, on_delete=models.PROTECT, verbose_name='Суд')
    
    CASE_TYPE_CHOICES = [
        ('civil', 'Гражданское'),
        ('administrative', 'Административное'),
        ('criminal', 'Уголовное'),
        ('arbitration', 'Арбитражное'),
        ('bankruptcy', 'Банкротство'),
    ]
    case_type = models.CharField('Тип дела', max_length=50, choices=CASE_TYPE_CHOICES)
    
    INSTANCE_CHOICES = [
        ('first', 'Первая инстанция'),
        ('appeal', 'Апелляционная'),
        ('cassation', 'Кассационная'),
        ('supervisory', 'Надзорная'),
    ]
    court_instance = models.CharField('Инстанция', max_length=20, choices=INSTANCE_CHOICES)
    
    subject_matter = models.TextField('Предмет спора')
    claim_amount = models.DecimalField('Сумма требований', max_digits=15, decimal_places=2, null=True, blank=True)
    
    STATUS_CHOICES = [
        ('accepted', 'Принято к производству'),
        ('scheduled', 'Назначено к рассмотрению'),
        ('hearing', 'Рассматривается'),
        ('decided', 'Решение вынесено'),
        ('appeal_filed', 'Подана апелляция'),
        ('final', 'Вступило в силу'),
        ('execution', 'Исполнение'),
        ('closed', 'Дело закрыто'),
    ]
    case_status = models.CharField('Статус дела', max_length=20, choices=STATUS_CHOICES)
    
    received_date = models.DateField('Дата поступления')
    judge_name = models.CharField('Судья', max_length=200)
    
    # Стороны дела
    plaintiff = models.TextField('Истец/Заявитель')
    defendant = models.TextField('Ответчик/Заинтересованное лицо')
    third_party = models.TextField('Третье лицо', blank=True)
    
    CLIENT_ROLE_CHOICES = [
        ('plaintiff', 'Истец'),
        ('defendant', 'Ответчик'),
        ('third_party', 'Третье лицо'),
        ('other', 'Иное'),
    ]
    client_role = models.CharField('Роль представляемой стороны', max_length=20, choices=CLIENT_ROLE_CHOICES)
    
    # Дополнительные поля
    subcategory = models.CharField('Подкатегория', max_length=200, blank=True)
    description = models.TextField('Краткое описание', blank=True)
    notes = models.TextField('Примечания', blank=True)
    
    # Связи
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        verbose_name='Владелец дела',
        related_name='owned_cases'
    )
    
    # Timestamps
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)
    updated_at = models.DateTimeField('Дата обновления', auto_now=True)
    
    class Meta:
        verbose_name = 'Дело'
        verbose_name_plural = 'Дела'
        unique_together = ['court_case_number', 'court']
        
    def __str__(self):
        return f"{self.court_case_number} ({self.court.name})"

class SeparateDispute(models.Model):
    """Обособленные споры для дел о банкротстве"""
    
    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name='separate_disputes', verbose_name='Основное дело')
    dispute_name = models.CharField('Наименование спора', max_length=500)
    court_determination_number = models.CharField('Номер определения о выделении', max_length=100, blank=True)
    dispute_amount = models.DecimalField('Сумма требований по спору', max_digits=15, decimal_places=2, null=True, blank=True)
    
    # Стороны спора (могут отличаться от основного дела)
    plaintiff_dispute = models.TextField('Истец по спору')
    defendant_dispute = models.TextField('Ответчик по спору')
    
    DISPUTE_STATUS_CHOICES = [
        ('separated', 'Выделен'),
        ('scheduled', 'Назначен к рассмотрению'),
        ('hearing', 'Рассматривается'),
        ('decided', 'Решение вынесено'),
        ('closed', 'Завершен'),
    ]
    dispute_status = models.CharField('Статус спора', max_length=20, choices=DISPUTE_STATUS_CHOICES)
    dispute_description = models.TextField('Описание спора', blank=True)
    
    # Timestamps
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)
    updated_at = models.DateTimeField('Дата обновления', auto_now=True)
    
    class Meta:
        verbose_name = 'Обособленный спор'
        verbose_name_plural = 'Обособленные споры'
        
    def __str__(self):
        return f"{self.dispute_name} (дело {self.case.court_case_number})"

class CaseAccess(models.Model):
    """Доступ пользователей к делам"""
    
    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name='access_grants')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='case_accesses')
    
    ACCESS_LEVEL_CHOICES = [
        ('full', 'Полный доступ'),
        ('calendar', 'Только календарь'),
        ('view', 'Только просмотр'),
    ]
    access_level = models.CharField('Уровень доступа', max_length=20, choices=ACCESS_LEVEL_CHOICES)
    
    granted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='granted_accesses',
        verbose_name='Предоставлен пользователем'
    )
    granted_at = models.DateTimeField('Дата предоставления', auto_now_add=True)
    
    class Meta:
        verbose_name = 'Доступ к делу'
        verbose_name_plural = 'Доступы к делам'
        unique_together = ['case', 'user']
        
    def __str__(self):
        return f"{self.user.full_name} - {self.case.court_case_number} ({self.access_level})"