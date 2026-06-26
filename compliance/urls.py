from django.urls import path

from . import views

urlpatterns = [
    path("", views.residency_list, name="admin_residency"),
    path("<uuid:residency_id>/review", views.residency_review, name="admin_residency_review"),
    path("dpia", views.dpia_list, name="admin_dpia"),
]
