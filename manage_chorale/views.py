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
from .models import Chorale, Membership, Event as ActivityEvent, ChoraleEvent, Contribution, MemberContribution, CashFlow, Absence, Sanction
from manage_users.models import CustomUser, Profile
from django.contrib.auth.mixins import LoginRequiredMixin
from .mixins import (
    ChoraleRequireMixin,
    TreasurerRequiredMixin,
    CensorRequiredMixin,
    AdminRequiredMixin,
    SecretaryOrAdminRequiredMixin,
)
from .services import get_dashboard_stats, ContributionService, SanctionService
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Sum, Q, Prefetch
from django.db import transaction
from django.utils.translation import gettext as _, ngettext


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
        # Vraies stats issues du service (anciens mocks supprimés)
        current_balance = stats.get("cash_balance", 0)
        pending_sanctions = stats.get("open_sanctions_count", 0)
        number_absentees = stats.get("unjustified_absences_this_month", 0)

        # Deltas non encore calculés (TODO: snapshots historiques pour comparer)
        increase_members = 0
        increase_balance = 0
        increase_sanctions = 0

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
            "page_title": _("Dashboard"),
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
            messages.error(request, _("You need to verify your email before creating a chorale."))
            return redirect(reverse('home'))

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
                created_by=user,
            )

            if data.get('logo'):
                chorale.logo = data['logo']

            chorale.save()
            Membership.objects.create(
                user=user,
                chorale=chorale,
                role=Membership.ROLE_ADMIN,
                is_admin=True,
            )
            self.request.session['active_chorale_slug'] = chorale.slug

            messages.success(self.request, _("Your chorale has been created successfully!"))
            return redirect(reverse('dashboard', kwargs={"slug": chorale.slug}))

        except Exception as e:
            print(f"Erreur lors de la création de la chorale: {e}")
            messages.error(self.request, _("An error occurred while creating the chorale."))
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
            self._queryset = CustomUser.objects.filter(
                chorales=self.chorale,
            ).select_related('profile').prefetch_related(
                Prefetch(
                    'memberships',
                    queryset=Membership.objects.filter(chorale=self.chorale),
                    to_attr='chorale_memberships',
                ),
            )
        return self._queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        total_members = self.paginator.count if hasattr(self, 'paginator') else len(self.get_queryset())
        context["page_title"] = _("Chorale members")
        context["total_members"] = total_members
        context["slug"] = self.chorale.slug
        return context

class UpdateMemberRoleView(AdminRequiredMixin, TemplateView):
    template_name = "pages/member_role.html"
    form_class = MemberRoleForm

    def _get_target(self, user_id):
        return get_object_or_404(
            Membership.objects.select_related('user'),
            user_id=user_id,
            chorale=self.chorale,
        )

    def get(self, request, slug, user_id, *args, **kwargs):
        target = self._get_target(user_id)
        form = self.form_class(instance=target)
        return render(request, self.template_name, {
            "form": form,
            "member": target.user,
            "slug": self.chorale.slug,
        })

    def post(self, request, slug, user_id, *args, **kwargs):
        target = self._get_target(user_id)
        form = self.form_class(request.POST, instance=target)
        if form.is_valid():
            form.save()
            messages.success(request, _("The role of %(name)s has been updated.") % {'name': target.user.get_full_name()})
            return redirect(reverse('members', kwargs={"slug": self.chorale.slug}))

        return render(request, self.template_name, {
            "form": form,
            "member": target.user,
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
            "page_title": _("Events calendar"),
            "calendar_weeks": weeks,
            "weekdays": [_("Mon"), _("Tue"), _("Wed"), _("Thu"), _("Fri"), _("Sat"), _("Sun")],
            "current_month": calendar.month_name[month],
            "current_year": year,
            "previous_month": previous_month,
            "next_month": next_month,
            "upcoming_events": upcoming_events,
            "slug": self.chorale.slug,
        }
        return render(request, self.template_name, context)

class CreateEventView(SecretaryOrAdminRequiredMixin, TemplateView):
    template_name = "pages/event_form.html"
    form_class = None
    permission_denied_message = "Accès réservé à l'admin ou au secrétaire de la chorale."

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

            messages.success(request, _("The event has been created successfully."))
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
        can_create = self.membership.is_admin or self.membership.role == Membership.ROLE_SECRETARY
        return render(request, self.template_name, {
            'events': events,
            'slug': self.chorale.slug,
            'can_create': can_create,
        })

class EventUpdateView(SecretaryOrAdminRequiredMixin, TemplateView):
    template_name = "pages/event_form.html"
    permission_denied_message = "Accès réservé à l'admin ou au secrétaire de la chorale."
    permission_denied_redirect = 'events'

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
            messages.success(request, _("The event has been updated successfully."))
            return redirect(reverse('event_detail', kwargs={"slug": self.chorale.slug, "event_id": event.id}))
        return render(request, self.template_name, {
            "form": form,
            "slug": self.chorale.slug,
            "event": event,
            "is_edit": True,
        })

# ── Trésorier ─────────────────────────────────────────────────────────────
#
# Toutes les vues ci-dessous héritent de TreasurerRequiredMixin :
# - super_admin_chorale → accès complet
# - chorale_role == 'treasurer' → accès complet
# - autres rôles → redirect vers dashboard avec message d'erreur
#
# Les listes (Contribution, MemberContribution, CashFlow) restent accessibles
# en lecture à tout membre via ChoraleRequireMixin si on l'utilisait — choix
# délibéré : ici on restreint TOUT, car les données financières sont sensibles.


class ContributionListView(ChoraleRequireMixin, TemplateView):
    template_name = "pages/treasurer/contribution_list.html"

    def get(self, request, slug, *args, **kwargs):
        contributions = (
            self.chorale.contributions
            .annotate(collected=Sum('payments__amount'))
            .order_by('-is_active', '-created_at')
        )
        return render(request, self.template_name, {
            'contributions': contributions,
            'slug': self.chorale.slug,
        })


class ContributionCreateView(TreasurerRequiredMixin, TemplateView):
    template_name = "pages/treasurer/contribution_form.html"

    def get(self, request, slug, *args, **kwargs):
        from .forms import ContributionForm
        form = ContributionForm(chorale=self.chorale)
        return render(request, self.template_name, {
            'form': form, 'slug': self.chorale.slug, 'is_edit': False,
        })

    def post(self, request, slug, *args, **kwargs):
        from .forms import ContributionForm
        form = ContributionForm(request.POST, chorale=self.chorale)
        if form.is_valid():
            contribution = form.save(commit=False)
            contribution.chorale = self.chorale  # ne JAMAIS faire confiance au form pour ça
            contribution.save()
            ActivityEvent.log(
                chorale=self.chorale, user=request.user, event_type='other',
                description=f"Type de cotisation créé : {contribution.title}",
                obj=contribution, request=request,
            )
            messages.success(request, _("Contribution type created."))
            return redirect(reverse('contributions', kwargs={'slug': self.chorale.slug}))
        return render(request, self.template_name, {
            'form': form, 'slug': self.chorale.slug, 'is_edit': False,
        })


class ContributionUpdateView(TreasurerRequiredMixin, TemplateView):
    template_name = "pages/treasurer/contribution_form.html"

    def _get_object(self, contribution_id):
        return get_object_or_404(Contribution, id=contribution_id, chorale=self.chorale)

    def get(self, request, slug, contribution_id, *args, **kwargs):
        from .forms import ContributionForm
        obj = self._get_object(contribution_id)
        form = ContributionForm(instance=obj, chorale=self.chorale)
        return render(request, self.template_name, {
            'form': form, 'slug': self.chorale.slug, 'contribution': obj, 'is_edit': True,
        })

    def post(self, request, slug, contribution_id, *args, **kwargs):
        from .forms import ContributionForm
        obj = self._get_object(contribution_id)
        form = ContributionForm(request.POST, instance=obj, chorale=self.chorale)
        if form.is_valid():
            form.save()
            ActivityEvent.log(
                chorale=self.chorale, user=request.user, event_type='other',
                description=f"Type de cotisation modifié : {obj.title}",
                obj=obj, request=request,
            )
            messages.success(request, _("Contribution type updated."))
            return redirect(reverse('contributions', kwargs={'slug': self.chorale.slug}))
        return render(request, self.template_name, {
            'form': form, 'slug': self.chorale.slug, 'contribution': obj, 'is_edit': True,
        })


class ContributionDeleteView(TreasurerRequiredMixin, TemplateView):
    """POST only — pas de page de confirmation séparée pour rester simple.
    Le bouton dans la liste demande confirmation côté JS."""

    def post(self, request, slug, contribution_id, *args, **kwargs):
        obj = get_object_or_404(Contribution, id=contribution_id, chorale=self.chorale)
        title = obj.title
        obj.delete()
        ActivityEvent.log(
            chorale=self.chorale, user=request.user, event_type='other',
            description=f"Type de cotisation supprimé : {title}",
            request=request,
        )
        messages.success(request, _("Contribution \"%(title)s\" deleted.") % {'title': title})
        return redirect(reverse('contributions', kwargs={'slug': self.chorale.slug}))

    def get(self, request, *args, **kwargs):
        # Empêche le retrait par GET (idempotence HTTP)
        return redirect(reverse('contributions', kwargs={'slug': kwargs.get('slug')}))


class MemberContributionListView(ChoraleRequireMixin, TemplateView):
    template_name = "pages/treasurer/payment_list.html"

    def get(self, request, slug, *args, **kwargs):
        payments = (
            MemberContribution.objects
            .filter(contribution__chorale=self.chorale)
            .select_related('contribution', 'member', 'recorded_by')
        )
        # Filtre optionnel par contribution / membre via query string
        contrib_id = request.GET.get('contribution')
        member_id = request.GET.get('member')
        if contrib_id:
            payments = payments.filter(contribution_id=contrib_id)
        if member_id:
            payments = payments.filter(member_id=member_id)

        total = payments.aggregate(s=Sum('amount'))['s'] or 0

        return render(request, self.template_name, {
            'payments': payments,
            'total': total,
            'slug': self.chorale.slug,
            'contributions': self.chorale.contributions.filter(is_active=True),
            'members': self.chorale.members.all(),
            'filter_contribution': contrib_id or '',
            'filter_member': member_id or '',
        })


class MemberContributionCreateView(TreasurerRequiredMixin, TemplateView):
    template_name = "pages/treasurer/payment_form.html"

    def get(self, request, slug, *args, **kwargs):
        from .forms import MemberContributionForm
        form = MemberContributionForm(chorale=self.chorale)
        return render(request, self.template_name, {
            'form': form, 'slug': self.chorale.slug,
        })

    def post(self, request, slug, *args, **kwargs):
        from .forms import MemberContributionForm
        form = MemberContributionForm(request.POST, chorale=self.chorale)
        if form.is_valid():
            try:
                # On délègue au service : centralise validation métier + audit
                ContributionService.record_payment(
                    contribution=form.cleaned_data['contribution'],
                    member=form.cleaned_data['member'],
                    amount=form.cleaned_data['amount'],
                    paid_at=form.cleaned_data.get('paid_at'),
                    note=form.cleaned_data.get('note', ''),
                    recorded_by=request.user,
                    request=request,
                )
            except DjangoValidationError as e:
                form.add_error(None, e.message)
                return render(request, self.template_name, {
                    'form': form, 'slug': self.chorale.slug,
                })
            messages.success(request, _("Payment recorded."))
            return redirect(reverse('payments', kwargs={'slug': self.chorale.slug}))
        return render(request, self.template_name, {
            'form': form, 'slug': self.chorale.slug,
        })


class CashFlowListView(ChoraleRequireMixin, TemplateView):
    template_name = "pages/treasurer/cashflow_list.html"

    def get(self, request, slug, *args, **kwargs):
        flows = self.chorale.cash_flows.select_related('created_by')
        cash_in = flows.filter(type_cash_flow=CashFlow.TYPE_ENTREE).aggregate(s=Sum('amount'))['s'] or 0
        cash_out = flows.filter(type_cash_flow=CashFlow.TYPE_SORTIE).aggregate(s=Sum('amount'))['s'] or 0
        return render(request, self.template_name, {
            'flows': flows,
            'cash_in': cash_in,
            'cash_out': cash_out,
            'balance': cash_in - cash_out,
            'slug': self.chorale.slug,
        })


class CashFlowCreateView(TreasurerRequiredMixin, TemplateView):
    template_name = "pages/treasurer/cashflow_form.html"

    def get(self, request, slug, *args, **kwargs):
        from .forms import CashFlowForm
        form = CashFlowForm()
        return render(request, self.template_name, {
            'form': form, 'slug': self.chorale.slug, 'is_edit': False,
        })

    def post(self, request, slug, *args, **kwargs):
        from .forms import CashFlowForm
        form = CashFlowForm(request.POST)
        if form.is_valid():
            flow = form.save(commit=False)
            flow.chorale = self.chorale
            flow.created_by = request.user
            flow.save()
            ActivityEvent.log(
                chorale=self.chorale, user=request.user, event_type='payment',
                description=(
                    f"{flow.get_type_cash_flow_display()} enregistrée : {flow.title} "
                    f"({flow.amount} XAF)"
                ),
                obj=flow, request=request,
            )
            messages.success(request, _("Cash flow entry recorded."))
            return redirect(reverse('cashflow', kwargs={'slug': self.chorale.slug}))
        return render(request, self.template_name, {
            'form': form, 'slug': self.chorale.slug, 'is_edit': False,
        })


class CashFlowUpdateView(TreasurerRequiredMixin, TemplateView):
    template_name = "pages/treasurer/cashflow_form.html"

    def _get_object(self, cashflow_id):
        return get_object_or_404(CashFlow, id=cashflow_id, chorale=self.chorale)

    def get(self, request, slug, cashflow_id, *args, **kwargs):
        from .forms import CashFlowForm
        flow = self._get_object(cashflow_id)
        form = CashFlowForm(instance=flow)
        return render(request, self.template_name, {
            'form': form, 'slug': self.chorale.slug, 'flow': flow, 'is_edit': True,
        })

    def post(self, request, slug, cashflow_id, *args, **kwargs):
        from .forms import CashFlowForm
        flow = self._get_object(cashflow_id)
        form = CashFlowForm(request.POST, instance=flow)
        if form.is_valid():
            form.save()
            ActivityEvent.log(
                chorale=self.chorale, user=request.user, event_type='payment',
                description=f"Mouvement de caisse modifié : {flow.title}",
                obj=flow, request=request,
            )
            messages.success(request, _("Cash flow entry updated."))
            return redirect(reverse('cashflow', kwargs={'slug': self.chorale.slug}))
        return render(request, self.template_name, {
            'form': form, 'slug': self.chorale.slug, 'flow': flow, 'is_edit': True,
        })


# ── Censeur ───────────────────────────────────────────────────────────────
#
# Toutes les vues ci-dessous héritent de CensorRequiredMixin :
# - super_admin_chorale → accès complet
# - chorale_role == 'censor' → accès complet
# - autres → redirect dashboard avec message d'erreur


class AbsenceListView(ChoraleRequireMixin, TemplateView):
    template_name = "pages/censor/absence_list.html"

    def get(self, request, slug, *args, **kwargs):
        absences = (Absence.objects
                    .filter(event__chorale=self.chorale)
                    .select_related('event', 'member', 'recorded_by'))
        # Filtres optionnels
        event_id = request.GET.get('event')
        member_id = request.GET.get('member')
        if event_id:
            absences = absences.filter(event_id=event_id)
        if member_id:
            absences = absences.filter(member_id=member_id)

        return render(request, self.template_name, {
            'absences': absences,
            'slug': self.chorale.slug,
            'events': ChoraleEvent.objects.filter(
                chorale=self.chorale, event_type__in=Absence.TRACKED_EVENT_TYPES,
            ).order_by('-date'),
            'members': self.chorale.members.all(),
            'filter_event': event_id or '',
            'filter_member': member_id or '',
        })


class AbsenceBulkCreateView(CensorRequiredMixin, TemplateView):
    """Saisie en masse pour UNE rencontre.

    Comportement idempotent : un POST sur la même rencontre efface les absences
    précédentes et recrée le nouvel état. Permet de corriger une saisie erronée
    sans manipuler la DB à la main.
    """
    template_name = "pages/censor/absence_bulk_form.html"

    def get(self, request, slug, *args, **kwargs):
        from .forms import BulkAbsenceForm
        form = BulkAbsenceForm(chorale=self.chorale)
        return render(request, self.template_name, {
            'form': form, 'slug': self.chorale.slug,
        })

    def post(self, request, slug, *args, **kwargs):
        from .forms import BulkAbsenceForm
        form = BulkAbsenceForm(request.POST, chorale=self.chorale)
        if form.is_valid():
            event = form.cleaned_data['event']
            absent_members = form.cleaned_data['absent_members']
            reason = form.cleaned_data['reason']
            is_justified = form.cleaned_data['is_justified']

            with transaction.atomic():
                # Idempotent upsert : on repart d'un état propre par rencontre
                Absence.objects.filter(event=event).delete()
                Absence.objects.bulk_create([
                    Absence(event=event, member=m, reason=reason,
                            is_justified=is_justified, recorded_by=request.user)
                    for m in absent_members
                ])

            ActivityEvent.log(
                chorale=self.chorale, user=request.user, event_type='other',
                description=f"Absences relevées pour « {event.title} » : "
                            f"{len(absent_members)} absent(s)",
                metadata={'event_id': event.id, 'count': len(absent_members)},
                request=request,
            )
            count = len(absent_members)
            messages.success(request, ngettext(
                "%(count)d absence recorded for \"%(title)s\".",
                "%(count)d absences recorded for \"%(title)s\".",
                count,
            ) % {'count': count, 'title': event.title})
            return redirect(reverse('absences', kwargs={'slug': self.chorale.slug}))

        return render(request, self.template_name, {
            'form': form, 'slug': self.chorale.slug,
        })


class AbsenceUpdateView(CensorRequiredMixin, TemplateView):
    template_name = "pages/censor/absence_edit_form.html"

    def _get_object(self, absence_id):
        return get_object_or_404(Absence, id=absence_id, event__chorale=self.chorale)

    def get(self, request, slug, absence_id, *args, **kwargs):
        from .forms import AbsenceEditForm
        absence = self._get_object(absence_id)
        form = AbsenceEditForm(instance=absence)
        return render(request, self.template_name, {
            'form': form, 'slug': self.chorale.slug, 'absence': absence,
        })

    def post(self, request, slug, absence_id, *args, **kwargs):
        from .forms import AbsenceEditForm
        absence = self._get_object(absence_id)
        form = AbsenceEditForm(request.POST, instance=absence)
        if form.is_valid():
            form.save()
            messages.success(request, _("Absence updated."))
            return redirect(reverse('absences', kwargs={'slug': self.chorale.slug}))
        return render(request, self.template_name, {
            'form': form, 'slug': self.chorale.slug, 'absence': absence,
        })


class AbsenceDeleteView(CensorRequiredMixin, TemplateView):
    def post(self, request, slug, absence_id, *args, **kwargs):
        absence = get_object_or_404(Absence, id=absence_id, event__chorale=self.chorale)
        absence.delete()
        messages.success(request, _("Absence deleted."))
        return redirect(reverse('absences', kwargs={'slug': self.chorale.slug}))

    def get(self, request, *args, **kwargs):
        # GET interdit (idempotence HTTP)
        return redirect(reverse('absences', kwargs={'slug': kwargs.get('slug')}))


class SanctionListView(ChoraleRequireMixin, TemplateView):
    template_name = "pages/censor/sanction_list.html"

    def get(self, request, slug, *args, **kwargs):
        sanctions = (self.chorale.sanctions
                     .select_related('member', 'recorded_by'))

        # Filtres optionnels
        sanction_type = request.GET.get('type')
        member_id = request.GET.get('member')
        status = request.GET.get('status')  # 'active' | 'closed' | ''
        if sanction_type:
            sanctions = sanctions.filter(sanction_type=sanction_type)
        if member_id:
            sanctions = sanctions.filter(member_id=member_id)
        if status == 'active':
            sanctions = sanctions.filter(lifted_at__isnull=True).filter(
                ~Q(sanction_type=Sanction.SANCTION_FINE) | Q(is_paid=False)
            )
        elif status == 'closed':
            sanctions = sanctions.filter(
                Q(lifted_at__isnull=False)
                | Q(sanction_type=Sanction.SANCTION_FINE, is_paid=True)
            )

        return render(request, self.template_name, {
            'sanctions': sanctions,
            'slug': self.chorale.slug,
            'members': self.chorale.members.all(),
            'sanction_types': Sanction.SANCTION_TYPE_CHOICES,
            'filter_type': sanction_type or '',
            'filter_member': member_id or '',
            'filter_status': status or '',
        })


class SanctionCreateView(CensorRequiredMixin, TemplateView):
    template_name = "pages/censor/sanction_form.html"

    def get(self, request, slug, *args, **kwargs):
        from .forms import SanctionForm
        form = SanctionForm(chorale=self.chorale)
        return render(request, self.template_name, {
            'form': form, 'slug': self.chorale.slug, 'is_edit': False,
        })

    def post(self, request, slug, *args, **kwargs):
        from .forms import SanctionForm
        form = SanctionForm(request.POST, chorale=self.chorale)
        if form.is_valid():
            try:
                SanctionService.apply(
                    chorale=self.chorale,
                    member=form.cleaned_data['member'],
                    sanction_type=form.cleaned_data['sanction_type'],
                    reason=form.cleaned_data['reason'],
                    amount=form.cleaned_data.get('amount'),
                    time_limit=form.cleaned_data.get('time_limit'),
                    applied_at=form.cleaned_data.get('applied_at'),
                    recorded_by=request.user,
                    request=request,
                )
            except DjangoValidationError as e:
                form.add_error(None, e.message)
                return render(request, self.template_name, {
                    'form': form, 'slug': self.chorale.slug, 'is_edit': False,
                })
            messages.success(request, _("Sanction recorded."))
            return redirect(reverse('sanctions', kwargs={'slug': self.chorale.slug}))

        return render(request, self.template_name, {
            'form': form, 'slug': self.chorale.slug, 'is_edit': False,
        })


class SanctionUpdateView(CensorRequiredMixin, TemplateView):
    template_name = "pages/censor/sanction_form.html"

    def _get_object(self, sanction_id):
        return get_object_or_404(Sanction, id=sanction_id, chorale=self.chorale)

    def get(self, request, slug, sanction_id, *args, **kwargs):
        from .forms import SanctionForm
        sanction = self._get_object(sanction_id)
        form = SanctionForm(instance=sanction, chorale=self.chorale)
        return render(request, self.template_name, {
            'form': form, 'slug': self.chorale.slug,
            'sanction': sanction, 'is_edit': True,
        })

    def post(self, request, slug, sanction_id, *args, **kwargs):
        from .forms import SanctionForm
        sanction = self._get_object(sanction_id)
        form = SanctionForm(request.POST, instance=sanction, chorale=self.chorale)
        if form.is_valid():
            form.save()
            ActivityEvent.log(
                chorale=self.chorale, user=request.user, event_type='other',
                description=f"Sanction modifiée pour {sanction.member.get_full_name() or sanction.member.username}",
                obj=sanction, request=request,
            )
            messages.success(request, _("Sanction updated."))
            return redirect(reverse('sanctions', kwargs={'slug': self.chorale.slug}))
        return render(request, self.template_name, {
            'form': form, 'slug': self.chorale.slug,
            'sanction': sanction, 'is_edit': True,
        })


class SanctionLiftView(CensorRequiredMixin, TemplateView):
    """Lève (clôture) une sanction. POST only."""

    def post(self, request, slug, sanction_id, *args, **kwargs):
        sanction = get_object_or_404(Sanction, id=sanction_id, chorale=self.chorale)
        try:
            SanctionService.lift(sanction=sanction, lifted_by=request.user, request=request)
        except DjangoValidationError as e:
            messages.error(request, e.message)
            return redirect(reverse('sanctions', kwargs={'slug': self.chorale.slug}))
        messages.success(request, _("Sanction lifted."))
        return redirect(reverse('sanctions', kwargs={'slug': self.chorale.slug}))

    def get(self, request, *args, **kwargs):
        return redirect(reverse('sanctions', kwargs={'slug': kwargs.get('slug')}))


class SanctionDeleteView(CensorRequiredMixin, TemplateView):
    def post(self, request, slug, sanction_id, *args, **kwargs):
        sanction = get_object_or_404(Sanction, id=sanction_id, chorale=self.chorale)
        target = sanction.member.get_full_name() or sanction.member.username
        sanction.delete()
        ActivityEvent.log(
            chorale=self.chorale, user=request.user, event_type='other',
            description=f"Sanction supprimée (cible : {target})",
            request=request,
        )
        messages.success(request, _("Sanction deleted."))
        return redirect(reverse('sanctions', kwargs={'slug': self.chorale.slug}))

    def get(self, request, *args, **kwargs):
        return redirect(reverse('sanctions', kwargs={'slug': kwargs.get('slug')}))


class MemberPopupView(ChoraleRequireMixin, TemplateView):
    template_name = "pages/member_popup.html"
    form_class = AddMemberForm

    # Choix de rôles présentables (hors 'admin' qui se gère via Membership.is_admin)
    ASSIGNABLE_ROLE_CHOICES = [
        (Membership.ROLE_MEMBER, _('Member')),
        (Membership.ROLE_SECRETARY, _('Secretary')),
        (Membership.ROLE_TREASURER, _('Treasurer')),
        (Membership.ROLE_CENSOR, _('Censor')),
    ]

    def get_role_choices(self):
        if self.membership.is_admin:
            return self.ASSIGNABLE_ROLE_CHOICES
        return [(Membership.ROLE_MEMBER, _('Member'))]

    def get_form(self, request):
        form = self.form_class(request.POST) if request.method == 'POST' else self.form_class()
        form.fields['role'].choices = self.get_role_choices()
        return form

    def get(self, request, slug, *args, **kwargs):
        form = self.get_form(request)
        return render(request, self.template_name, {"form": form, "slug": self.chorale.slug})

    def post(self, request, slug, *args, **kwargs):
        form = self.get_form(request)
        chorale = self.chorale

        if form.is_valid():
            role = form['role'].value()
            allowed_roles = [choice[0] for choice in self.get_role_choices()]

            if role not in allowed_roles:
                messages.error(request, _("You are not authorized to assign this role."))
                return render(request, self.template_name, {"form": form, "slug": chorale.slug})

            email = form['email'].value()
            first_name = form['first_name'].value()
            last_name = form['last_name'].value()
            contact_phone = form['contact_phone'].value()
            username = email.split('@')[0].lower()
            try:
                with transaction.atomic():
                    member = CustomUser.objects.create_user(
                        username=username,
                        email=email,
                        password="defaultpassword123",
                        first_name=first_name,
                        last_name=last_name,
                    )
                    Profile.objects.create(user=member, _contact=contact_phone)
                    Membership.objects.create(
                        user=member,
                        chorale=chorale,
                        role=role,
                        is_admin=False,
                    )

                role_label = dict(self.ASSIGNABLE_ROLE_CHOICES).get(role, role)
                messages.success(request, _("%(name)s has been added as %(role)s.") % {
                    'name': member.get_full_name(),
                    'role': role_label,
                })
                return redirect(reverse('members', kwargs={"slug": chorale.slug}))
            except Exception:
                messages.error(request, _("An error occurred while adding the member."))
                return redirect(reverse('members', kwargs={"slug": chorale.slug}))


class ChoraleSelectView(LoginRequiredMixin, TemplateView):
    """Écran de sélection de chorale pour les users multi-chorales.

    - GET : liste des memberships avec rôle + count de membres.
    - POST (slug) : valide qu'il s'agit d'une chorale de l'user, écrit
      ``session['active_chorale_slug']`` puis redirige vers le dashboard.
    """

    template_name = "pages/select_chorale.html"

    def _user_memberships(self):
        from django.db.models import Count
        return (
            self.request.user.memberships
            .select_related('chorale')
            .annotate(members_count=Count('chorale__memberships'))
            .order_by('-is_admin', 'joined_at')
        )

    def get(self, request, *args, **kwargs):
        memberships = list(self._user_memberships())
        if not memberships:
            return redirect(reverse('create_chorale'))
        if len(memberships) == 1:
            slug = memberships[0].chorale.slug
            request.session['active_chorale_slug'] = slug
            return redirect(reverse('dashboard', kwargs={'slug': slug}))
        return render(request, self.template_name, {'memberships': memberships})

    def post(self, request, *args, **kwargs):
        slug = request.POST.get('slug') or request.GET.get('slug')
        if not slug:
            messages.error(request, _("Please choose a chorale."))
            return redirect(reverse('select_chorale'))

        belongs = request.user.memberships.filter(chorale__slug=slug).exists()
        if not belongs:
            messages.error(request, _("You do not belong to this chorale."))
            return redirect(reverse('select_chorale'))

        request.session['active_chorale_slug'] = slug
        return redirect(reverse('dashboard', kwargs={'slug': slug}))


@login_required
def close_popup(request):
    return render(request, "pages/close_popup.html")

@login_required
def sidebar_toggle(request, slug):
    sidebar_open = request.GET.get('open') == '1'
    return render(request, "base/navbar.html", {"sidebar_open": sidebar_open, "slug": slug})