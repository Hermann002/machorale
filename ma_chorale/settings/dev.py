from .base import *

DEBUG = True

# Dev only: accept any Host (localhost, 127.0.0.1, WSL IP, LAN IP for the mobile
# app). Never used in prod — prod.py keeps the strict ALLOWED_HOSTS from .env.
ALLOWED_HOSTS = ['*']

WHITENOISE_AUTOREFRESH = DEBUG

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = config('emailhost')
EMAIL_PORT = config('emailport')
EMAIL_USE_TLS = config('emailusetls', default=True)
EMAIL_HOST_USER = config('emailuser')
EMAIL_HOST_PASSWORD = config('emailpassword')
DEFAULT_FROM_EMAIL = config('defaultfromemail')

CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

SITE_URL = 'http://localhost:8000'