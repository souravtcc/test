from django.contrib import admin
from django.urls import include, path


urlpatterns = [
    path("admin/", admin.site.urls),
    path("receiver/", include("payments.receiver_urls")),
    path("api/payments/", include("payments.urls")),
]
