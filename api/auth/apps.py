from django.apps import AppConfig


class AuthConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'api.auth'
    label = 'iam_auth'
    verbose_name = 'Authentication Service'
