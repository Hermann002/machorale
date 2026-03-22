from django.shortcuts import render
from django.views.generic import TemplateView, ListView
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
from .models import Chorale, Event
from manage_users.models import CustomUser
from django.db.models import Q
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import formats
from datetime import datetime
import json

class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "pages/dashboard.html"
    total_members = 42
    last_meeting_date = formats.date_format(datetime(2024, 5, 20), "M d, Y")
    current_balance = 1_000_000.00
    pending_sanctions = 5

    increase_members = 3
    number_absentees = 4
    increase_balance = 10
    increase_sanctions = 1

    recent_activities = Event.objects.filter(is_important=True)[:5]
    # for 

    with open("./fake_data.json", "r") as f:
        fake_data = json.load(f)
    recent_activities = fake_data["fake_recents_events"]

    context = {
        "page_title": "Tableau de bord",
        "total_members": total_members,
        "last_meeting_date": last_meeting_date,
        "current_balance": current_balance,
        "pending_sanctions": pending_sanctions,
        "increase_members": increase_members,
        "number_absentees": number_absentees,
        "increase_balance": increase_balance,
        "increase_sanctions": increase_sanctions,
        "recent_activities": recent_activities,
    }

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name, context=self.context)
    

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
        user = self.request.user
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
            chorale.members.add(user)
            user.role = 'super_admin_chorale'
            user.save()

            messages.success(self.request, "Votre chorale a été créée avec succès !")
            return redirect(reverse('dashboard'))
            
        except Exception as e:
            print(f"Erreur lors de la création de la chorale: {e}")
            messages.error(self.request, "Une erreur est survenue lors de la création de la chorale.")
            return redirect(reverse('dashboard'))
    

class ListMembersView(LoginRequiredMixin, ListView):
    template_name = "pages/members.html"
    model = CustomUser
    context_object_name = "members"
    paginate_by = 10

    def get_queryset(self):
        user = self.request.user
        chorales = user.chorales.all()
        members = CustomUser.objects.filter(chorales__in=chorales).distinct()
        return members 

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Membres de la chorale"
        return context

class ContributionView(LoginRequiredMixin, TemplateView):
    template_name = "pages/contributions.html"

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name)
    
