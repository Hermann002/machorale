from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import TemplateView, ListView
from .forms import CreateChoraleForm, AddMemberForm, ConfChoraleForm, MemberRoleForm
from django.contrib import messages
from django.urls import reverse
from django.http import HttpResponseRedirect
from formtools.wizard.views import SessionWizardView
from django.core.files.storage import FileSystemStorage
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.decorators import login_required
from django.utils import formats, timezone
from datetime import datetime, date, timedelta
from functools import lru_cache
import calendar
import json
import os
from .models import Chorale, Event as ActivityEvent, ChoraleEvent
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
        upcoming_event_count = stats.get("upcoming_event_count", 0)
        last_meeting_date = formats.date_format(timezone.now(), "M d, Y")
        current_balance = 1_000_000.00
        pending_sanctions = 5

        increase_members = 2
        number_absentees = 4
        increase_balance = 10
        increase_sanctions = 1

        recent_events = list(ActivityEvent.objects.filter(chorale=self.chorale).order_by('-timestamp')[:5])
        recent_activities = recent_events if recent_events else load_recent_activities()

        upcoming_practices = ChoraleEvent.objects.filter(
            chorale=self.chorale,
            date__gte=timezone.now(),
            event_type=ChoraleEvent.EVENT_TYPE_CHOICES[0][0],
        ).order_by('date')[:3]
        upcoming_events = ChoraleEvent.objects.filter(chorale=self.chorale, date__gte=timezone.now()).order_by('date')[:4]

        if upcoming_events:
            last_meeting_date = formats.date_format(upcoming_events[0].date, "M d, Y")

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
            "upcoming_practices": upcoming_practices,
            "upcoming_events": upcoming_events,
            "upcoming_event_count": upcoming_event_count,
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
            user.role = CustomUser.ROLE_SUPERADMIN_CHORALE
            user.save()

            messages.success(self.request, "Votre chorale a été créée avec succès !")
            return redirect(reverse('dashboard', kwargs={"slug": chorale.slug}))
            
        except Exception as e:
            print(f"Erreur lors de la création de la chorale: {e}")
            messages.error(self.request, "Une erreur est survenue lors de la création de la chorale.")
            return redirect(reverse('home'))
    

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

class UpdateMemberRoleView(ChoraleRequireMixin, TemplateView):
    template_name = "pages/member_role.html"
    form_class = MemberRoleForm

    def dispatch(self, request, *args, **kwargs):
        # Seul l'admin peut modifier les rôles des membres
        if request.user.role != CustomUser.ROLE_SUPERADMIN_CHORALE:
            messages.error(request, "Vous n'avez pas la permission de modifier les rôles.")
            return redirect(reverse('home'))
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, slug, user_id, *args, **kwargs):
        member = get_object_or_404(CustomUser, id=user_id, chorales=self.chorale)
        form = self.form_class(instance=member)
        return render(request, self.template_name, {
            "form": form,
            "member": member,
            "slug": self.chorale.slug,
        })

    def post(self, request, slug, user_id, *args, **kwargs):
        member = get_object_or_404(CustomUser, id=user_id, chorales=self.chorale)
        form = self.form_class(request.POST, instance=member)
        if form.is_valid():
            form.save()
            messages.success(request, f"Le rôle de {member.get_full_name()} a bien été mis à jour.")
            return redirect(reverse('members', kwargs={"slug": self.chorale.slug}))

        return render(request, self.template_name, {
            "form": form,
            "member": member,
            "slug": self.chorale.slug,
        })


class EventListView(ChoraleRequireMixin, TemplateView):
    template_name = "pages/events.html"

    def get(self, request, slug, *args, **kwargs):
        today = timezone.localtime().date()
        year = int(request.GET.get("year", today.year))
        month = int(request.GET.get("month", today.month))

        event_queryset = ChoraleEvent.objects.filter(chorale=self.chorale)
        upcoming_events = event_queryset.filter(date__gte=timezone.now()).order_by('date')[:6]
        month_events = event_queryset.filter(date__year=year, date__month=month).order_by('date')

        event_calendar = {}
        for event in month_events:
            event_date = event.date.date()
            event_calendar.setdefault(event_date, []).append(event)

        first_weekday, days_in_month = calendar.monthrange(year, month)
        weeks = []
        week = []
        for _ in range(first_weekday):
            week.append(None)

        for day in range(1, days_in_month + 1):
            current_date = date(year, month, day)
            week.append({
                'day': current_date,
                'events': event_calendar.get(current_date, []),
            })
            if len(week) == 7:
                weeks.append(week)
                week = []

        if week:
            while len(week) < 7:
                week.append(None)
            weeks.append(week)

        previous_month = date(year, month, 1) - timedelta(days=1)
        next_month = date(year, month, days_in_month) + timedelta(days=1)

        context = {
            "page_title": "Calendrier des événements",
            "calendar_weeks": weeks,
            "weekdays": ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"],
            "current_month": calendar.month_name[month],
            "current_year": year,
            "previous_month": previous_month,
            "next_month": next_month,
            "upcoming_events": upcoming_events,
            "slug": self.chorale.slug,
        }
        return render(request, self.template_name, context)

class CreateEventView(ChoraleRequireMixin, TemplateView):
    template_name = "pages/event_form.html"
    form_class = None

    def dispatch(self, request, *args, **kwargs):
        if not (request.user.role == CustomUser.ROLE_SUPERADMIN_CHORALE or request.user.chorale_role == CustomUser.CHORALE_ROLE_SECRETARY):
            messages.error(request, "Vous n'avez pas la permission de créer un événement.")
            return redirect(reverse('dashboard', kwargs={"slug": kwargs.get('slug')}))
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, slug, *args, **kwargs):
        from .forms import ChoraleEventForm
        form = ChoraleEventForm()
        return render(request, self.template_name, {"form": form, "slug": self.chorale.slug})

    def post(self, request, slug, *args, **kwargs):
        from .forms import ChoraleEventForm
        form = ChoraleEventForm(request.POST, request.FILES)
        if form.is_valid():
            event = form.save(commit=False)
            event.chorale = self.chorale
            event.created_by = request.user
            event.save()

            ActivityEvent.log(
                chorale=self.chorale,
                user=request.user,
                event_type='other',
                description=f"Événement créé : {event.title}",
                metadata={"event_id": event.id, "title": event.title},
                request=request,
            )

            messages.success(request, "L'événement a été créé avec succès.")
            return redirect(reverse('events', kwargs={"slug": self.chorale.slug}))

        return render(request, self.template_name, {"form": form, "slug": self.chorale.slug})

class EventDetailView(ChoraleRequireMixin, TemplateView):
    template_name = "pages/event_detail.html"

    def get(self, request, slug, event_id, *args, **kwargs):
        event = get_object_or_404(ChoraleEvent, id=event_id, chorale=self.chorale)
        return render(request, self.template_name, {"event": event, "slug": self.chorale.slug})

class EventTableView(ChoraleRequireMixin, TemplateView):
    template_name = "pages/events_list.html"

    def get(self, request, slug, *args, **kwargs):
        events = ChoraleEvent.objects.filter(
            chorale=self.chorale
        ).select_related('created_by').order_by('-date')
        can_create = (
            request.user.role == CustomUser.ROLE_SUPERADMIN_CHORALE
            or request.user.chorale_role == CustomUser.CHORALE_ROLE_SECRETARY
        )
        return render(request, self.template_name, {
            'events': events,
            'slug': self.chorale.slug,
            'can_create': can_create,
        })

class EventUpdateView(ChoraleRequireMixin, TemplateView):
    template_name = "pages/event_form.html"

    def _can_edit(self, request):
        return (
            request.user.role == CustomUser.ROLE_SUPERADMIN_CHORALE
            or request.user.chorale_role == CustomUser.CHORALE_ROLE_SECRETARY
        )

    def dispatch(self, request, *args, **kwargs):
        if not self._can_edit(request):
            messages.error(request, "Vous n'avez pas la permission de modifier un événement.")
            return redirect(reverse('events', kwargs={"slug": kwargs.get('slug')}))
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, slug, event_id, *args, **kwargs):
        from .forms import ChoraleEventForm
        event = get_object_or_404(ChoraleEvent, id=event_id, chorale=self.chorale)
        form = ChoraleEventForm(instance=event)
        return render(request, self.template_name, {
            "form": form,
            "slug": self.chorale.slug,
            "event": event,
            "is_edit": True,
        })

    def post(self, request, slug, event_id, *args, **kwargs):
        from .forms import ChoraleEventForm
        event = get_object_or_404(ChoraleEvent, id=event_id, chorale=self.chorale)
        form = ChoraleEventForm(request.POST, request.FILES, instance=event)
        if form.is_valid():
            form.save()
            ActivityEvent.log(
                chorale=self.chorale,
                user=request.user,
                event_type='other',
                description=f"Événement modifié : {event.title}",
                metadata={"event_id": event.id, "title": event.title},
                request=request,
            )
            messages.success(request, "L'événement a été modifié avec succès.")
            return redirect(reverse('event_detail', kwargs={"slug": self.chorale.slug, "event_id": event.id}))
        return render(request, self.template_name, {
            "form": form,
            "slug": self.chorale.slug,
            "event": event,
            "is_edit": True,
        })

class ContributionView(ChoraleRequireMixin, TemplateView):
    template_name = "pages/contributions.html"

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name)
    
class MemberPopupView(ChoraleRequireMixin, TemplateView):
    template_name = "pages/member_popup.html"
    form_class = AddMemberForm

    def get_role_choices(self, request):
        """Retourne les choix de rôle selon le rôle de l'utilisateur"""
        if request.user.role == CustomUser.ROLE_SUPERADMIN_CHORALE:
            # Admin : tous les rôles disponibles
            return CustomUser.CHORALE_ROLE_CHOICES
        else:
            # Non-admin (secrétaire, censeur, trésorier) : seulement "member"
            return [
                (CustomUser.CHORALE_ROLE_MEMBER, 'Membre')
            ]

    def get_form(self, request):
        """Crée le formulaire et adapte les choix selon le rôle"""
        form = self.form_class(request.POST) if request.method == 'POST' else self.form_class()
        form.fields['role'].choices = self.get_role_choices(request)
        return form

    def get(self, request, slug, *args, **kwargs):
        form = self.get_form(request)
        return render(request, self.template_name, {"form": form, "slug": self.chorale.slug})
    
    def post(self, request, slug, *args, **kwargs):
        form = self.get_form(request)
        chorale = self.chorale

        if form.is_valid():
            # Validation supplémentaire : vérifier que le rôle choisi est autorisé pour l'utilisateur
            role = form['role'].value()
            allowed_roles = [choice[0] for choice in self.get_role_choices(request)]
            
            if role not in allowed_roles:
                messages.error(request, "Vous n'êtes pas autorisé à attribuer ce rôle.")
                return render(request, self.template_name, {"form": form, "slug": chorale.slug})
            
            email = form['email'].value()
            first_name = form['first_name'].value()
            last_name = form['last_name'].value()
            contact_phone = form['contact_phone'].value()
            username = email.split('@')[0].lower()
            try:
                member = CustomUser.objects.create_user(
                    username=username,
                    email=email,
                    password="defaultpassword123",
                    first_name=first_name,
                    last_name=last_name,
                    chorale_role=role,
                )
                Profile.objects.create(user=member, _contact=contact_phone)
                chorale.members.add(member)

                messages.success(request, f"{member.get_full_name()} a été ajouté en tant que {member.get_role_display()} avec succès !")
                return redirect(reverse('members', kwargs={"slug": chorale.slug}))
            except Exception as e:
                messages.error(request, "Une erreur est survenue lors de l'ajout du membre.")
                return redirect(reverse('members', kwargs={"slug": chorale.slug}))


@login_required
def close_popup(request):
    return render(request, "pages/close_popup.html")

@login_required
def sidebar_toggle(request, slug):
    sidebar_open = request.GET.get('open') == '1'
    return render(request, "base/navbar.html", {"sidebar_open": sidebar_open, "slug": slug})