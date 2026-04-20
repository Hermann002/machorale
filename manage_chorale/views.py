from django.shortcuts import render, redirect
from django.views.generic import TemplateView, ListView
from .forms import CreateChoraleForm, AddMemberForm, ConfChoraleForm
from django.contrib import messages
from django.urls import reverse
from django.http import HttpResponseRedirect
from formtools.wizard.views import SessionWizardView
from django.core.files.storage import FileSystemStorage
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.decorators import login_required
from django.utils import formats
from datetime import datetime
from functools import lru_cache
import json
import os
from .models import Chorale
from manage_users.models import CustomUser, Profile
from django.contrib.auth.mixins import LoginRequiredMixin
from .mixins import ChoraleRequireMixin
from .services import get_dashboard_stats


@lru_cache(maxsize=1)
def load_recent_activities():
    fake_data_path = settings.BASE_DIR / 'fake_data.json'
    try:
        with open(fake_data_path, encoding='utf-8') as f:
            data = json.load(f)
        return data.get('fake_recents_events', [])
    except (FileNotFoundError, json.JSONDecodeError):
        return []


class DashboardView(ChoraleRequireMixin, TemplateView):
    template_name = "pages/dashboard.html"

    def get(self, request, slug, *args, **kwargs):
        stats = get_dashboard_stats(self.chorale.id)
        total_members = stats.get("total_members", 0)
        last_meeting_date = formats.date_format(datetime(2024, 5, 20), "M d, Y")
        current_balance = 1_000_000.00
        pending_sanctions = 5

        increase_members = 2
        number_absentees = 4
        increase_balance = 10
        increase_sanctions = 1

        recent_activities = load_recent_activities()

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
        return render(request, self.template_name, {**context, "slug": self.chorale.slug})
    

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
        if not getattr(request.user, 'is_verify', False):
            messages.error(request, "You need to verify your email before creating a chorale.")
            return redirect(reverse('home'))

        try:
            managed_chorale = request.user.managed_group
        except ObjectDoesNotExist:
            managed_chorale = None

        if managed_chorale:
            messages.info(request, "You already manage a chorale. Redirecting to your dashboard.")
            return redirect(reverse('dashboard', kwargs={"slug": managed_chorale.slug}))

        return super().get(request, *args, **kwargs)

    def done(self, form_list, **kwargs):
        user = self.request.user
        try:
            # Récupérer toutes les données nettoyées
            data = self.get_all_cleaned_data()
            print(data)
            
            # Découper le champ "location" en city/country (simplifié pour l'exemple)
            location = data.get('location', '')
            city = location.split(',')[0].strip() if ',' in location else location
            country = location.split(',')[-1].strip() if ',' in location else 'France'
            address = location  # À améliorer avec un champ dédié plus tard
            
            # Créer la chorale
            chorale = Chorale(
                logo = data['logo'], # if data.get('logo') else None,
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
            return redirect(reverse('dashboard', kwargs={"slug": chorale.slug}))
            
        except Exception as e:
            print(f"Erreur lors de la création de la chorale: {e}")
            messages.error(self.request, "Une erreur est survenue lors de la création de la chorale.")
            return redirect(reverse('dashboard'))
    

class ListMembersView(ChoraleRequireMixin, ListView):
    template_name = "pages/members.html"
    model = CustomUser
    context_object_name = "members"
    paginate_by = 5
    slug_url_kwarg = "slug"
    
    # filter to be implemented later

    def get_queryset(self):
        if not hasattr(self, '_queryset'):
            self._queryset = CustomUser.objects.filter(chorales=self.chorale).select_related('profile')
        return self._queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        total_members = self.paginator.count if hasattr(self, 'paginator') else len(self.get_queryset())
        context["page_title"] = "Membres de la chorale"
        context["total_members"] = total_members
        context["slug"] = self.chorale.slug
        return context

class ContributionView(ChoraleRequireMixin, TemplateView):
    template_name = "pages/contributions.html"

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name)
    
class MemberPopupView(ChoraleRequireMixin, TemplateView):
    template_name = "pages/member_popup.html"
    form_class = AddMemberForm


    def get(self, request, slug,*args, **kwargs):
        return render(request, self.template_name, {"form": self.form_class(), "slug": slug})
    
    def post(self, request, slug, *args, **kwargs):
        form = AddMemberForm(request.POST)
        chorale = self.chorale

        if form.is_valid():
            email = form['email'].value()
            first_name = form['first_name'].value()
            last_name = form['last_name'].value()
            contact_phone = form['contact_phone'].value()
            role = form['role'].value()
            username = email.split('@')[0].lower()
            try:
                member = CustomUser.objects.create_user(
                    username=username,
                    email=email,
                    password="defaultpassword123",
                    first_name=first_name,
                    last_name=last_name,
                    role=role,
                )
                Profile.objects.create(user=member, _contact=contact_phone)
                chorale.members.add(member)

                messages.success(request, f"{member.get_full_name()} a été ajouté en tant que {member.get_role_display()} avec succès !")
                return redirect(reverse('members', kwargs={"slug": slug}))
            except Exception as e:
                messages.error(request, "Une erreur est survenue lors de l'ajout du membre.")
                return redirect(reverse('members', kwargs={"slug": slug}))


@login_required
def close_popup(request):
    return render(request, "pages/close_popup.html")

@login_required
def sidebar_toggle(request, slug):
    sidebar_open = request.GET.get('open') == '1'
    return render(request, "base/navbar.html", {"sidebar_open": sidebar_open, "slug": slug})