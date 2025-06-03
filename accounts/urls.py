from django.urls import path
from . import views

# URL маршруты для приложения accounts
urlpatterns = [
    # Веб-страницы
    path('', views.home_view, name='home'),
    path('login/', views.login_view, name='login'),
    path('register/<uuid:token>/', views.register_view, name='register'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('logout/', views.logout_view, name='logout'),
    
    # API endpoints
    path('api/login/', views.api_login, name='api_login'),
    path('api/register/', views.api_register, name='api_register'),
    path('api/logout/', views.api_logout, name='api_logout'),
    path('api/profile/', views.api_user_profile, name='api_user_profile'),
    path('api/profile/update/', views.api_user_profile_update, name='api_user_profile_update'),
    path('api/change-password/', views.api_change_password, name='api_change_password'),
    
    # API для владельца системы
    path('api/users/', views.UserListView.as_view(), name='api_user_list'),
    path('api/invite/', views.api_invite_user, name='api_invite_user'),
]