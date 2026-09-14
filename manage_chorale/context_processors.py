def current_membership(request):
    """Expose la Membership active + la liste des memberships du user au template."""
    empty = {
        "current_membership": None,
        "user_memberships": [],
        "active_chorale_slug": None,
    }

    if not getattr(request, "user", None) or not request.user.is_authenticated:
        return empty

    from manage_chorale.models import Membership

    # ✅ Si le mixin a déjà chargé le membership, on le réutilise
    # (via request._cached_membership défini dans le mixin)
    if hasattr(request, "_cached_membership"):
        membership = request._cached_membership
        # On a juste besoin de charger user_memberships pour le switcher
        user_memberships = (
            Membership.objects.select_related("chorale")
            .filter(user=request.user)
            .order_by("-is_admin", "joined_at")
        )
        return {
            "current_membership": membership,
            "user_memberships": user_memberships,
            "active_chorale_slug": request.session.get("active_chorale_slug"),
        }

    # ✅ Sinon (pages hors mixin), on fait la requête normale
    slug = None
    match = getattr(request, "resolver_match", None)
    if match:
        slug = match.kwargs.get("slug")
    active_session_slug = (
        request.session.get("active_chorale_slug")
        if hasattr(request, "session")
        else None
    )
    if not slug:
        slug = active_session_slug

    qs = (
        Membership.objects.select_related("chorale")
        .filter(user=request.user)
        .order_by("-is_admin", "joined_at")
    )

    membership = None
    if slug:
        membership = qs.filter(chorale__slug=slug).first()
    if membership is None:
        membership = qs.first()

    return {
        "current_membership": membership,
        "user_memberships": qs,
        "active_chorale_slug": active_session_slug,
    }
