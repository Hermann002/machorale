from django.contrib import messages
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