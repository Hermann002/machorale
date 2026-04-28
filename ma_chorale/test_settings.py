from .settings import *

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"  # capture les emails en mémoire pour les tests
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True