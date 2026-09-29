from django.contrib import admin
from django.urls import path, include
from chatbot import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('health', views.health, name='health'),
    path('api/', include('chatbot.urls')),
    path('', include('chatbot.urls')),
]
