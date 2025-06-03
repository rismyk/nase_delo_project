from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import User

class UserSerializer(serializers.ModelSerializer):
    """Сериализатор для модели пользователя"""
    
    class Meta:
        model = User
        fields = [
            'id', 'email', 'full_name', 'phone', 'telegram_id', 
            'organization', 'lawyer_certificate', 'region', 'role',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

class UserRegistrationSerializer(serializers.ModelSerializer):
    """Сериализатор для регистрации нового пользователя"""
    
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)
    invitation_token = serializers.UUIDField(write_only=True)
    
    class Meta:
        model = User
        fields = [
            'email', 'full_name', 'phone', 'organization', 
            'lawyer_certificate', 'region', 'password', 
            'password_confirm', 'invitation_token'
        ]
    
    def validate(self, attrs):
        # Проверяем, что пароли совпадают
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("Пароли не совпадают")
        
        # Проверяем токен приглашения
        from invitations.models import SystemInvitation
        try:
            invitation = SystemInvitation.objects.get(
                invitation_token=attrs['invitation_token'],
                invitee_email=attrs['email']
            )
            if not invitation.is_valid():
                raise serializers.ValidationError("Приглашение недействительно или истекло")
        except SystemInvitation.DoesNotExist:
            raise serializers.ValidationError("Недействительный токен приглашения")
        
        return attrs
    
    def create(self, validated_data):
        # Удаляем лишние поля
        invitation_token = validated_data.pop('invitation_token')
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        
        # Создаем пользователя
        user = User.objects.create_user(
            username=validated_data['email'],  # используем email как username
            password=password,
            **validated_data
        )
        
        # Отмечаем приглашение как использованное
        from invitations.models import SystemInvitation
        invitation = SystemInvitation.objects.get(
            invitation_token=invitation_token,
            invitee_email=user.email
        )
        invitation.mark_as_used(user)
        
        return user

class LoginSerializer(serializers.Serializer):
    """Сериализатор для входа в систему"""
    
    email = serializers.EmailField()
    password = serializers.CharField()
    
    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')
        
        if email and password:
            # Сначала находим пользователя по email (берем первого, если есть дубликаты)
            try:
                user_obj = User.objects.filter(email=email).first()
                if not user_obj:
                    raise User.DoesNotExist()
                    
                # Аутентифицируем по username
                user = authenticate(username=user_obj.username, password=password)
                if not user:
                    # Попробуем еще раз по email на случай, если username = email
                    user = authenticate(username=email, password=password)
            except User.DoesNotExist:
                user = None
            
            if user and user.is_active:
                attrs['user'] = user
                return attrs
            else:
                raise serializers.ValidationError("Неверный email или пароль")
        else:
            raise serializers.ValidationError("Необходимо указать email и пароль")

class PasswordChangeSerializer(serializers.Serializer):
    """Сериализатор для смены пароля"""
    
    old_password = serializers.CharField()
    new_password = serializers.CharField(min_length=8)
    new_password_confirm = serializers.CharField()
    
    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError("Новые пароли не совпадают")
        return attrs
    
    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Неверный текущий пароль")
        return value