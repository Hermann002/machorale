def current_membership(request):
    """Expose la Membership active + la liste des memberships du user au template.

    Variables injectées :
    - ``current_membership`` : Membership active (slug URL > session sticky)
    - ``user_memberships``   : QuerySet de toutes les memberships du user (pour
      le dropdown switcher dans la navbar)
    - ``active_chorale_slug``: slug en session (utile sur ``select_chorale``
      hors mixin)

    Retourne tout à ``None``/vide pour les utilisateurs anonymes.
    """
    empty = {
        'current_membership': None,
        'user_memberships': [],
        'active_chorale_slug': None,
    }

    if not getattr(request, 'user', None) or not request.user.is_authenticated:
        return empty

    from manage_chorale.models import Membership

    slug = None
    match = getattr(request, 'resolver_match', None)
    if match:
        slug = match.kwargs.get('slug')
    active_session_slug = request.session.get('active_chorale_slug') if hasattr(request, 'session') else None
    if not slug:
        slug = active_session_slug

    qs = (
        Membership.objects
        .select_related('chorale')
        .filter(user=request.user)
        .order_by('-is_admin', 'joined_at')
    )

    membership = None
    if slug:
        membership = qs.filter(chorale__slug=slug).first()
    if membership is None:
        membership = qs.first()

    return {
        'current_membership': membership,
        'user_memberships': qs,
        'active_chorale_slug': active_session_slug,
    }
