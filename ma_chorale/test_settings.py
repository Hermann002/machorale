from .settings import *
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",  # ultra rapide
    }
}

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"  # capture les emails en mémoire pour les tests
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True