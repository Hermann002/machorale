from django.urls import reverse

from .tasks import send_link_to_user, send_code_to_user as send_code_to_user_task


def send_code_to_user(email, code):
    return send_code_to_user_task.delay(email, code)

def send_password_reset_link(email, uidb64, token):
    return send_link_to_user.delay(email, uidb64, token)


def resolve_post_login_redirect(user, session):
    """Décide où renvoyer un utilisateur juste après login (ou retour sur /).

    Règles :
    - 0 membership  → wizard de création de chorale
    - 1 membership  → dashboard de cette chorale (slug stocké en session)
    - N membership  → si ``session['active_chorale_slug']`` pointe encore vers
      une membership valide, dashboard de cette chorale (stickiness) ;
      sinon, écran de sélection.
    """
    memberships = list(
        user.memberships.select_related('chorale').only(
            'chorale__slug', 'is_admin', 'joined_at',
        )
    )
    count = len(memberships)

    if count == 0:
        return reverse('create_chorale')

    if count == 1:
        slug = memberships[0].chorale.slug
        session['active_chorale_slug'] = slug
        return reverse('dashboard', kwargs={'slug': slug})

    active = session.get('active_chorale_slug')
    if active and any(m.chorale.slug == active for m in memberships):
        return reverse('dashboard', kwargs={'slug': active})

    return reverse('select_chorale')