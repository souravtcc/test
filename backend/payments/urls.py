from django.urls import path

from . import views


urlpatterns = [
    path("admin-debug/", views.admin_debug),
    path("config/", views.payment_config),
    path("dashboard/", views.dashboard),
    path("wallets/connect/", views.connect_wallet),
    path("create/", views.create_payment),
    path("<int:payment_id>/submit/", views.submit_payment),
    path("<int:payment_id>/", views.payment_detail),
]
