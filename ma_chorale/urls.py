"""URL configuration for ma_chorale project."""
from django.conf import settings
from django.contrib import admin
from django.http import HttpResponseRedirect
from django.urls import path, include, translate_url
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import check_for_language, override
from django.views.decorators.http import require_POST
from django.conf.urls.i18n import i18n_patterns


@require_POST
def set_language(request):
    """Drop-in replacement for django.views.i18n.set_language.

    Resolves `next` under its source language (detected from the URL prefix)
    before translating to the target language, so URL swaps like
    /en/u/login/ -> /fr/u/login/ work even when the active locale on the
    /i18n/setlang/ request doesn't match the source URL's prefix.
    """
    lang_code = request.POST.get("language")
    next_url = request.POST.get("next") or request.headers.get("Referer") or "/"

    if lang_code and check_for_language(lang_code):
        available = [code for code, _name in settings.LANGUAGES]
        source_lang = settings.LANGUAGE_CODE
        for code in available:
            if next_url.startswith(f"/{code}/") or next_url == f"/{code}":
                source_lang = code
                break

        with override(source_lang):
            translated = translate_url(next_url, lang_code)

        if not url_has_allowed_host_and_scheme(
            url=translated,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure(),
        ):
            translated = "/"

        response = HttpResponseRedirect(translated)
        response.set_cookie(
            settings.LANGUAGE_COOKIE_NAME,
            lang_code,
            max_age=settings.LANGUAGE_COOKIE_AGE,
            path=settings.LANGUAGE_COOKIE_PATH,
            domain=settings.LANGUAGE_COOKIE_DOMAIN,
            secure=settings.LANGUAGE_COOKIE_SECURE,
            httponly=settings.LANGUAGE_COOKIE_HTTPONLY,
            samesite=settings.LANGUAGE_COOKIE_SAMESITE,
        )
        return response

    return HttpResponseRedirect(next_url)


urlpatterns = [
    path('admin/', admin.site.urls),
    path('i18n/setlang/', set_language, name='set_language'),
]

urlpatterns += i18n_patterns(
    path('u/', include('manage_users.urls')),
    path('', include('landing.urls')),
    path('a/', include('manage_chorale.urls')),
    prefix_default_language=True,
)
