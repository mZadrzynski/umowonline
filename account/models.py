from django.contrib.auth.models import AbstractUser
from django.db import models
from django.contrib.auth.models import Group
from django.conf import settings

class CustomUser(AbstractUser):
    email = models.EmailField('email address', unique=True)
    pass
