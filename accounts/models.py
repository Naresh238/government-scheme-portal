
from django.db import models
from django.contrib.auth.models import User


class SchemeAlert(models.Model):
    title = models.CharField(max_length=200)
    category = models.CharField(max_length=100)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class EligibilityHistory(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )
    age = models.PositiveIntegerField()
    income = models.PositiveIntegerField()
    occupation = models.CharField(max_length=50)
    result = models.TextField()
    checked_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.checked_at}"


class GovernmentScheme(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    category = models.CharField(max_length=100)
    description = models.TextField()
    eligibility = models.TextField()
    benefits = models.TextField()
    official_url = models.URLField()

    # Age criteria
    min_age = models.PositiveIntegerField(default=0)
    max_age = models.PositiveIntegerField(default=120)

    # Maximum annual family income; blank means no limit configured
    max_annual_income = models.PositiveIntegerField(
        null=True,
        blank=True
    )

    # Optional occupation requirement
    required_occupation = models.CharField(
        max_length=100,
        blank=True
    )

    # Optional state requirement
    required_state = models.CharField(
        max_length=100,
        blank=True
    )

    # Additional eligibility requirements
    requires_land_ownership = models.BooleanField(default=False)

    requires_no_pucca_house = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
