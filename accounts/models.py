from django.contrib.auth.models import AbstractUser
from django.db import models


class Plan(models.TextChoices):
    FREE = "FREE", "Free"
    PRO = "PRO", "Pro"


class User(AbstractUser):
    email = models.EmailField(unique=True)
    ai_tips_enabled = models.BooleanField(default=False)
    plan = models.CharField(max_length=10, choices=Plan.choices, default=Plan.FREE)
    stripe_customer_id = models.CharField(max_length=64, blank=True)

    def __str__(self):
        return self.email or self.username
