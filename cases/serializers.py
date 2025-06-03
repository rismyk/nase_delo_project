from rest_framework import serializers
from .models import Court, Case, SeparateDispute, CaseAccess
from accounts.serializers import UserSerializer

class CourtSerializer(serializers.ModelSerializer):
    """Сериализатор для справочника судов"""
    
    class Meta:
        model = Court
        fields = ['id', 'name', 'court_type', 'region', 'address']

class SeparateDisputeSerializer(serializers.ModelSerializer):
    """Сериализатор для обособленных споров"""
    
    class Meta:
        model = SeparateDispute
        fields = [
            'id', 'dispute_name', 'court_determination_number', 
            'dispute_amount', 'plaintiff_dispute', 'defendant_dispute',
            'dispute_status', 'dispute_description', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

class CaseAccessSerializer(serializers.ModelSerializer):
    """Сериализатор для доступа к делам"""
    
    user = UserSerializer(read_only=True)
    granted_by = UserSerializer(read_only=True)
    
    class Meta:
        model = CaseAccess
        fields = ['id', 'user', 'access_level', 'granted_by', 'granted_at']

class CaseListSerializer(serializers.ModelSerializer):
    """Сериализатор для списка дел (краткая информация)"""
    
    court_name = serializers.CharField(source='court.name', read_only=True)
    owner_name = serializers.CharField(source='owner.full_name', read_only=True)
    access_level = serializers.SerializerMethodField()
    
    class Meta:
        model = Case
        fields = [
            'id', 'court_case_number', 'court_name', 'case_type', 
            'case_status', 'subject_matter', 'claim_amount', 
            'received_date', 'owner_name', 'access_level', 'created_at'
        ]
    
    def get_access_level(self, obj):
        """Определяем уровень доступа пользователя к делу"""
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return None
        
        user = request.user
        
        # Если пользователь - владелец дела
        if obj.owner == user:
            return 'owner'
        
        # Если пользователь имеет доступ к делу
        try:
            access = CaseAccess.objects.get(case=obj, user=user)
            return access.access_level
        except CaseAccess.DoesNotExist:
            return None

class CaseDetailSerializer(serializers.ModelSerializer):
    """Сериализатор для детальной информации о деле"""
    
    court = CourtSerializer(read_only=True)
    court_id = serializers.IntegerField(write_only=True)
    owner = UserSerializer(read_only=True)
    separate_disputes = SeparateDisputeSerializer(many=True, read_only=True)
    access_grants = CaseAccessSerializer(many=True, read_only=True)
    access_level = serializers.SerializerMethodField()
    
    class Meta:
        model = Case
        fields = [
            'id', 'court_case_number', 'court', 'court_id', 'case_type',
            'court_instance', 'subject_matter', 'claim_amount', 'case_status',
            'received_date', 'judge_name', 'plaintiff', 'defendant', 
            'third_party', 'client_role', 'subcategory', 'description', 
            'notes', 'owner', 'separate_disputes', 'access_grants', 
            'access_level', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'owner', 'created_at', 'updated_at']
    
    def get_access_level(self, obj):
        """Определяем уровень доступа пользователя к делу"""
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return None
        
        user = request.user
        
        # Если пользователь - владелец дела
        if obj.owner == user:
            return 'owner'
        
        # Если пользователь имеет доступ к делу
        try:
            access = CaseAccess.objects.get(case=obj, user=user)
            return access.access_level
        except CaseAccess.DoesNotExist:
            return None
    
    def create(self, validated_data):
        """Создание нового дела"""
        request = self.context.get('request')
        validated_data['owner'] = request.user
        return super().create(validated_data)

class CaseCreateSerializer(serializers.ModelSerializer):
    """Упрощенный сериализатор для создания дела"""
    
    class Meta:
        model = Case
        fields = [
            'court_case_number', 'court', 'case_type', 'court_instance',
            'subject_matter', 'claim_amount', 'case_status', 'received_date',
            'judge_name', 'plaintiff', 'defendant', 'third_party', 
            'client_role', 'subcategory', 'description', 'notes'
        ]
    
    def create(self, validated_data):
        """Создание нового дела с автоматическим назначением владельца"""
        request = self.context.get('request')
        validated_data['owner'] = request.user
        return super().create(validated_data)
    
    def validate(self, attrs):
        """Валидация данных дела"""
        court_case_number = attrs.get('court_case_number')
        court = attrs.get('court')
        
        # Проверяем уникальность номера дела в суде
        if Case.objects.filter(court_case_number=court_case_number, court=court).exists():
            raise serializers.ValidationError(
                "Дело с таким номером уже существует в данном суде"
            )
        
        return attrs

class CaseInvitationSerializer(serializers.Serializer):
    """Сериализатор для приглашения к делу"""
    
    email = serializers.EmailField()
    access_level = serializers.ChoiceField(choices=CaseAccess.ACCESS_LEVEL_CHOICES)
    message = serializers.CharField(max_length=1000, required=False, allow_blank=True)
    
    def validate_email(self, value):
        """Проверяем, что пользователь с таким email существует"""
        from accounts.models import User
        
        try:
            user = User.objects.get(email=value)
            return value
        except User.DoesNotExist:
            raise serializers.ValidationError(
                "Пользователь с таким email не зарегистрирован в системе"
            )