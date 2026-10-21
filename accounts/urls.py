
from django.urls import path
from . import views

app_name = "accounts"

urlpatterns = [
    path("", views.home, name="home"),
    path("register/", views.register, name="register"),
    path("login/", views.user_login, name="login"),
    path("logout/", views.user_logout, name="logout"),

    path(
        "eligibility/",
        views.check_eligibility,
        name="eligibility",
    ),
    path(
        "eligibility/result/",
        views.eligibility_result,
        name="eligibility_result",
    ),

    path("history/", views.eligibility_history, name="history"),
    path("schemes/", views.schemes, name="schemes"),
    path(
        "schemes/<str:scheme_name>/",
        views.scheme_details,
        name="scheme_details",
    ),
    path("alerts/", views.live_alerts, name="alerts"),
    path("profile/", views.user_profile, name="profile"),
]
