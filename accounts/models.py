from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    """Кастомная модель пользователя для системы 'Наше дело'"""
    
    # Дополнительные поля из ТЗ
    full_name = models.CharField('Полное имя', max_length=200)
    phone = models.CharField('Телефон', max_length=20, blank=True)
    telegram_id = models.CharField('Telegram ID', max_length=100, blank=True)
    organization = models.CharField('Организация', max_length=300, blank=True)
    lawyer_certificate = models.CharField('Номер удостоверения', max_length=100, blank=True)
    region = models.CharField('Регион работы', max_length=100, blank=True)
    
    # Роли пользователей
    ROLE_CHOICES = [
        ('owner', 'Владелец системы'),
        ('invited', 'Приглашенный юрист'),
    ]
    role = models.CharField('Роль', max_length=20, choices=ROLE_CHOICES, default='invited')
    
    # Timestamps
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)
    updated_at = models.DateTimeField('Дата обновления', auto_now=True)
    
    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
        
    def __str__(self):
        return f"{self.full_name} ({self.email})"
    
    @property
    def is_system_owner(self):
        """Проверка, является ли пользователь владельцем системы"""
        return self.role == 'owner'
    
    def save(self, *args, **kwargs):
        # Если full_name не заполнено, используем first_name + last_name
        if not self.full_name:
            self.full_name = f"{self.first_name} {self.last_name}".strip()
        super().save(*args, **kwargs)