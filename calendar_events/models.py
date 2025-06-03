from django.db import models
from django.conf import settings
from django.utils import timezone

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
    
    # Информация об отложении - расширенная версия
    postponement_reason = models.TextField('Причина отложения', blank=True)
    original_event = models.ForeignKey(
        'self', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='postponed_events',
        verbose_name='Исходное событие'
    )
    
    # Новые поля для отложения
    postponed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='postponed_events',
        verbose_name="Кто отложил"
    )
    postponed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Дата отложения"
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
    
    # Свойства для API
    @property
    def case_number(self):
        """Возвращает номер дела"""
        return self.case.court_case_number if self.case else None
    
    @property
    def case_title(self):
        """Возвращает заголовок дела"""
        if self.case:
            return f"{self.case.court_case_number} - {self.case.subject_matter[:50]}"
        return None
    
    @property
    def court_name(self):
        """Возвращает название суда"""
        return self.case.court.name if self.case and self.case.court else None
    
    @property
    def is_postponed(self):
        """Проверяет, было ли событие отложено"""
        return self.status == 'postponed'
    
    @property
    def is_original(self):
        """Проверяет, является ли событие оригинальным (не перенесенным)"""
        return self.original_event is None
    
    @property 
    def postponement_count(self):
        """Возвращает количество переносов"""
        return len(self.get_postponement_history()) - 1
    
    def postpone_event(self, new_datetime, reason, postponed_by, new_end_datetime=None):
        """
        Улучшенный метод для отложения события
        """
        # Помечаем текущее событие как отложенное
        self.status = 'postponed'
        self.postponement_reason = reason
        self.postponed_by = postponed_by
        self.postponed_at = timezone.now()
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
            original_event=self.original_event or self,  # Ссылка на первое событие в цепочке
            email_notifications=self.email_notifications,
            telegram_notifications=self.telegram_notifications,
            created_by=self.created_by,
        )
        
        return new_event
    
    def postpone(self, new_datetime, reason, postponed_by):
        """
        Альтернативное название метода для совместимости с API
        """
        return self.postpone_event(new_datetime, reason, postponed_by)
    
    def get_postponement_history(self):
        """
        Получить всю историю переносов события
        """
        history = []
        current_event = self
        
        # Идем по цепочке original_event до самого первого события
        while current_event.original_event:
            current_event = current_event.original_event
        
        # Собираем все события в цепочке переносов
        def collect_postponements(event):
            history.append(event)
            for postponed in event.postponed_events.all().order_by('postponed_at'):
                collect_postponements(postponed)
        
        collect_postponements(current_event)
        return history
    
    def get_original_event(self):
        """
        Получить самое первое событие в цепочке переносов
        """
        current_event = self
        while current_event.original_event:
            current_event = current_event.original_event
        return current_event
    
    def get_latest_event(self):
        """
        Получить самое последнее (актуальное) событие в цепочке переносов
        """
        original = self.get_original_event()
        
        def find_latest(event):
            latest = event
            for postponed in event.postponed_events.all():
                candidate = find_latest(postponed)
                if candidate.created_at > latest.created_at:
                    latest = candidate
            return latest
        
        return find_latest(original)
    
    def can_be_postponed(self):
        """
        Проверяет, может ли событие быть отложено
        """
        return self.status == 'scheduled' and self.start_datetime > timezone.now()
    
    def get_status_color(self):
        """
        Возвращает цвет для отображения статуса
        """
        colors = {
            'scheduled': 'primary',
            'postponed': 'warning', 
            'completed': 'success',
            'cancelled': 'danger',
        }
        return colors.get(self.status, 'secondary')


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


class PostponementLog(models.Model):
    """
    Лог переносов событий для аудита
    """
    original_event = models.ForeignKey(
        CalendarEvent, 
        on_delete=models.CASCADE, 
        related_name='postponement_logs'
    )
    new_event = models.ForeignKey(
        CalendarEvent, 
        on_delete=models.CASCADE, 
        related_name='creation_logs'
    )
    
    old_datetime = models.DateTimeField('Старая дата и время')
    new_datetime = models.DateTimeField('Новая дата и время')
    reason = models.TextField('Причина переноса', blank=True)
    
    postponed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE,
        verbose_name='Кто перенес'
    )
    postponed_at = models.DateTimeField('Дата переноса', auto_now_add=True)
    
    # Дополнительная информация
    user_ip = models.GenericIPAddressField('IP адрес', null=True, blank=True)
    user_agent = models.TextField('User Agent', blank=True)
    
    class Meta:
        verbose_name = 'Лог переноса события'
        verbose_name_plural = 'Логи переносов событий'
        ordering = ['-postponed_at']
    
    def __str__(self):
        return f"Перенос {self.original_event.title} с {self.old_datetime} на {self.new_datetime}"