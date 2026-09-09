from decimal import Decimal

from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db.models import Count, Sum
from django.utils import timezone

from django.db.models import Q, Subquery, OuterRef

from .models import (
    Contribution,
    Chorale,
    ChoraleEvent,
    MemberContribution,
    CashFlow,
    Event,
    Sanction,
    Absence,
)


class ContributionService:
    """Encapsule la logique métier autour des cotisations.

    Pourquoi pas dans la vue ? Les vues doivent rester fines (parse HTTP, render).
    La logique « valider que le payeur est dans la chorale, créer le paiement, logger
    l'événement » est métier, doit être testable sans HTTP, et réutilisable
    (CLI, API, Celery task, command admin).
    """

    @staticmethod
    def record_payment(
        *,
        contribution: Contribution,
        member,
        amount,
        recorded_by,
        paid_at=None,
        note: str = "",
        request=None,
    ) -> MemberContribution:
        # Garantie d'intégrité métier : on ne peut pas enregistrer un paiement
        # pour un user qui n'est pas membre de la chorale visée.
        if not contribution.chorale.members.filter(pk=member.pk).exists():
            raise ValidationError(
                "Ce membre n'appartient pas à la chorale de cette contribution."
            )

        if amount is None:
            amount = contribution.amount

        if Decimal(amount) <= 0:
            raise ValidationError("Le montant doit être strictement positif.")

        payment = MemberContribution.objects.create(
            contribution=contribution,
            member=member,
            amount=amount,
            paid_at=paid_at or timezone.now().date(),
            note=note,
            recorded_by=recorded_by,
        )

        # Audit immuable. Le bus d'événements (Event) est notre journal de bord.
        Event.log(
            chorale=contribution.chorale,
            user=recorded_by,
            event_type="payment",
            description=(
                f"{member.get_full_name() or member.username} a payé "
                f"{amount} XAF pour « {contribution.title} »"
            ),
            obj=payment,
            metadata={
                "contribution_id": contribution.id,
                "member_id": member.id,
                "amount": str(amount),
            },
            request=request,
        )

        # Invalider le cache du dashboard : le solde a changé
        cache.delete(f"dashboard_stats:{contribution.chorale.id}")
        from notifications.services import notify_chorale

        notify_chorale(
            contribution.chorale,
            payload={
                "title": "Nouveau paiement",
                "body": (
                    f"{member.get_full_name() or member.username} a payé "
                    f"{amount} XAF pour « {contribution.title} »"
                ),
                "amount": str(amount),
                "payment_id": payment.id,
            },
            kind="payment",
        )
        return payment


class SanctionService:
    """Logique métier autour des sanctions.
    Centralise les validations et l'audit pour éviter la dispersion.
    """

    @staticmethod
    def apply(
        *,
        chorale,
        member,
        sanction_type,
        reason,
        recorded_by,
        amount=None,
        time_limit=None,
        applied_at=None,
        request=None,
    ) -> Sanction:
        # Intégrité métier : ne pas sanctionner un user qui n'est pas dans la chorale
        if not chorale.members.filter(pk=member.pk).exists():
            raise ValidationError("Ce membre n'appartient pas à la chorale.")

        # Cohérence type ↔ amount : seules les amendes ont un montant
        if sanction_type == Sanction.SANCTION_FINE:
            if amount is None or Decimal(amount) <= 0:
                raise ValidationError(
                    "Une amende requiert un montant strictement positif."
                )
        else:
            # Forcer la nullité : éviter qu'un warning porte par erreur un amount résiduel
            amount = None

        sanction = Sanction.objects.create(
            chorale=chorale,
            member=member,
            sanction_type=sanction_type,
            reason=reason,
            amount=amount,
            time_limit=time_limit,
            applied_at=applied_at or timezone.now().date(),
            recorded_by=recorded_by,
        )

        # Audit. event_type='warning' est déjà flaggé important automatiquement.
        Event.log(
            chorale=chorale,
            user=recorded_by,
            event_type="warning",
            description=(
                f"{sanction.get_sanction_type_display()} appliqué à "
                f"{member.get_full_name() or member.username}"
                + (f" ({amount} XAF)" if amount else "")
            ),
            obj=sanction,
            metadata={
                "sanction_type": sanction_type,
                "member_id": member.id,
                "amount": str(amount) if amount else None,
            },
            request=request,
        )

        cache.delete(f"dashboard_stats:{chorale.id}")

        from notifications.services import notify_chorale

        notify_chorale(
            chorale,
            payload={
                "title": "Nouvelle sanction",
                "body": (
                    f"{sanction.get_sanction_type_display()} appliqué à "
                    f"{member.get_full_name() or member.username}"
                    + (f" ({amount} XAF)" if amount else "")
                ),
                "member_id": member.id,
                "sanction_id": sanction.id,
            },
            kind="sanction",
        )
        return sanction

    @staticmethod
    def lift(*, sanction: Sanction, lifted_by, request=None) -> Sanction:
        """Cloture une sanction (date de levée = aujourd'hui)."""
        if sanction.lifted_at is not None:
            raise ValidationError("Cette sanction est déjà levée.")
        sanction.lifted_at = timezone.now().date()
        sanction.save(update_fields=["lifted_at", "updated_at"])

        Event.log(
            chorale=sanction.chorale,
            user=lifted_by,
            event_type="other",
            description=f"Sanction levée : {sanction.get_sanction_type_display()} de "
            f"{sanction.member.get_full_name() or sanction.member.username}",
            obj=sanction,
            request=request,
        )
        cache.delete(f"dashboard_stats:{sanction.chorale.id}")
        return sanction


def get_dashboard_stats(chorale_id, timeout=60):
    cache_key = f"dashboard_stats:{chorale_id}"
    stats = cache.get(cache_key)
    if stats is not None:
        return stats

    chorale = Chorale.objects.filter(pk=chorale_id).first()
    if not chorale:
        return {"error": "Chorale not found"}

    now = timezone.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # Solde de caisse = somme(entrées) - somme(sorties)
    cash_stats = CashFlow.objects.filter(chorale=chorale).aggregate(
        cash_in=Sum("amount", filter=Q(type_cash_flow=CashFlow.TYPE_ENTREE)),
        cash_out=Sum("amount", filter=Q(type_cash_flow=CashFlow.TYPE_SORTIE)),
    )
    cash_in = cash_stats["cash_in"] or 0
    cash_out = cash_stats["cash_out"] or 0

    monthly_payments = (
        MemberContribution.objects.filter(
            contribution__chorale=OuterRef("pk"), paid_at__gte=month_start.date()
        )
        .values("contribution__chorale")
        .annotate(total=Sum("amount"))
        .values("total")
    )

    open_sanctions = (
        Sanction.objects.filter(chorale=OuterRef("pk"), lifted_at__isnull=True)
        .filter(~Q(sanction_type=Sanction.SANCTION_FINE) | Q(is_paid=False))
        .values("chorale")
        .annotate(count=Count("id"))
        .values("count")
    )

    unjustified_absences = (
        Absence.objects.filter(
            event__chorale=OuterRef("pk"),
            is_justified=False,
            recorded_at__gte=month_start,
        )
        .values("event__chorale")
        .annotate(count=Count("id"))
        .values("count")
    )

    upcoming_events = (
        ChoraleEvent.objects.filter(chorale=OuterRef("pk"), date__gte=now)
        .values("chorale")
        .annotate(count=Count("id"))
        .values("count")
    )

    active_contributions = (
        Contribution.objects.filter(chorale=OuterRef("pk"), is_active=True)
        .values("chorale")
        .annotate(count=Count("id"))
        .values("count")
    )

    chorale_stats = (
        Chorale.objects.filter(pk=chorale_id)
        .annotate(
            total_members=Count("memberships"),
            collected_month=Subquery(monthly_payments),
            open_sanctions_count=Subquery(open_sanctions),
            unjustified_absences_this_month=Subquery(unjustified_absences),
            upcoming_event_count=Subquery(upcoming_events),
            active_contribution_count=Subquery(active_contributions),
        )
        .values(
            "total_members",
            "collected_month",
            "open_sanctions_count",
            "unjustified_absences_this_month",
            "upcoming_event_count",
            "active_contribution_count",
        )
        .first()
    )

    stats = {
        "total_members": chorale_stats["total_members"] or 0,
        "upcoming_event_count": chorale_stats["upcoming_event_count"] or 0,
        "cash_balance": cash_in - cash_out,
        "cash_in_total": cash_in,
        "cash_out_total": cash_out,
        "contributions_collected_this_month": chorale_stats["collected_month"] or 0,
        "active_contribution_count": chorale_stats["active_contribution_count"] or 0,
        "open_sanctions_count": chorale_stats["open_sanctions_count"] or 0,
        "unjustified_absences_this_month": chorale_stats[
            "unjustified_absences_this_month"
        ]
        or 0,
    }

    cache.set(cache_key, stats, timeout)
    return stats
