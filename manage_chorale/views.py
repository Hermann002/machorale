from django.shortcuts import render
from django.views.generic import TemplateView
from .forms import CreateChoraleForm
from django.contrib import messages
from django.urls import reverse
from django.http import HttpResponseRedirect

class DashboardView(TemplateView):
    template_name = "pages/dashboard.html"

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name, context={"page_title": "Tableau de bord"})
    
class CreateChoraleView(TemplateView):
    template_name = "pages/create_chorale.html"

    def get(self, request, *args, **kwargs):
        try:
            if request.user.is_verify is False:
                print(request.user.is_verify)
                messages.error(request, "You need to verify your email before creating a chorale.")
                return HttpResponseRedirect(reverse('dashboard'))
        except AttributeError as e:
            print(f"AttributeError: {e}")
            messages.error(request, "You need to be logged in to create a chorale.")
            return HttpResponseRedirect(reverse('dashboard'))
        form = CreateChoraleForm()
        return render(request, self.template_name, context={"page_title": "Créer une chorale", "form": form})
    
    def post(self, request, *args, **kwargs):
        form = CreateChoraleForm(request.POST)
        
        if form.is_valid():
            chorale = form.save(commit=False)
            chorale.admin = request.user
            chorale.save()
            return render(request, "pages/dashboard.html", context={"page_title": "Tableau de bord", "success_message": "Chorale créée avec succès."})
        return render(request, self.template_name, context={"page_title": "Créer une chorale", "form": form})
    
class ConfChoraleView(TemplateView):
    template_name = "pages/conf-chorale.html"

    def get(self, request, *args, **kwargs):
        try:
            if request.user.is_verify is False:
                print(request.user.is_verify)
                messages.error(request, "You need to verify your email before configurate a chorale.")
                return HttpResponseRedirect(reverse('dashboard'))
        except AttributeError as e:
            print(f"AttributeError: {e}")
            messages.error(request, "You need to be logged in to configurate a chorale.")
            return HttpResponseRedirect(reverse('dashboard'))
        form = CreateChoraleForm()
        return render(request, self.template_name, context={"page_title": "Configurer votre chorale", "form": form})