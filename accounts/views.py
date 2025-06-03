from rest_framework import status, generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from .models import User
from .serializers import (
    UserSerializer, UserRegistrationSerializer, 
    LoginSerializer, PasswordChangeSerializer
)

# ============= WEB VIEWS (для обычных страниц) =============

def home_view(request):
    """Главная страница - редирект в зависимости от аутентификации"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    else:
        return redirect('login')

def login_view(request):
    """Страница входа"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'accounts/login.html')

def register_view(request, token):
    """Страница регистрации по токену приглашения"""
    from invitations.models import SystemInvitation
    
    try:
        invitation = SystemInvitation.objects.get(invitation_token=token)
        if not invitation.is_valid():
            return render(request, 'accounts/invitation_expired.html')
        
        context = {
            'invitation': invitation,
            'token': token
        }
        return render(request, 'accounts/register.html', context)
    except SystemInvitation.DoesNotExist:
        return render(request, 'accounts/invitation_invalid.html')

@login_required
def dashboard_view(request):
    """Главная панель (дашборд)"""
    return render(request, 'dashboard.html')

def logout_view(request):
    """Выход из системы"""
    logout(request)
    return redirect('login')

# ============= API VIEWS =============

@api_view(['POST'])
@permission_classes([permissions.AllowAny])
@csrf_exempt
def api_login(request):
    """API для входа в систему"""
    serializer = LoginSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.validated_data['user']
        
        # Логинуем пользователя для веб-сессии
        login(request, user)
        
        return Response({
            'success': True,
            'message': 'Вход выполнен успешно',
            'user': UserSerializer(user).data
        })
    
    return Response({
        'success': False,
        'errors': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([permissions.AllowAny])
@csrf_exempt
def api_register(request):
    """API для регистрации нового пользователя"""
    serializer = UserRegistrationSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        
        # Логинуем пользователя
        login(request, user)
        
        return Response({
            'success': True,
            'message': 'Регистрация прошла успешно',
            'user': UserSerializer(user).data
        }, status=status.HTTP_201_CREATED)
    
    return Response({
        'success': False,
        'errors': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def api_logout(request):
    """API для выхода из системы"""
    logout(request)
    return Response({'success': True, 'message': 'Выход выполнен успешно'})

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def api_user_profile(request):
    """API для получения профиля текущего пользователя"""
    serializer = UserSerializer(request.user)
    return Response(serializer.data)

@api_view(['PUT', 'PATCH'])
@permission_classes([permissions.IsAuthenticated])
def api_user_profile_update(request):
    """API для обновления профиля пользователя"""
    serializer = UserSerializer(request.user, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def api_change_password(request):
    """API для смены пароля"""
    serializer = PasswordChangeSerializer(data=request.data, context={'request': request})
    if serializer.is_valid():
        user = request.user
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        
        return Response({
            'success': True,
            'message': 'Пароль успешно изменен'
        })
    
    return Response({
        'success': False,
        'errors': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)

# ============= API VIEWS для владельца системы =============

class UserListView(generics.ListAPIView):
    """API для получения списка пользователей (только для владельца)"""
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        # Только владелец системы может видеть всех пользователей
        if self.request.user.is_system_owner:
            return User.objects.all().order_by('-created_at')
        else:
            # Обычные пользователи видят только себя
            return User.objects.filter(id=self.request.user.id)

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
@csrf_exempt
def api_invite_user(request):
    """API для приглашения нового пользователя в систему (только владелец)"""
    
    # Отладочная информация
    print(f"User: {request.user.email}")
    print(f"User role: {request.user.role}")
    print(f"Is system owner: {request.user.is_system_owner}")
    
    if not request.user.is_system_owner:
        return Response({
            'success': False,
            'error': f'Только владелец системы может приглашать пользователей. Ваша роль: {request.user.role}'
        }, status=status.HTTP_403_FORBIDDEN)
    
    email = request.data.get('email')
    if not email:
        return Response({
            'success': False,
            'error': 'Email обязателен'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Проверяем, что пользователь с таким email не существует
    if User.objects.filter(email=email).exists():
        return Response({
            'success': False,
            'error': 'Пользователь с таким email уже существует'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Создаем приглашение
    from invitations.models import SystemInvitation
    invitation = SystemInvitation.objects.create(
        inviter=request.user,
        invitee_email=email
    )
    
    # TODO: Отправить email с приглашением
    
    return Response({
        'success': True,
        'invitation_id': invitation.id,
        'invitation_url': request.build_absolute_uri(
            reverse('register', kwargs={'token': invitation.invitation_token})
        )
    })