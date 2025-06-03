from rest_framework import status, generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.db.models import Q
from django.shortcuts import get_object_or_404

from .models import Court, Case, SeparateDispute, CaseAccess
from .serializers import (
    CourtSerializer, CaseListSerializer, CaseDetailSerializer, 
    CaseCreateSerializer, SeparateDisputeSerializer, CaseInvitationSerializer
)

# ============= СПРАВОЧНИКИ =============

class CourtListView(generics.ListCreateAPIView):
    """API для списка судов"""
    queryset = Court.objects.all().order_by('name')
    serializer_class = CourtSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Фильтрация по типу суда
        court_type = self.request.query_params.get('type')
        if court_type:
            queryset = queryset.filter(court_type=court_type)
        
        # Поиск по названию
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(name__icontains=search)
        
        return queryset

# ============= ДЕЛА =============

class CaseListView(generics.ListCreateAPIView):
    """API для списка дел пользователя"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return CaseCreateSerializer
        return CaseListSerializer
    
    def get_queryset(self):
        user = self.request.user
        
        # Дела пользователя: собственные + дела с доступом
        owned_cases = Case.objects.filter(owner=user)
        accessible_cases = Case.objects.filter(access_grants__user=user)
        
        # Объединяем и убираем дубликаты
        queryset = Case.objects.filter(
            Q(owner=user) | Q(access_grants__user=user)
        ).distinct().order_by('-created_at')
        
        # Фильтры
        case_type = self.request.query_params.get('type')
        if case_type:
            queryset = queryset.filter(case_type=case_type)
        
        case_status = self.request.query_params.get('status')
        if case_status:
            queryset = queryset.filter(case_status=case_status)
        
        # Поиск
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(court_case_number__icontains=search) |
                Q(subject_matter__icontains=search) |
                Q(plaintiff__icontains=search) |
                Q(defendant__icontains=search)
            )
        
        # Фильтр "только мои дела"
        only_owned = self.request.query_params.get('only_owned')
        if only_owned == 'true':
            queryset = queryset.filter(owner=user)
        
        return queryset

class CaseDetailView(generics.RetrieveUpdateDestroyAPIView):
    """API для детального просмотра/редактирования дела"""
    serializer_class = CaseDetailSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        return Case.objects.filter(
            Q(owner=user) | Q(access_grants__user=user)
        ).distinct()
    
    def get_object(self):
        obj = super().get_object()
        
        # Проверяем уровень доступа для операций изменения/удаления
        if self.request.method in ['PUT', 'PATCH', 'DELETE']:
            if obj.owner != self.request.user:
                # Проверяем, есть ли полный доступ
                try:
                    access = CaseAccess.objects.get(case=obj, user=self.request.user)
                    if access.access_level != 'full':
                        from rest_framework.exceptions import PermissionDenied
                        raise PermissionDenied("Недостаточно прав для выполнения операции")
                except CaseAccess.DoesNotExist:
                    from rest_framework.exceptions import PermissionDenied
                    raise PermissionDenied("Нет доступа к данному делу")
        
        return obj

# ============= ОБОСОБЛЕННЫЕ СПОРЫ =============

@api_view(['GET', 'POST'])
@permission_classes([permissions.IsAuthenticated])
def case_separate_disputes(request, case_id):
    """API для обособленных споров дела"""
    
    # Проверяем доступ к делу
    case = get_object_or_404(Case, id=case_id)
    user = request.user
    
    if case.owner != user:
        try:
            access = CaseAccess.objects.get(case=case, user=user)
            if request.method == 'POST' and access.access_level not in ['full']:
                return Response({
                    'error': 'Недостаточно прав для создания обособленных споров'
                }, status=status.HTTP_403_FORBIDDEN)
        except CaseAccess.DoesNotExist:
            return Response({
                'error': 'Нет доступа к данному делу'
            }, status=status.HTTP_403_FORBIDDEN)
    
    if request.method == 'GET':
        disputes = SeparateDispute.objects.filter(case=case).order_by('-created_at')
        serializer = SeparateDisputeSerializer(disputes, many=True)
        return Response(serializer.data)
    
    elif request.method == 'POST':
        serializer = SeparateDisputeSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(case=case)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET', 'PUT', 'PATCH', 'DELETE'])
@permission_classes([permissions.IsAuthenticated])
def separate_dispute_detail(request, case_id, dispute_id):
    """API для конкретного обособленного спора"""
    
    # Проверяем доступ к делу
    case = get_object_or_404(Case, id=case_id)
    dispute = get_object_or_404(SeparateDispute, id=dispute_id, case=case)
    user = request.user
    
    if case.owner != user:
        try:
            access = CaseAccess.objects.get(case=case, user=user)
            if request.method in ['PUT', 'PATCH', 'DELETE'] and access.access_level not in ['full']:
                return Response({
                    'error': 'Недостаточно прав для изменения обособленных споров'
                }, status=status.HTTP_403_FORBIDDEN)
        except CaseAccess.DoesNotExist:
            return Response({
                'error': 'Нет доступа к данному делу'
            }, status=status.HTTP_403_FORBIDDEN)
    
    if request.method == 'GET':
        serializer = SeparateDisputeSerializer(dispute)
        return Response(serializer.data)
    
    elif request.method in ['PUT', 'PATCH']:
        serializer = SeparateDisputeSerializer(
            dispute, data=request.data, partial=(request.method == 'PATCH')
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    elif request.method == 'DELETE':
        dispute.delete()
        return Response({'success': True}, status=status.HTTP_204_NO_CONTENT)

# ============= УПРАВЛЕНИЕ ДОСТУПОМ К ДЕЛАМ =============

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def invite_to_case(request, case_id):
    """API для приглашения пользователя к делу"""
    
    case = get_object_or_404(Case, id=case_id)
    
    # Только владелец дела может приглашать других пользователей
    if case.owner != request.user:
        return Response({
            'error': 'Только владелец дела может приглашать пользователей'
        }, status=status.HTTP_403_FORBIDDEN)
    
    serializer = CaseInvitationSerializer(data=request.data)
    if serializer.is_valid():
        email = serializer.validated_data['email']
        access_level = serializer.validated_data['access_level']
        message = serializer.validated_data.get('message', '')
        
        # Находим пользователя
        from accounts.models import User
        try:
            invitee = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({
                'error': 'Пользователь с таким email не найден'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Проверяем, что пользователь не приглашает сам себя
        if invitee == request.user:
            return Response({
                'error': 'Нельзя пригласить самого себя'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Проверяем, что у пользователя еще нет доступа
        if CaseAccess.objects.filter(case=case, user=invitee).exists():
            return Response({
                'error': 'У пользователя уже есть доступ к этому делу'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Создаем или обновляем приглашение
        from invitations.models import CaseInvitation
        invitation, created = CaseInvitation.objects.get_or_create(
            case=case,
            invitee_email=email,
            defaults={
                'inviter': request.user,
                'access_level': access_level,
                'invitation_message': message
            }
        )
        
        if not created:
            # Обновляем существующее приглашение
            invitation.access_level = access_level
            invitation.invitation_message = message
            invitation.status = 'pending'
            invitation.save()
        
        # Если пользователь уже зарегистрирован, сразу даем доступ
        CaseAccess.objects.get_or_create(
            case=case,
            user=invitee,
            defaults={
                'access_level': access_level,
                'granted_by': request.user
            }
        )
        
        return Response({
            'success': True,
            'message': f'Пользователь {email} приглашен к делу с уровнем доступа "{access_level}"'
        })
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def case_access_list(request, case_id):
    """API для списка пользователей с доступом к делу"""
    
    case = get_object_or_404(Case, id=case_id)
    user = request.user
    
    # Проверяем доступ к делу
    if case.owner != user:
        try:
            CaseAccess.objects.get(case=case, user=user)
        except CaseAccess.DoesNotExist:
            return Response({
                'error': 'Нет доступа к данному делу'
            }, status=status.HTTP_403_FORBIDDEN)
    
    accesses = CaseAccess.objects.filter(case=case).order_by('-granted_at')
    from .serializers import CaseAccessSerializer
    serializer = CaseAccessSerializer(accesses, many=True)
    
    return Response(serializer.data)

@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated])
def revoke_case_access(request, case_id, access_id):
    """API для отзыва доступа к делу"""
    
    case = get_object_or_404(Case, id=case_id)
    access = get_object_or_404(CaseAccess, id=access_id, case=case)
    
    # Только владелец дела может отзывать доступ
    if case.owner != request.user:
        return Response({
            'error': 'Только владелец дела может отзывать доступ'
        }, status=status.HTTP_403_FORBIDDEN)
    
    access.delete()
    
    return Response({
        'success': True,
        'message': 'Доступ к делу отозван'
    })

# ============= СТАТИСТИКА =============

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def cases_stats(request):
    """API для получения статистики по делам пользователя"""
    
    user = request.user
    
    # Собственные дела пользователя
    owned_cases = Case.objects.filter(owner=user)
    
    # Дела с доступом
    accessible_cases = Case.objects.filter(access_grants__user=user).exclude(owner=user)
    
    # Статистика по статусам
    stats = {
        'owned_cases_count': owned_cases.count(),
        'accessible_cases_count': accessible_cases.count(),
        'total_cases_count': owned_cases.count() + accessible_cases.count(),
        'by_status': {}
    }
    
    # Группировка по статусам
    for choice in Case.STATUS_CHOICES:
        status_code = choice[0]
        status_name = choice[1]
        count = owned_cases.filter(case_status=status_code).count()
        stats['by_status'][status_code] = {
            'name': status_name,
            'count': count
        }
    
    # Группировка по типам дел
    stats['by_type'] = {}
    for choice in Case.CASE_TYPE_CHOICES:
        type_code = choice[0]
        type_name = choice[1]
        count = owned_cases.filter(case_type=type_code).count()
        stats['by_type'][type_code] = {
            'name': type_name,
            'count': count
        }
    
    return Response(stats)