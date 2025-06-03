from django.urls import path
from . import views

# URL маршруты для API дел
urlpatterns = [
    # Справочники
    path('courts/', views.CourtListView.as_view(), name='court_list'),
    
    # Дела
    path('', views.CaseListView.as_view(), name='case_list'),
    path('<int:pk>/', views.CaseDetailView.as_view(), name='case_detail'),
    
    # Обособленные споры
    path('<int:case_id>/disputes/', views.case_separate_disputes, name='case_disputes'),
    path('<int:case_id>/disputes/<int:dispute_id>/', views.separate_dispute_detail, name='dispute_detail'),
    
    # Управление доступом
    path('<int:case_id>/invite/', views.invite_to_case, name='invite_to_case'),
    path('<int:case_id>/access/', views.case_access_list, name='case_access_list'),
    path('<int:case_id>/access/<int:access_id>/revoke/', views.revoke_case_access, name='revoke_case_access'),
    
    # Статистика
    path('stats/', views.cases_stats, name='cases_stats'),
]