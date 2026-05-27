from django.urls import path

from . import receiver_views


app_name = "receiver_dashboard"

urlpatterns = [
    path("", receiver_views.dashboard, name="dashboard"),
    path("login/", receiver_views.login_view, name="login"),
    path("logout/", receiver_views.logout_view, name="logout"),
]
