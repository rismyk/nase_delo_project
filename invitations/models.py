import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import timedelta

class SystemInvitation(models.Model):
    """Приглашения в систему (только владелец может отправлять)"""
    
    inviter = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='sent_system_invitations',
        verbose_name='Пригласивший (владелец системы)'
    )
    invitee_email = models.EmailField('Email приглашаемого')
    invitation_token = models.UUIDField('Токен приглашения', default=uuid.uuid4, unique=True)
    
    STATUS_CHOICES = [
        ('pending', 'Ожидает подтверждения'),
        ('used', 'Использовано'),
        ('expired', 'Истекло'),
        ('revoked', 'Отозвано'),
    ]
    status = models.CharField('Статус', max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Срок действия - 7 дней
    expires_at = models.DateTimeField('Срок действия')
    used_at = models.DateTimeField('Дата использования', null=True, blank=True)
    used_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='used_system_invitation',
        verbose_name='Зарегистрированный пользователь'
    )
    
    # Timestamps
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)
    updated_at = models.DateTimeField('Дата обновления', auto_now=True)
    
    class Meta:
        verbose_name = 'Приглашение в систему'
        verbose_name_plural = 'Приглашения в систему'
        ordering = ['-created_at']
        
    def __str__(self):
        return f"Приглашение для {self.invitee_email} от {self.inviter.full_name}"
    
    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(days=7)
        super().save(*args, **kwargs)
    
    def is_expired(self):
        """Проверка истечения срока действия"""
        return timezone.now() > self.expires_at
    
    def is_valid(self):
        """Проверка действительности приглашения"""
        return self.status == 'pending' and not self.is_expired()
    
    def mark_as_used(self, user):
        """Отметить приглашение как использованное"""
        self.status = 'used'
        self.used_at = timezone.now()
        self.used_by = user
        self.save()
    
    def revoke(self):
        """Отозвать приглашение"""
        self.status = 'revoked'
        self.save()

class CaseInvitation(models.Model):
    """Приглашения к делу"""
    
    case = models.ForeignKey('cases.Case', on_delete=models.CASCADE, related_name='invitations', verbose_name='Дело')
    inviter = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='sent_case_invitations',
        verbose_name='Пригласивший'
    )
    invitee_email = models.EmailField('Email приглашаемого')
    invitee = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='received_case_invitations',
        verbose_name='Приглашенный пользователь'
    )
    
    ACCESS_LEVEL_CHOICES = [
        ('full', 'Полный доступ'),
        ('calendar', 'Только календарь'),
        ('view', 'Только просмотр'),
    ]
    access_level = models.CharField('Уровень доступа', max_length=20, choices=ACCESS_LEVEL_CHOICES)
    
    STATUS_CHOICES = [
        ('pending', 'Ожидает ответа'),
        ('accepted', 'Принято'),
        ('declined', 'Отклонено'),
        ('expired', 'Истекло'),
    ]
    status = models.CharField('Статус', max_length=20, choices=STATUS_CHOICES, default='pending')
    
    invitation_token = models.UUIDField('Токен приглашения', default=uuid.uuid4, unique=True)
    invitation_message = models.TextField('Сообщение при приглашении', blank=True)
    
    # Timestamps
    invited_at = models.DateTimeField('Дата приглашения', auto_now_add=True)
    responded_at = models.DateTimeField('Дата ответа', null=True, blank=True)
    expires_at = models.DateTimeField('Срок действия')
    
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)
    updated_at = models.DateTimeField('Дата обновления', auto_now=True)
    
    class Meta:
        verbose_name = 'Приглашение к делу'
        verbose_name_plural = 'Приглашения к делам'
        ordering = ['-invited_at']
        unique_together = ['case', 'invitee_email']
        
    def __str__(self):
        return f"Приглашение к делу {self.case.court_case_number} для {self.invitee_email}"
    
    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(days=14)  # 14 дней на ответ
        super().save(*args, **kwargs)
    
    def is_expired(self):
        """Проверка истечения срока действия"""
        return timezone.now() > self.expires_at
    
    def is_valid(self):
        """Проверка действительности приглашения"""
        return self.status == 'pending' and not self.is_expired()
    
    def accept(self, user):
        """Принять приглашение"""
        from cases.models import CaseAccess
        
        self.status = 'accepted'
        self.responded_at = timezone.now()
        self.invitee = user
        self.save()
        
        # Создаем доступ к делу
        CaseAccess.objects.get_or_create(
            case=self.case,
            user=user,
            defaults={
                'access_level': self.access_level,
                'granted_by': self.inviter,
            }
        )
    
    def decline(self, user):
        """Отклонить приглашение"""
        self.status = 'declined'
        self.responded_at = timezone.now()
        self.invitee = user
        self.save()

class InvitationHistory(models.Model):
    """История приглашений"""
    
    invitation_type = models.CharField('Тип приглашения', max_length=20, choices=[
        ('system', 'В систему'),
        ('case', 'К делу'),
    ])
    inviter = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='invitation_history',
        verbose_name='Пригласивший'
    )
    invitee_email = models.EmailField('Email приглашаемого')
    action = models.CharField('Действие', max_length=50)  # sent, accepted, declined, revoked, expired
    details = models.JSONField('Детали', default=dict, blank=True)
    
    created_at = models.DateTimeField('Дата действия', auto_now_add=True)
    
    class Meta:
        verbose_name = 'История приглашений'
        verbose_name_plural = 'История приглашений'
        ordering = ['-created_at']
        
    def __str__(self):
        return f"{self.action} - {self.invitee_email} ({self.created_at.strftime('%d.%m.%Y %H:%M')})"