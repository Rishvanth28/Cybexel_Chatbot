from django.contrib import admin
from .models import Business, ChatMessage

@admin.register(Business)
class BusinessAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'area', 'rating', 'status')
    list_filter = ('category', 'status')
    search_fields = ('name', 'area', 'address')


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'content_preview', 'created_at')
    list_filter = ('role', 'created_at', 'user')
    search_fields = ('content', 'user__username')
    readonly_fields = ('created_at',)

    def content_preview(self, obj):
        return obj.content[:80] + '...' if len(obj.content) > 80 else obj.content
    content_preview.short_description = 'Content'
