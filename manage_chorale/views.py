from django.shortcuts import render
from django.views.generic import TemplateView
from .forms import CreateChoraleForm
from django.contrib import messages
from django.urls import reverse
from django.shortcuts import redirect
from django.http import HttpResponseRedirect
from formtools.wizard.views import SessionWizardView
from .forms import CreateChoraleForm, ConfChoraleForm
from django.core.files.storage import FileSystemStorage
from django.conf import settings
import os
from .models import Chorale

class DashboardView(TemplateView):
    template_name = "pages/dashboard.html"

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name, context={"page_title": "Tableau de bord"})
    

FORMS = [
    ("create", CreateChoraleForm),
    ("conf", ConfChoraleForm),
]

TEMPLATES = {
    "create": "pages/create_chorale.html",
    "conf": "pages/conf_chorale.html",
}


    
class CreateChoraleView(SessionWizardView):
    form_list = FORMS
    file_storage = FileSystemStorage(location=os.path.join(settings.MEDIA_ROOT, "temp"))

    def get_template_names(self):
        return [TEMPLATES[self.steps.current]]

    def get(self, request, *args, **kwargs):
        try:
            if not request.user.is_verify:
                messages.error(request, "You need to verify your email before creating a chorale.")
                return redirect(reverse('dashboard'))
        except AttributeError:
            messages.error(request, "You need to be logged in to create a chorale.")
            return redirect(reverse('dashboard'))
        return super().get(request, *args, **kwargs)

    def done(self, form_list, **kwargs):
        try:
            # Récupérer toutes les données nettoyées
            data = self.get_all_cleaned_data()
            
            # Découper le champ "location" en city/country (simplifié pour l'exemple)
            location = data.get('location', '')
            city = location.split(',')[0].strip() if ',' in location else location
            country = location.split(',')[-1].strip() if ',' in location else 'France'
            address = location  # À améliorer avec un champ dédié plus tard
            
            # Créer la chorale
            chorale = Chorale(
                name=data['name'],
                type_c=data['type_c'],
                description=data.get('description', ''),
                established_date=data.get('established_date'),
                country=country,
                city=city,
                address=address,
                contact_email=data.get('contact_email', ''),
                contact_phone=data.get('contact_phone', ''),
                slogan=data.get('slogan', ''),
                meeting_frequency=data.get('meeting_frequency', ''),
                admin=self.request.user,  # L'utilisateur connecté devient admin
            )
            
            # Sauvegarder le logo si présent
            if data.get('logo'):
                chorale.logo = data['logo']
            
            chorale.save()
            
            messages.success(self.request, "Votre chorale a été créée avec succès !")
            return redirect(reverse('dashboard'))
            
        except Exception as e:
            print(f"Erreur lors de la création de la chorale: {e}")
            messages.error(self.request, "Une erreur est survenue lors de la création de la chorale.")
            return redirect(reverse('dashboard'))
    
    # def post(self, request, *args, **kwargs):
    #     form = CreateChoraleForm(request.POST)
        
    #     if form.is_valid():
    #         chorale = form.save(commit=False)
    #         chorale.admin = request.user
    #         chorale.save()
    #         return render(request, "pages/dashboard.html", context={"page_title": "Tableau de bord", "success_message": "Chorale créée avec succès."})
    #     return render(request, self.template_name, context={"page_title": "Créer une chorale", "form": form})
    
