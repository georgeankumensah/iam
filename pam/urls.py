from django.urls import path

from . import views

urlpatterns = [
    path("sessions", views.start_session, name="pam_start"),
    path("sessions/<uuid:session_id>/end", views.end_session, name="pam_end"),
]
