from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib.auth.mixins import LoginRequiredMixin

class ChoraleRequireMixin(LoginRequiredMixin):
    chorale_url_kwargs = 'slug'

    def dispatch(self, request, *args, **kwargs):
        chorale = None

        slug = kwargs.get(self.chorale_url_kwargs)
        if slug:
            from manage_chorale.models import Chorale
            try:
                chorale = Chorale.objects.get(slug=slug, admin=request.user)
            except Chorale.DoesNotExist:
                messages.error(request, "Cette chorale n'existe pas, Vous devez créer une chorale !")
                return redirect(reverse('create_chorale'))
        
        if chorale is None:
            messages.info(request, "Vous devez créer une chorale !")
            return redirect(reverse('create_chorale'))

        self.chorale = chorale
        return super().dispatch(request, *args, **kwargs)