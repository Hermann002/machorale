from django.shortcuts import render
# views.py
from django.http import JsonResponse
from django.db import connection
from django.conf import settings

def home(request, slug=None):
    return render(request, 'landing/pages/home.html', {"slug": slug})

def health_check(request):
    """
    Endpoint de health check pour les services externes.
    Retourne 200 si tout va bien, 503 sinon.
    """
    checks = {
        "database": False,
        "redis": False,
        "debug": settings.DEBUG,
    }
    status_code = 200

    # 🔍 Vérification base de données
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        checks["database"] = True
    except Exception as e:
        checks["database_error"] = str(e)
        status_code = 503

    # 🔍 Vérification Redis (si utilisé)
    try:
        from django.core.cache import cache
        cache.set("__health_check__", "ok", timeout=10)
        if cache.get("__health_check__") == "ok":
            checks["redis"] = True
        else:
            checks["redis_error"] = "Cache get failed"
            status_code = 503
    except Exception as e:
        checks["redis_error"] = str(e)
        status_code = 503

    return JsonResponse(checks, status=status_code)