from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

class CustomUser(AbstractUser):
    email = models.EmailField('email address', unique=True)
    username = models.CharField(max_length=150, unique=True)
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']
    
User = get_user_model()


class Subscription(models.Model):
    SUBSCRIPTION_STATUS = [
        ('active', 'Aktywna'),
        ('expired', 'Wygasła'),
        ('cancelled', 'Anulowana'),
    ]
    
    # Użyj get_user_model() zamiast bezpośredniego importu User
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='subscription')
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField()
    status = models.CharField(max_length=20, choices=SUBSCRIPTION_STATUS, default='active')
    hotpay_transaction_id = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def is_active(self):
        return (
            self.status == 'active' and 
            timezone.now() <= self.end_date
        )
    
    def extend_subscription(self, days=30):
        if self.is_active():
            self.end_date += timedelta(days=days)
        else:
            self.start_date = timezone.now()
            self.end_date = timezone.now() + timedelta(days=days)
            self.status = 'active'
        self.save()
    
    def __str__(self):
        return f"{self.user.username} - {self.status}"