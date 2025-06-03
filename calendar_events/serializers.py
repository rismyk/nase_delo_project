from rest_framework import serializers
from .models import CalendarEvent, EventNotification
from cases.models import Case, CaseAccess, SeparateDispute
from accounts.models import User

class CalendarEventListSerializer(serializers.ModelSerializer):
    """Сериализатор для списка событий календаря (краткая информация)"""
    
    case_number = serializers.CharField(source='case.court_case_number', read_only=True)
    case_title = serializers.SerializerMethodField()
    court_name = serializers.CharField(source='case.court.name', read_only=True)
    dispute_name = serializers.CharField(source='separate_dispute.dispute_name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.full_name', read_only=True)
    
    # Поля для отложения
    postponed_by_name = serializers.CharField(source='postponed_by.full_name', read_only=True)
    is_postponed = serializers.BooleanField(read_only=True)
    is_original = serializers.BooleanField(read_only=True)
    postponement_count = serializers.IntegerField(read_only=True)
    
    # Информация об исходном событии
    original_event_id = serializers.IntegerField(source='original_event.id', read_only=True)
    original_event_title = serializers.CharField(source='original_event.title', read_only=True)
    original_event_datetime = serializers.DateTimeField(source='original_event.start_datetime', read_only=True)
    
    class Meta:
        model = CalendarEvent
        fields = [
            'id', 'event_type', 'title', 'start_datetime', 'end_datetime',
            'status', 'case_number', 'case_title', 'court_name', 'dispute_name',
            'courtroom', 'created_by_name', 'created_at',
            
            # Поля для отложения
            'postponed_by_name', 'is_postponed', 'is_original', 'postponement_count',
            'original_event_id', 'original_event_title', 'original_event_datetime',
            'postponement_reason', 'postponed_at'
        ]
    
    def get_case_title(self, obj):
        """Получаем краткое название дела"""
        if obj.separate_dispute:
            return f"{obj.case.court_case_number} - {obj.separate_dispute.dispute_name}"
        return f"{obj.case.court_case_number} - {obj.case.subject_matter[:50]}{'...' if len(obj.case.subject_matter) > 50 else ''}"

class CalendarEventDetailSerializer(serializers.ModelSerializer):
    """Сериализатор для детальной информации о событии"""
    
    # Связанные объекты
    case_id = serializers.IntegerField(write_only=True)
    separate_dispute_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    
    # Read-only поля
    case_number = serializers.CharField(source='case.court_case_number', read_only=True)
    case_title = serializers.SerializerMethodField(read_only=True)
    court_name = serializers.CharField(source='case.court.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.full_name', read_only=True)
    
    # Поля для отложения
    postponed_by_name = serializers.CharField(source='postponed_by.full_name', read_only=True)
    is_postponed = serializers.BooleanField(read_only=True)
    is_original = serializers.BooleanField(read_only=True)
    postponement_count = serializers.IntegerField(read_only=True)
    
    # Информация об исходном событии
    original_event_id = serializers.IntegerField(source='original_event.id', read_only=True)
    original_event_title = serializers.CharField(source='original_event.title', read_only=True)
    original_event_datetime = serializers.DateTimeField(source='original_event.start_datetime', read_only=True)
    
    class Meta:
        model = CalendarEvent
        fields = [
            'id', 'case_id', 'separate_dispute_id',
            'event_type', 'title', 'description', 'start_datetime', 'end_datetime',
            'courtroom', 'court_address', 'participants', 'agenda', 'status',
            'email_notifications', 'telegram_notifications',
            'created_by', 'created_at', 'updated_at',
            
            # Поля отложения
            'postponement_reason', 'original_event', 'postponed_by', 'postponed_at',
            
            # Read-only поля
            'case_number', 'case_title', 'court_name', 'created_by_name',
            'postponed_by_name', 'is_postponed', 'is_original', 'postponement_count',
            'original_event_id', 'original_event_title', 'original_event_datetime',
        ]
        read_only_fields = [
            'id', 'created_by', 'created_at', 'updated_at',
            'postponement_reason', 'original_event', 'postponed_by', 'postponed_at'
        ]
    
    def get_case_title(self, obj):
        """Получаем полное название дела"""
        if obj.separate_dispute:
            return f"{obj.case.court_case_number} - {obj.separate_dispute.dispute_name}"
        return f"{obj.case.court_case_number} - {obj.case.subject_matter}"
    
    def create(self, validated_data):
        """Создание нового события"""
        request = self.context.get('request')
        validated_data['created_by'] = request.user
        
        # Обрабатываем case_id и separate_dispute_id
        case_id = validated_data.pop('case_id')
        separate_dispute_id = validated_data.pop('separate_dispute_id', None)
        
        validated_data['case_id'] = case_id
        if separate_dispute_id:
            validated_data['separate_dispute_id'] = separate_dispute_id
        
        return super().create(validated_data)
    
    def validate(self, attrs):
        """Валидация данных события"""
        case_id = attrs.get('case_id')
        separate_dispute_id = attrs.get('separate_dispute_id')
        
        # Проверяем доступ к делу
        try:
            case = Case.objects.get(id=case_id)
        except Case.DoesNotExist:
            raise serializers.ValidationError("Дело не найдено")
        
        request = self.context.get('request')
        user = request.user
        
        # Проверяем, что пользователь имеет доступ к делу
        if case.owner != user:
            try:
                access = CaseAccess.objects.get(case=case, user=user)
                if access.access_level not in ['full', 'calendar']:
                    raise serializers.ValidationError("Недостаточно прав для создания событий по этому делу")
            except CaseAccess.DoesNotExist:
                raise serializers.ValidationError("Нет доступа к данному делу")
        
        # Если указан обособленный спор, проверяем его принадлежность к делу
        if separate_dispute_id:
            try:
                dispute = SeparateDispute.objects.get(id=separate_dispute_id, case=case)
            except SeparateDispute.DoesNotExist:
                raise serializers.ValidationError("Обособленный спор не найден или не принадлежит к указанному делу")
        
        # Проверяем даты
        start_datetime = attrs.get('start_datetime')
        end_datetime = attrs.get('end_datetime')
        
        if end_datetime and start_datetime and start_datetime >= end_datetime:
            raise serializers.ValidationError("Время окончания должно быть позже времени начала")
        
        return attrs

class CalendarEventCreateSerializer(serializers.ModelSerializer):
    """Упрощенный сериализатор для создания события"""
    
    # Информация о создателе
    created_by_name = serializers.CharField(source='created_by.full_name', read_only=True)
    
    # Информация о деле
    case_number = serializers.CharField(source='case.court_case_number', read_only=True)
    court_name = serializers.CharField(source='case.court.name', read_only=True)
    
    class Meta:
        model = CalendarEvent
        fields = [
            'id', 'case', 'separate_dispute', 'event_type', 'title', 'description',
            'start_datetime', 'end_datetime', 'courtroom', 'court_address',
            'participants', 'agenda', 'email_notifications', 'telegram_notifications',
            'status', 'created_at',
            
            # Read-only информационные поля
            'created_by_name', 'case_number', 'court_name'
        ]
        read_only_fields = ['id', 'created_at', 'status']
    
    def create(self, validated_data):
        """Создание события с автоматическим назначением создателя"""
        request = self.context.get('request')
        validated_data['created_by'] = request.user
        return super().create(validated_data)
    
    def validate_case(self, value):
        """Проверяем доступ к делу"""
        request = self.context.get('request')
        user = request.user
        
        if value.owner != user:
            try:
                access = CaseAccess.objects.get(case=value, user=user)
                if access.access_level not in ['full', 'calendar']:
                    raise serializers.ValidationError("Недостаточно прав для создания событий по этому делу")
            except CaseAccess.DoesNotExist:
                raise serializers.ValidationError("Нет доступа к данному делу")
        
        return value
    
    def validate_separate_dispute(self, value):
        """Проверяем принадлежность обособленного спора к делу"""
        if value:
            case = self.initial_data.get('case')
            if case and value.case.id != int(case):
                raise serializers.ValidationError("Обособленный спор не принадлежит выбранному делу")
        return value
    
    def validate(self, attrs):
        """Дополнительная валидация"""
        start_datetime = attrs.get('start_datetime')
        end_datetime = attrs.get('end_datetime')
        event_type = attrs.get('event_type')
        separate_dispute = attrs.get('separate_dispute')
        
        # Проверяем даты
        if end_datetime and start_datetime and start_datetime >= end_datetime:
            raise serializers.ValidationError({
                'end_datetime': 'Время окончания должно быть позже времени начала'
            })
        
        # Для событий по обособленным спорам обязательно должен быть указан спор
        if event_type == 'separate_hearing' and not separate_dispute:
            raise serializers.ValidationError({
                'separate_dispute': 'Для события по обособленному спору необходимо выбрать спор'
            })
        
        return attrs

class EventPostponeSerializer(serializers.Serializer):
    """Сериализатор для отложения события"""
    
    new_start_datetime = serializers.DateTimeField()
    new_end_datetime = serializers.DateTimeField(required=False, allow_null=True)
    reason = serializers.CharField(max_length=1000, required=False, allow_blank=True)
    
    def validate_new_start_datetime(self, value):
        """Проверяем, что новая дата в будущем"""
        from django.utils import timezone
        
        if value <= timezone.now():
            raise serializers.ValidationError("Новая дата и время должны быть в будущем")
        return value
    
    def validate(self, attrs):
        """Валидация данных для отложения"""
        new_start = attrs.get('new_start_datetime')
        new_end = attrs.get('new_end_datetime')
        
        if new_end and new_start and new_start >= new_end:
            raise serializers.ValidationError("Время окончания должно быть позже времени начала")
        
        return attrs

class EventNotificationSerializer(serializers.ModelSerializer):
    """Сериализатор для уведомлений о событиях"""
    
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    event_title = serializers.CharField(source='event.title', read_only=True)
    
    class Meta:
        model = EventNotification
        fields = [
            'id', 'event', 'user', 'notification_type', 'notification_time',
            'sent', 'sent_at', 'created_at',
            
            # Read-only информационные поля
            'user_name', 'event_title'
        ]
        read_only_fields = ['id', 'sent', 'sent_at', 'created_at']

class CalendarStatsSerializer(serializers.Serializer):
    """Сериализатор для статистики календаря"""
    
    total_events = serializers.IntegerField()
    upcoming_events = serializers.IntegerField()
    today_events = serializers.IntegerField()
    week_events = serializers.IntegerField()
    postponed_events = serializers.IntegerField()
    by_type = serializers.DictField()
    by_status = serializers.DictField()

class PostponementHistorySerializer(serializers.ModelSerializer):
    """Сериализатор для истории переносов"""
    
    postponed_by_name = serializers.CharField(source='postponed_by.full_name', read_only=True)
    original_datetime = serializers.DateTimeField(source='original_event.start_datetime', read_only=True)
    
    class Meta:
        model = CalendarEvent
        fields = [
            'id', 'title', 'start_datetime', 'status', 'postponement_reason',
            'postponed_by_name', 'postponed_at', 'original_datetime'
        ]

# Дополнительные сериализаторы для совместимости с существующим API

class CaseListSerializer(serializers.Serializer):
    """Простой сериализатор дела для совместимости"""
    id = serializers.IntegerField()
    court_case_number = serializers.CharField()
    subject_matter = serializers.CharField()

class SeparateDisputeSerializer(serializers.Serializer):
    """Простой сериализатор обособленного спора для совместимости"""
    id = serializers.IntegerField()
    dispute_name = serializers.CharField()
    case_id = serializers.IntegerField()

class UserSerializer(serializers.Serializer):
    """Простой сериализатор пользователя для совместимости"""
    id = serializers.IntegerField()
    full_name = serializers.CharField()
    email = serializers.EmailField()