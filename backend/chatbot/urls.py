from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    # Auth endpoints
    path('api/auth/register/', views.register, name='register'),
    path('api/auth/login/', views.user_login, name='login'),
    path('api/auth/logout/', views.user_logout, name='logout'),
    path('api/auth/me/', views.get_current_user, name='current_user'),
    path('api/auth/history/', views.get_chat_history, name='chat_history'),
    # Chat endpoints
    path('api/chat/', views.chat, name='chat'),
    path('api/search/', views.search, name='search'),
    path('api/businesses/<str:business_id>/', views.business_detail, name='business_detail'),
    path('api/categories/', views.categories, name='categories'),
    path('api/areas/', views.areas, name='areas'),
]
