from django.urls import path

from . import views

urlpatterns = [
    path("sessions", views.session_list, name="pam_list"),
    path("sessions/<uuid:session_id>/end", views.end_session, name="pam_end"),
    path("sessions/<uuid:session_id>/revoke", views.revoke_session, name="pam_revoke"),
]
