from django.contrib import admin
from .models import SchemeAlert, EligibilityHistory, GovernmentScheme


@admin.register(SchemeAlert)
class SchemeAlertAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "created_at")
    search_fields = ("title", "category")


@admin.register(EligibilityHistory)
class EligibilityHistoryAdmin(admin.ModelAdmin):
    list_display = ("user", "age", "income", "occupation", "checked_at")
    search_fields = ("user__username", "occupation")


@admin.register(GovernmentScheme)
class GovernmentSchemeAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "slug", "created_at")
    list_filter = ("category",)
    search_fields = ("name", "category", "description")
    prepopulated_fields = {"slug": ("name",)}
