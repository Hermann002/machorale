"""django-ratelimit glue for DRF views.

``is_ratelimited`` is the same primitive the web app's ``RateLimitedMixin``
uses. Here we translate a hit into a DRF ``Throttled`` (429) so it flows through
the custom exception handler and returns the standard ``{detail, errors}``
envelope instead of django-ratelimit's HTML 403.
"""
from django_ratelimit.core import is_ratelimited
from rest_framework.exceptions import Throttled


def email_key(group, request):
    """Rate-limit key derived from the request body's ``email`` (DRF parses the
    JSON body into ``request.data``, so ``post:email`` would not see it)."""
    return (request.data.get("email") or "").lower()


def enforce(request, *, group, key, rate, method=("POST",)):
    """Raise ``Throttled`` (429) if this request trips the limit, else no-op."""
    limited = is_ratelimited(
        request,
        group=group,
        key=key,
        rate=rate,
        method=list(method),
        increment=True,
    )
    if limited:
        raise Throttled()
