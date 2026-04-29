from .base import *

DEBUG = True

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