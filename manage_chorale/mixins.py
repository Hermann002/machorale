from django.contrib import messages
from django.http import HttpResponseRedirect
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib.auth.mixins import LoginRequiredMixin
from manage_users.models import CustomUser


class ChoraleRequireMixin(LoginRequiredMixin):
    chorale_url_kwargs = 'slug'

    def dispatch(self, request, *args, **kwargs):
        from manage_chorale.models import Chorale

        slug = kwargs.get(self.chorale_url_kwargs)
        chorale = None

        # Si l'utilisateur est admin de chorale
        if request.user.role == CustomUser.ROLE_SUPERADMIN_CHORALE:
            if slug:
                try:
                    chorale = Chorale.objects.select_related('admin').get(slug=slug, admin=request.user)
                except Chorale.DoesNotExist:
                    messages.error(request, "Cette chorale n'existe pas, Vous devez créer une chorale !")
                    return redirect(reverse('create_chorale'))

            if chorale is None:
                messages.info(request, "Vous devez créer une chorale !")
                return redirect(reverse('create_chorale'))
        else:
            # L'utilisateur n'est pas admin, récupérer la chorale où il est membre
            if slug:
                try:
                    chorale = Chorale.objects.get(slug=slug, members=request.user)
                except Chorale.DoesNotExist:
                    messages.error(request, "Vous n'êtes pas membre de cette chorale !")
                    return redirect(reverse('home'))
            else:
                # Pas de slug fourni, prendre la première chorale du membre
                chorale = request.user.chorales.first()
                if not chorale:
                    messages.info(request, "Vous n'êtes membre d'aucune chorale !")
                    return redirect(reverse('home'))

        self.chorale = chorale
        return super().dispatch(request, *args, **kwargs)


class RoleRequireMixin(ChoraleRequireMixin):
    """Filtre l'accès en fonction du chorale_role de l'utilisateur.

    Pattern: Template Method — on intercale un check entre la résolution de chorale
    (assurée par le parent) et le dispatch effectif vers la vue.

    Convention: les super_admin_chorale (admins de la chorale) bypassent toujours
    le filtre — ils peuvent tout faire dans leur chorale.
    """

    # Sous-classes : liste de chorale_role autorisés
    allowed_chorale_roles: list[str] = []
    permission_denied_message = "Vous n'avez pas la permission d'accéder à cette page."
    permission_denied_redirect = 'dashboard'

    def dispatch(self, request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)

        # Si le parent a déjà redirigé (chorale introuvable, etc.), on respecte sans surcharger.
        # Détection : la chorale n'a pas pu être attachée à self.
        if not getattr(self, 'chorale', None):
            return response

        # Admin de chorale : accès total dans sa chorale
        if request.user.role == CustomUser.ROLE_SUPERADMIN_CHORALE:
            return response

        # Membre lambda : check du chorale_role
        if request.user.chorale_role not in self.allowed_chorale_roles:
            messages.error(request, self.permission_denied_message)
            return redirect(reverse(self.permission_denied_redirect,
                                    kwargs={'slug': self.chorale.slug}))

        return response


class TreasurerRequiredMixin(RoleRequireMixin):
    allowed_chorale_roles = [CustomUser.CHORALE_ROLE_TREASURER]
    permission_denied_message = "Accès réservé au trésorier de la chorale."


class CensorRequiredMixin(RoleRequireMixin):
    allowed_chorale_roles = [CustomUser.CHORALE_ROLE_CENSOR]
    permission_denied_message = "Accès réservé au censeur de la chorale."
