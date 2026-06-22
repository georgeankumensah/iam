from django.urls import path

from .views import audit, clients, roles, users

urlpatterns = [
    path("users", users.users_list, name="admin_users"),
    path("users/bulk-import", users.users_bulk_import, name="admin_users_bulk"),
    path("users/<uuid:user_id>", users.users_detail, name="admin_user_detail"),
    path("roles", roles.roles_list, name="admin_roles"),
    path("roles/<uuid:role_id>", roles.role_detail, name="admin_role_detail"),
    path("roles/<uuid:role_id>/bind", roles.role_bind, name="admin_role_bind"),
    path("clients", clients.clients_list, name="admin_clients"),
    path("clients/<uuid:client_id>", clients.client_detail, name="admin_client_detail"),
    path("clients/<uuid:client_id>/promote", clients.client_promote, name="admin_client_promote"),
    path("audit", audit.audit_search, name="admin_audit"),
    path("audit/export", audit.audit_export, name="admin_audit_export"),
]
