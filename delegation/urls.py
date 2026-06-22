from django.urls import path

from . import views

urlpatterns = [
    path("webhook", views.webhook, name="delegation_webhook"),
]
