from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('api/chat/', views.chat, name='chat'),
    path('api/search/', views.search, name='search'),
    path('api/businesses/<str:business_id>/', views.business_detail, name='business_detail'),
    path('api/categories/', views.categories, name='categories'),
    path('api/areas/', views.areas, name='areas'),
]
