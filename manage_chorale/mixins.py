from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils.translation import gettext_lazy as _


class RateLimitedMixin:
    """Applique un rate limit sur les requêtes mutantes (POST par défaut).

    Utilisation dans une vue :
        class MyView(RateLimitedMixin, SomeOtherMixin, TemplateView):
            rl_rate   = '10/m'          # surcharger si besoin
            rl_key    = 'user_or_ip'    # 'ip' pour les vues publiques
            rl_methods = ('POST',)      # ('GET', 'POST') pour les vues créant des objets sur GET

    Le mixin doit être listé EN PREMIER dans les bases pour s'exécuter avant
    les autres dispatch (auth, rôle, …).
    Sur dépassement : message d'erreur Django + redirect vers la même URL (GET).
    """

    rl_rate: str = '20/m'
    rl_key: str = 'user_or_ip'
    rl_methods: tuple = ('POST',)

    def dispatch(self, request, *args, **kwargs):
        from django_ratelimit.core import is_ratelimited

        if request.method in self.rl_methods:
            limited = is_ratelimited(
                request,
                group=self.__class__.__name__,
                key=self.rl_key,
                rate=self.rl_rate,
                increment=True,
            )
            if limited:
                messages.error(
                    request,
                    _("Trop de requêtes. Veuillez patienter avant de réessayer."),
                )
                return redirect(request.get_full_path())

        return super().dispatch(request, *args, **kwargs)


class ChoraleRequireMixin(LoginRequiredMixin):
    """Résout la chorale (depuis le slug) et l'appartenance courante via Membership.

    Attache ``self.chorale`` et ``self.membership`` pour usage dans la vue.
    Les sous-classes peuvent surcharger ``_check_role`` pour ajouter un filtre
    de rôle (exécuté AVANT que ``get``/``post`` ne tourne — pas d'effet de bord
    parasite).
    """

    chorale_url_kwargs = 'slug'

    def _resolve_membership(self, request, **kwargs):
        from manage_chorale.models import Membership

        slug = kwargs.get(self.chorale_url_kwargs)
        if not slug:
            # Toutes les URLs scope-chorale incluent <slug:slug>/. Une absence ici
            # signifie un câblage cassé côté URL conf — préférable d'envoyer vers
            # le sélecteur plutôt que de masquer le bug.
            return redirect(reverse('select_chorale'))

        try:
            membership = (
                Membership.objects
                .select_related('chorale')
                .get(chorale__slug=slug, user=request.user)
            )
        except Membership.DoesNotExist:
            messages.error(request, "Vous n'êtes pas membre de cette chorale !")
            return redirect(reverse('select_chorale'))

        self.membership = membership
        self.chorale = membership.chorale
        # Sticky : on garde la chorale active en session pour le switcher
        # et pour la redirection sticky depuis /, /login, etc.
        request.session['active_chorale_slug'] = membership.chorale.slug
        return None

    def _check_role(self, request):
        """Hook : retourne une réponse de redirection si l'accès doit être refusé."""
        return None

    def dispatch(self, request, *args, **kwargs):
        # LoginRequiredMixin doit s'exécuter en premier (auth check)
        if not request.user.is_authenticated:
            return super().dispatch(request, *args, **kwargs)

        deny = self._resolve_membership(request, **kwargs)
        if deny is not None:
            return deny

        deny = self._check_role(request)
        if deny is not None:
            return deny

        return super().dispatch(request, *args, **kwargs)


class RoleRequireMixin(ChoraleRequireMixin):
    """Filtre l'accès par rôle Membership.

    Convention : ``is_admin=True`` bypass toujours le filtre.
    """

    allowed_chorale_roles: list[str] = []
    permission_denied_message = "Vous n'avez pas la permission d'accéder à cette page."
    permission_denied_redirect = 'dashboard'

    def _check_role(self, request):
        if self.membership.is_admin:
            return None
        if self.membership.role not in self.allowed_chorale_roles:
            messages.error(request, self.permission_denied_message)
            return redirect(reverse(self.permission_denied_redirect,
                                    kwargs={'slug': self.chorale.slug}))
        return None


class AdminRequiredMixin(RoleRequireMixin):
    """Réserve l'accès à l'admin de la chorale (Membership.is_admin)."""

    allowed_chorale_roles: list[str] = []  # personne d'autre que l'admin
    permission_denied_message = "Accès réservé à l'admin de la chorale."


class TreasurerRequiredMixin(RoleRequireMixin):
    allowed_chorale_roles = ['treasurer']
    permission_denied_message = "Accès réservé au trésorier de la chorale."


class CensorRequiredMixin(RoleRequireMixin):
    allowed_chorale_roles = ['censor']
    permission_denied_message = "Accès réservé au censeur de la chorale."


class SecretaryOrAdminRequiredMixin(RoleRequireMixin):
    allowed_chorale_roles = ['secretary']
    permission_denied_message = "Accès réservé au secrétaire ou à l'admin de la chorale."
