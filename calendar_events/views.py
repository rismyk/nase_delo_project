from rest_framework import status, generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.db.models import Q, Count
from django.shortcuts import get_object_or_404
from django.utils import timezone
from datetime import datetime, timedelta

from .models import CalendarEvent, EventNotification
from .serializers import (
    CalendarEventListSerializer, CalendarEventDetailSerializer,
    CalendarEventCreateSerializer, EventPostponeSerializer,
    EventNotificationSerializer, CalendarStatsSerializer
)
from cases.models import Case, CaseAccess

# ============= КАЛЕНДАРНЫЕ СОБЫТИЯ =============

class CalendarEventListView(generics.ListCreateAPIView):
    """API для списка событий календаря"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return CalendarEventCreateSerializer
        return CalendarEventListSerializer
    
    def get_queryset(self):
        user = self.request.user
        
        # Отладочная информация
        print(f"=== DEBUG CALENDAR API ===")
        print(f"User: {user.email}")
        
        # События по делам пользователя: собственные + дела с доступом к календарю
        accessible_cases = Case.objects.filter(
            Q(owner=user) | Q(access_grants__user=user, access_grants__access_level__in=['full', 'calendar'])
        ).distinct()
        
        print(f"Accessible cases count: {accessible_cases.count()}")
        for case in accessible_cases:
            print(f"Case: {case.court_case_number}")
        
        queryset = CalendarEvent.objects.filter(
            case__in=accessible_cases
        ).select_related(
            'case', 'case__court', 'separate_dispute', 'created_by'
        ).order_by('start_datetime')
        
        print(f"Total events count: {queryset.count()}")
        
        # Фильтры
        
        # Фильтр по типу события
        event_type = self.request.query_params.get('type')
        if event_type:
            queryset = queryset.filter(event_type=event_type)
        
        # Фильтр по статусу
        event_status = self.request.query_params.get('status')
        if event_status:
            queryset = queryset.filter(status=event_status)
        
        # Фильтр по делу
        case_id = self.request.query_params.get('case_id')
        if case_id:
            queryset = queryset.filter(case_id=case_id)
        
        # Фильтр по датам
        date_from = self.request.query_params.get('date_from')
        if date_from:
            try:
                date_from = datetime.fromisoformat(date_from.replace('Z', '+00:00'))
                queryset = queryset.filter(start_datetime__gte=date_from)
            except ValueError:
                pass
        
        date_to = self.request.query_params.get('date_to')
        if date_to:
            try:
                date_to = datetime.fromisoformat(date_to.replace('Z', '+00:00'))
                queryset = queryset.filter(start_datetime__lte=date_to)
            except ValueError:
                pass
        
        # Фильтр "только предстоящие события"
        upcoming = self.request.query_params.get('upcoming')
        if upcoming == 'true':
            from django.utils import timezone
            queryset = queryset.filter(start_datetime__gte=timezone.now())
            print(f"Upcoming events count: {queryset.count()}")
        
        # Фильтр "события сегодня"
        today = self.request.query_params.get('today')
        if today == 'true':
            today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
            today_end = today_start + timedelta(days=1)
            queryset = queryset.filter(start_datetime__range=[today_start, today_end])
        
        # Фильтр "события на неделе"
        this_week = self.request.query_params.get('week')
        if this_week == 'true':
            week_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
            week_end = week_start + timedelta(days=7)
            queryset = queryset.filter(start_datetime__range=[week_start, week_end])
        
        print(f"Final queryset count: {queryset.count()}")
        return queryset

class CalendarEventDetailView(generics.RetrieveUpdateDestroyAPIView):
    """API для детального просмотра/редактирования события"""
    serializer_class = CalendarEventDetailSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        accessible_cases = Case.objects.filter(
            Q(owner=user) | Q(access_grants__user=user)
        ).distinct()
        
        return CalendarEvent.objects.filter(case__in=accessible_cases)
    
    def get_object(self):
        obj = super().get_object()
        
        # Проверяем права для изменения/удаления
        if self.request.method in ['PUT', 'PATCH', 'DELETE']:
            user = self.request.user
            case = obj.case
            
            # Владелец дела может все
            if case.owner == user:
                return obj
            
            # Создатель события может редактировать свои события
            if obj.created_by == user:
                return obj
            
            # Проверяем уровень доступа к делу
            try:
                access = CaseAccess.objects.get(case=case, user=user)
                if access.access_level not in ['full', 'calendar']:
                    from rest_framework.exceptions import PermissionDenied
                    raise PermissionDenied("Недостаточно прав для выполнения операции")
            except CaseAccess.DoesNotExist:
                from rest_framework.exceptions import PermissionDenied
                raise PermissionDenied("Нет доступа к данному делу")
        
        return obj

# ============= ОТЛОЖЕНИЕ СОБЫТИЙ =============

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def postpone_event(request, event_id):
    """API для отложения события"""
    
    # Получаем событие и проверяем доступ
    user = request.user
    accessible_cases = Case.objects.filter(
        Q(owner=user) | Q(access_grants__user=user, access_grants__access_level__in=['full', 'calendar'])
    ).distinct()
    
    event = get_object_or_404(CalendarEvent, id=event_id, case__in=accessible_cases)
    
    # Проверяем, что событие можно отложить
    if event.status == 'postponed':
        return Response({
            'error': 'Событие уже отложено'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    serializer = EventPostponeSerializer(data=request.data)
    if serializer.is_valid():
        new_start = serializer.validated_data['new_start_datetime']
        new_end = serializer.validated_data.get('new_end_datetime')
        reason = serializer.validated_data['reason']
        
        # Отлагаем событие (создаем новое)
        new_event = event.postpone_event(new_start, reason, new_end)
        
        # Возвращаем данные нового события
        response_serializer = CalendarEventDetailSerializer(new_event, context={'request': request})
        return Response({
            'success': True,
            'message': 'Событие успешно отложено',
            'original_event_id': event.id,
            'new_event': response_serializer.data
        })
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# ============= УВЕДОМЛЕНИЯ =============

@api_view(['GET', 'POST'])
@permission_classes([permissions.IsAuthenticated])
def event_notifications(request, event_id):
    """API для уведомлений о событии"""
    
    # Проверяем доступ к событию
    user = request.user
    accessible_cases = Case.objects.filter(
        Q(owner=user) | Q(access_grants__user=user)
    ).distinct()
    
    event = get_object_or_404(CalendarEvent, id=event_id, case__in=accessible_cases)
    
    if request.method == 'GET':
        notifications = EventNotification.objects.filter(event=event, user=user)
        serializer = EventNotificationSerializer(notifications, many=True)
        return Response(serializer.data)
    
    elif request.method == 'POST':
        # Создаем уведомление
        serializer = EventNotificationSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(event=event, user=user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# ============= СТАТИСТИКА =============

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def calendar_stats(request):
    """API для получения статистики календаря пользователя"""
    
    user = request.user
    
    # Получаем события пользователя
    accessible_cases = Case.objects.filter(
        Q(owner=user) | Q(access_grants__user=user)
    ).distinct()
    
    events = CalendarEvent.objects.filter(case__in=accessible_cases)
    
    # Базовая статистика
    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)
    week_end = today_start + timedelta(days=7)
    
    total_events = events.count()
    upcoming_events = events.filter(start_datetime__gte=now, status='scheduled').count()
    today_events = events.filter(start_datetime__range=[today_start, today_end]).count()
    week_events = events.filter(start_datetime__range=[today_start, week_end]).count()
    postponed_events = events.filter(status='postponed').count()
    
    # Группировка по типам
    by_type = {}
    for choice in CalendarEvent.EVENT_TYPE_CHOICES:
        type_code = choice[0]
        type_name = choice[1]
        count = events.filter(event_type=type_code).count()
        by_type[type_code] = {
            'name': type_name,
            'count': count
        }
    
    # Группировка по статусам
    by_status = {}
    for choice in CalendarEvent.STATUS_CHOICES:
        status_code = choice[0]
        status_name = choice[1]
        count = events.filter(status=status_code).count()
        by_status[status_code] = {
            'name': status_name,
            'count': count
        }
    
    stats = {
        'total_events': total_events,
        'upcoming_events': upcoming_events,
        'today_events': today_events,
        'week_events': week_events,
        'postponed_events': postponed_events,
        'by_type': by_type,
        'by_status': by_status
    }
    
    serializer = CalendarStatsSerializer(stats)
    return Response(serializer.data)

# ============= КАЛЕНДАРНОЕ ПРЕДСТАВЛЕНИЕ =============

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def calendar_view(request):
    """API для календарного представления событий"""
    
    user = request.user
    
    # Получаем параметры запроса
    year = request.query_params.get('year')
    month = request.query_params.get('month')
    
    if year and month:
        try:
            year = int(year)
            month = int(month)
            
            # Получаем события за месяц
            month_start = datetime(year, month, 1).replace(tzinfo=timezone.get_current_timezone())
            if month == 12:
                month_end = datetime(year + 1, 1, 1).replace(tzinfo=timezone.get_current_timezone())
            else:
                month_end = datetime(year, month + 1, 1).replace(tzinfo=timezone.get_current_timezone())
            
            accessible_cases = Case.objects.filter(
                Q(owner=user) | Q(access_grants__user=user)
            ).distinct()
            
            events = CalendarEvent.objects.filter(
                case__in=accessible_cases,
                start_datetime__range=[month_start, month_end]
            ).select_related('case', 'case__court', 'separate_dispute', 'created_by')
            
            # Группируем события по дням
            events_by_day = {}
            for event in events:
                day = event.start_datetime.day
                if day not in events_by_day:
                    events_by_day[day] = []
                
                event_data = CalendarEventListSerializer(event, context={'request': request}).data
                events_by_day[day].append(event_data)
            
            return Response({
                'year': year,
                'month': month,
                'events_by_day': events_by_day,
                'total_events': len(events)
            })
            
        except (ValueError, TypeError):
            return Response({
                'error': 'Неверный формат года или месяца'
            }, status=status.HTTP_400_BAD_REQUEST)
    
    else:
        return Response({
            'error': 'Необходимо указать год и месяц'
        }, status=status.HTTP_400_BAD_REQUEST)

# ============= БЫСТРЫЕ ДЕЙСТВИЯ =============

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def mark_event_completed(request, event_id):
    """API для отметки события как завершенного"""
    
    user = request.user
    accessible_cases = Case.objects.filter(
        Q(owner=user) | Q(access_grants__user=user, access_grants__access_level__in=['full', 'calendar'])
    ).distinct()
    
    event = get_object_or_404(CalendarEvent, id=event_id, case__in=accessible_cases)
    
    # Проверяем права
    if event.case.owner != user and event.created_by != user:
        try:
            access = CaseAccess.objects.get(case=event.case, user=user)
            if access.access_level not in ['full', 'calendar']:
                return Response({
                    'error': 'Недостаточно прав для выполнения операции'
                }, status=status.HTTP_403_FORBIDDEN)
        except CaseAccess.DoesNotExist:
            return Response({
                'error': 'Нет доступа к данному делу'
            }, status=status.HTTP_403_FORBIDDEN)
    
    event.status = 'completed'
    event.save()
    
    serializer = CalendarEventDetailSerializer(event, context={'request': request})
    return Response({
        'success': True,
        'message': 'Событие отмечено как завершенное',
        'event': serializer.data
    })