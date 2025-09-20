from django.db import models
from django.contrib.auth.models import AbstractUser
from django.db import models

# Create your models here.

class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ('user', 'User'),
        ('shopkeeper', 'Shopkeeper')
    )

    role = models.CharField(
        max_length = 20,
        choices = ROLE_CHOICES,
        default = 'user',
        help_text = "User role: 'user' for customers, 'shopkeeper' for admin"
    )

    phone_number = models.CharField(
        max_length = 15,
        blank = True,
        null = True,
        help_text = "User's phone number for order delivery."
    )

    address = models.CharField(
        blank = True,
        null = True,
        help_text = "User's default shipping address"
    )

    date_of_birth = models.DateField(
        blank = True,
        null = True,
        help_text = "User's date of birth"
    )

    def __str__(self):
        return f"{self.username} ({self.role})"
    
    @property
    def is_shopkeeper(self):
        """Property to check if user is a shopkeeper"""
        return self.role == 'shopkeeper'

    @property
    def full_name(self):
        """Returns user's full name"""
        return f"{self.first_name} {self.last_name}".strip()

    class Meta:
        db_table = 'auth_custom_user'
        verbose_name = 'User'
        verbose_name_plural = 'Users'
 
