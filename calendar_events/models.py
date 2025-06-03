from django.db import models
from django.conf import settings

class CalendarEvent(models.Model):
    """События календаря"""
    
    case = models.ForeignKey('cases.Case', on_delete=models.CASCADE, related_name='events', verbose_name='Дело')
    separate_dispute = models.ForeignKey(
        'cases.SeparateDispute', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='events',
        verbose_name='Обособленный спор'
    )
    
    EVENT_TYPE_CHOICES = [
        ('hearing', 'Судебное заседание'),
        ('separate_hearing', 'Заседание по обособленному спору'),
        ('deadline', 'Срок подачи документов'),
        ('reminder', 'Личное напоминание'),
    ]
    event_type = models.CharField('Тип события', max_length=20, choices=EVENT_TYPE_CHOICES)
    
    title = models.CharField('Название', max_length=300)
    description = models.TextField('Описание', blank=True)
    
    start_datetime = models.DateTimeField('Дата и время начала')
    end_datetime = models.DateTimeField('Дата и время окончания', null=True, blank=True)
    
    # Информация о заседании
    courtroom = models.CharField('Номер зала/кабинета', max_length=50, blank=True)
    court_address = models.TextField('Адрес суда', blank=True)
    participants = models.TextField('Участники процесса', blank=True)
    agenda = models.TextField('Вопросы для рассмотрения', blank=True)
    
    STATUS_CHOICES = [
        ('scheduled', 'Запланировано'),
        ('postponed', 'Отложено'),
        ('completed', 'Проведено'),
        ('cancelled', 'Отменено'),
    ]
    status = models.CharField('Статус', max_length=20, choices=STATUS_CHOICES, default='scheduled')
    
    # Информация об отложении
    postponement_reason = models.TextField('Причина отложения', blank=True)
    original_event = models.ForeignKey(
        'self', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='postponed_events',
        verbose_name='Исходное событие'
    )
    
    # Настройки уведомлений
    email_notifications = models.BooleanField('Email уведомления', default=True)
    telegram_notifications = models.BooleanField('Telegram уведомления', default=False)
    
    # Пользователь, создавший событие
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='created_events',
        verbose_name='Создано пользователем'
    )
    
    # Timestamps
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)
    updated_at = models.DateTimeField('Дата обновления', auto_now=True)
    
    class Meta:
        verbose_name = 'Событие календаря'
        verbose_name_plural = 'События календаря'
        ordering = ['start_datetime']
        
    def __str__(self):
        return f"{self.title} - {self.start_datetime.strftime('%d.%m.%Y %H:%M')}"
    
    def postpone_event(self, new_datetime, reason, new_end_datetime=None):
        """Метод для отложения события"""
        # Помечаем текущее событие как отложенное
        self.status = 'postponed'
        self.postponement_reason = reason
        self.save()
        
        # Создаем новое событие с новой датой
        new_event = CalendarEvent.objects.create(
            case=self.case,
            separate_dispute=self.separate_dispute,
            event_type=self.event_type,
            title=self.title,
            description=self.description,
            start_datetime=new_datetime,
            end_datetime=new_end_datetime or self.end_datetime,
            courtroom=self.courtroom,
            court_address=self.court_address,
            participants=self.participants,
            agenda=self.agenda,
            status='scheduled',
            original_event=self.original_event or self,
            email_notifications=self.email_notifications,
            telegram_notifications=self.telegram_notifications,
            created_by=self.created_by,
        )
        
        return new_event

class EventNotification(models.Model):
    """Настройки уведомлений для событий"""
    
    event = models.ForeignKey(CalendarEvent, on_delete=models.CASCADE, related_name='notifications')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    
    NOTIFICATION_TYPE_CHOICES = [
        ('email', 'Email'),
        ('telegram', 'Telegram'),
    ]
    notification_type = models.CharField('Тип уведомления', max_length=20, choices=NOTIFICATION_TYPE_CHOICES)
    
    NOTIFICATION_TIME_CHOICES = [
        ('3_days', 'За 3 дня'),
        ('1_day', 'За 1 день'),
        ('2_hours', 'За 2 часа'),
        ('30_minutes', 'За 30 минут'),
    ]
    notification_time = models.CharField('Время уведомления', max_length=20, choices=NOTIFICATION_TIME_CHOICES)
    
    sent = models.BooleanField('Отправлено', default=False)
    sent_at = models.DateTimeField('Дата отправки', null=True, blank=True)
    
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)
    
    class Meta:
        verbose_name = 'Уведомление о событии'
        verbose_name_plural = 'Уведомления о событиях'
        unique_together = ['event', 'user', 'notification_type', 'notification_time']
        
    def __str__(self):
        return f"Уведомление для {self.user.full_name} о {self.event.title}"