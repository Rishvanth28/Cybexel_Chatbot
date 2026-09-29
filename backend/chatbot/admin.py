from django.contrib import admin
from .models import Business

@admin.register(Business)
class BusinessAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'area', 'rating', 'status')
    list_filter = ('category', 'status')
    search_fields = ('name', 'area', 'address')
