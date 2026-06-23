from .base import *

DEBUG = True

# Dev only: accept any Host (localhost, 127.0.0.1, WSL IP, LAN IP for the mobile
# app). Never used in prod — prod.py keeps the strict ALLOWED_HOSTS from .env.
ALLOWED_HOSTS = ['*']

WHITENOISE_AUTOREFRESH = DEBUG

# Dev : pas de SMTP réel. Les emails (OTP, reset) sont imprimés dans la console
# où tourne runserver — copier le code OTP depuis le terminal.
# Pour tester un vrai envoi SendGrid en local, recommenter le bloc SMTP ci-dessous.
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
DEFAULT_FROM_EMAIL = config('defaultfromemail', default='noreply@localhost')

# EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
# EMAIL_HOST = config('emailhost')
# EMAIL_PORT = config('emailport', cast=int)
# EMAIL_USE_TLS = config('emailuse-tls', default=True, cast=bool)
# EMAIL_HOST_USER = config('emailuser')
# EMAIL_HOST_PASSWORD = config('emailpassword')

CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

SITE_URL = 'http://localhost:8000'