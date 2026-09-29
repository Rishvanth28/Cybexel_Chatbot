from django.db import models
from django.contrib.auth.models import User


class ChatMessage(models.Model):
    """Stores individual chat messages per user."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_messages')
    role = models.CharField(max_length=10, choices=[('user', 'User'), ('assistant', 'Assistant')])
    content = models.TextField()
    businesses = models.JSONField(default=list, blank=True)
    intent_data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.user.username} - {self.role} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"


class Business(models.Model):
    business_id = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=255)
    category = models.CharField(max_length=100)
    subcategory = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    services = models.TextField(blank=True)
    address = models.TextField(blank=True)
    area = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100, default='Coimbatore')
    state = models.CharField(max_length=100, default='Tamil Nadu')
    pincode = models.CharField(max_length=10, blank=True)
    latitude = models.FloatField()
    longitude = models.FloatField()
    phone = models.CharField(max_length=20, blank=True)
    rating = models.FloatField(default=0.0)
    review_count = models.IntegerField(default=0)
    price_range = models.CharField(max_length=20, blank=True)
    open_hours = models.CharField(max_length=100, blank=True)
    search_keywords = models.TextField(blank=True)
    status = models.CharField(max_length=20, default='active')

    class Meta:
        verbose_name_plural = 'Businesses'
        ordering = ['-rating']

    def __str__(self):
        return f"{self.name} ({self.category})"
