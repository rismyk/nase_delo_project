from rest_framework import serializers
from .models import CalendarEvent, EventNotification
from cases.serializers import CaseListSerializer, SeparateDisputeSerializer
from accounts.serializers import UserSerializer

class CalendarEventListSerializer(serializers.ModelSerializer):
    """Сериализатор для списка событий календаря (краткая информация)"""
    
    case_number = serializers.CharField(source='case.court_case_number', read_only=True)
    case_title = serializers.SerializerMethodField()
    court_name = serializers.CharField(source='case.court.name', read_only=True)
    dispute_name = serializers.CharField(source='separate_dispute.dispute_name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.full_name', read_only=True)
    
    class Meta:
        model = CalendarEvent
        fields = [
            'id', 'event_type', 'title', 'start_datetime', 'end_datetime',
            'status', 'case_number', 'case_title', 'court_name', 'dispute_name',
            'courtroom', 'created_by_name', 'created_at'
        ]
    
    def get_case_title(self, obj):
        """Получаем краткое название дела"""
        if obj.separate_dispute:
            return f"{obj.case.court_case_number} - {obj.separate_dispute.dispute_name}"
        return f"{obj.case.court_case_number} - {obj.case.subject_matter[:50]}{'...' if len(obj.case.subject_matter) > 50 else ''}"

class CalendarEventDetailSerializer(serializers.ModelSerializer):
    """Сериализатор для детальной информации о событии"""
    
    case = CaseListSerializer(read_only=True)
    case_id = serializers.IntegerField(write_only=True)
    separate_dispute = SeparateDisputeSerializer(read_only=True)
    separate_dispute_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    created_by = UserSerializer(read_only=True)
    
    class Meta:
        model = CalendarEvent
        fields = [
            'id', 'case', 'case_id', 'separate_dispute', 'separate_dispute_id',
            'event_type', 'title', 'description', 'start_datetime', 'end_datetime',
            'courtroom', 'court_address', 'participants', 'agenda', 'status',
            'postponement_reason', 'original_event', 'email_notifications',
            'telegram_notifications', 'created_by', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_by', 'created_at', 'updated_at']
    
    def create(self, validated_data):
        """Создание нового события"""
        request = self.context.get('request')
        validated_data['created_by'] = request.user
        return super().create(validated_data)
    
    def validate(self, attrs):
        """Валидация данных события"""
        case_id = attrs.get('case_id')
        separate_dispute_id = attrs.get('separate_dispute_id')
        
        # Проверяем доступ к делу
        from cases.models import Case, CaseAccess
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
            from cases.models import SeparateDispute
            try:
                dispute = SeparateDispute.objects.get(id=separate_dispute_id, case=case)
                attrs['separate_dispute_id'] = dispute.id
            except SeparateDispute.DoesNotExist:
                raise serializers.ValidationError("Обособленный спор не найден или не принадлежит к указанному делу")
        
        # Проверяем даты
        start_datetime = attrs.get('start_datetime')
        end_datetime = attrs.get('end_datetime')
        
        if end_datetime and start_datetime >= end_datetime:
            raise serializers.ValidationError("Время окончания должно быть позже времени начала")
        
        return attrs

class CalendarEventCreateSerializer(serializers.ModelSerializer):
    """Упрощенный сериализатор для создания события"""
    
    class Meta:
        model = CalendarEvent
        fields = [
            'case', 'separate_dispute', 'event_type', 'title', 'description',
            'start_datetime', 'end_datetime', 'courtroom', 'court_address',
            'participants', 'agenda', 'email_notifications', 'telegram_notifications'
        ]
    
    def create(self, validated_data):
        """Создание события с автоматическим назначением создателя"""
        request = self.context.get('request')
        validated_data['created_by'] = request.user
        return super().create(validated_data)

class EventPostponeSerializer(serializers.Serializer):
    """Сериализатор для отложения события"""
    
    new_start_datetime = serializers.DateTimeField()
    new_end_datetime = serializers.DateTimeField(required=False, allow_null=True)
    reason = serializers.CharField(max_length=1000)
    
    def validate(self, attrs):
        """Валидация данных для отложения"""
        new_start = attrs.get('new_start_datetime')
        new_end = attrs.get('new_end_datetime')
        
        if new_end and new_start >= new_end:
            raise serializers.ValidationError("Время окончания должно быть позже времени начала")
        
        return attrs

class EventNotificationSerializer(serializers.ModelSerializer):
    """Сериализатор для уведомлений о событиях"""
    
    user = UserSerializer(read_only=True)
    event_title = serializers.CharField(source='event.title', read_only=True)
    
    class Meta:
        model = EventNotification
        fields = [
            'id', 'event', 'user', 'notification_type', 'notification_time',
            'sent', 'sent_at', 'event_title', 'created_at'
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