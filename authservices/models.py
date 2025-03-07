from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    role = [
        ('Admin', 'admin'),
        ('Attendee', 'attendee'),
        ('Organizer', 'organizer')
    ]
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    username = models.CharField(max_length=255, unique=True)
    bio = models.TextField(blank=True)
    phone_number = models.CharField(max_length=15, blank=True)  
    profile_image = models.ImageField(upload_to='media/', null=True, blank=True)
    role = models.CharField(choices=role, max_length=255, default='attendee')
    verification_token = models.CharField(max_length=255, null=True, blank=True)
    verification_token_expiry = models.DateTimeField(null=True, blank=True)
    is_verified = models.BooleanField(default=False)
    REQUIRED_FIELDS = ['email']

    def __str__(self):
        return self.username