from django.urls import path

from . import hrms, views

urlpatterns = [
    path("Users", views.scim_create_user, name="scim_create"),
    path("Users/<uuid:user_id>", views.scim_user_detail, name="scim_detail"),
    path("hrms-webhook", hrms.hrms_webhook, name="hrms_webhook"),
]
