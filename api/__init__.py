# IAM API package
# Contains all API applications for the IAM system

__version__ = '1.0.0'
__author__ = 'IAM Team'

from .auth.apps import AuthConfig

__all__ = [
    'AuthConfig',
]
