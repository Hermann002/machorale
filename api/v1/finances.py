"""Sprint 6 — contributions catalogue, member payments, cash flow.

The most sensitive data in the app. Reads are open to any member (mirroring
the web list views on ``ChoraleRequireMixin``); writes are treasurer/admin
(``IsTreasurerOrAdminOrReadOnly``, the web's ``TreasurerRequiredMixin``).

Money is Decimal end to end — DRF renders Decimals as strings, floats never
cross the wire. Payments go through ``ContributionService.record_payment``
(validation, activity log, dashboard-cache invalidation, notification) —
business rules stay in the service, never duplicated here.
"""
from decimal import Decimal

from django.core.cache import cache
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import DecimalField, Q, Sum, Value
from django.db.models.functions import Coalesce
from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.generics import (
    ListCreateAPIView,
    RetrieveUpdateAPIView,
    RetrieveUpdateDestroyAPIView,
)
from rest_framework.response import Response

from manage_chorale.models import CashFlow, Contribution, MemberContribution
from manage_chorale.models import Event as ActivityEvent
from manage_chorale.services import ContributionService

from .events import _parse_date
from .permissions import IsTreasurerOrAdminOrReadOnly
from .serializers import (
    CashFlowSerializer,
    ContributionSerializer,
    MemberContributionSerializer,
    PaymentCreateSerializer,
)

MONEY = DecimalField(max_digits=14, decimal_places=2)


def money_str(value):
    """Aggregate result → exact 2-decimal string. Postgres returns clean
    Decimals; sqlite (local test runs) leaks float noise — normalize both."""
    return str(Decimal(str(value)).quantize(Decimal("0.01")))


class _FinancesBase:
    permission_classes = [IsTreasurerOrAdminOrReadOnly]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["chorale"] = self.request.chorale
        return context

    def _invalidate_dashboard(self):
        cache.delete(f"dashboard_stats:{self.request.chorale.id}")


# --- Contribution catalogue --------------------------------------------------

@extend_schema(tags=["finances"])
class ContributionListCreateView(_FinancesBase, ListCreateAPIView):
    """GET ``/chorales/<slug>/contributions/`` — catalogue, newest first,
    ``?is_active=true|false`` filter, each with ``total_collected``.
    POST creates a type (treasurer/admin)."""

    serializer_class = ContributionSerializer

    @extend_schema(
        summary="List the contribution types",
        parameters=[
            OpenApiParameter(
                "is_active", bool, description="Filter on active state.",
            ),
        ],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(summary="Create a contribution type (treasurer/admin)")
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

    def get_queryset(self):
        qs = (
            Contribution.objects.filter(chorale=self.request.chorale)
            .annotate(
                collected=Coalesce(
                    Sum("payments__amount"), Value(0), output_field=MONEY
                )
            )
            .order_by("-created_at")
        )
        is_active = self.request.query_params.get("is_active")
        if is_active is not None:
            if is_active.lower() not in ("true", "false"):
                raise ValidationError(
                    {"is_active": [_("Use true or false.")]}
                )
            qs = qs.filter(is_active=is_active.lower() == "true")
        return qs

    def perform_create(self, serializer):
        contribution = serializer.save()
        self._invalidate_dashboard()
        ActivityEvent.log(
            chorale=self.request.chorale,
            user=self.request.user,
            event_type="other",
            description=f"Type de cotisation créé : {contribution.title}",
            obj=contribution,
            request=self.request,
        )


@extend_schema(tags=["finances"], summary="Retrieve / edit / delete a contribution type")
@extend_schema(
    methods=["PATCH"],
    summary="Edit a contribution type (treasurer/admin)",
)
class ContributionDetailView(_FinancesBase, RetrieveUpdateDestroyAPIView):
    """GET/PATCH/DELETE ``/chorales/<slug>/contributions/<id>/``. DELETE
    cascades to its payments (same as the web delete) — prefer
    ``is_active=false`` to retire a type while keeping history."""

    serializer_class = ContributionSerializer
    http_method_names = ["get", "patch", "delete", "head", "options"]

    def get_queryset(self):
        return Contribution.objects.filter(chorale=self.request.chorale)

    def perform_update(self, serializer):
        contribution = serializer.save()
        self._invalidate_dashboard()
        ActivityEvent.log(
            chorale=self.request.chorale,
            user=self.request.user,
            event_type="other",
            description=f"Type de cotisation modifié : {contribution.title}",
            obj=contribution,
            request=self.request,
        )

    def perform_destroy(self, instance):
        ActivityEvent.log(
            chorale=self.request.chorale,
            user=self.request.user,
            event_type="other",
            description=f"Type de cotisation supprimé : {instance.title}",
            request=self.request,
        )
        instance.delete()
        self._invalidate_dashboard()


# --- Payments ----------------------------------------------------------------

@extend_schema(tags=["finances"])
class PaymentListCreateView(_FinancesBase, ListCreateAPIView):
    """GET ``/chorales/<slug>/contributions/<id>/payments/`` — payments of one
    contribution type, ``?member=<membership id>`` filter. POST records a
    payment (treasurer/admin) through ``ContributionService`` — payments are
    immutable, there is no PATCH/DELETE."""

    serializer_class = MemberContributionSerializer

    def _get_contribution(self):
        contribution = Contribution.objects.filter(
            chorale=self.request.chorale, pk=self.kwargs["pk"]
        ).first()
        if contribution is None:
            raise NotFound(_("Contribution type not found."))
        return contribution

    def get_queryset(self):
        qs = (
            MemberContribution.objects.select_related("member", "recorded_by")
            .filter(contribution=self._get_contribution())
            .order_by("-paid_at", "-created_at")
        )
        member = self.request.query_params.get("member")
        if member:
            if not member.isdigit():
                raise ValidationError(
                    {"member": [_("Expected a membership id.")]}
                )
            qs = qs.filter(
                member__memberships__id=member,
                member__memberships__chorale=self.request.chorale,
            )
        return qs

    @extend_schema(
        summary="List the payments of a contribution type",
        parameters=[
            OpenApiParameter(
                "member", int, description="Filter by membership id.",
            ),
        ],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary="Record a payment (treasurer/admin)",
        request=PaymentCreateSerializer,
        responses={201: MemberContributionSerializer},
    )
    def post(self, request, *args, **kwargs):
        contribution = self._get_contribution()
        serializer = PaymentCreateSerializer(
            data=request.data, context={"chorale": request.chorale}
        )
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            payment = ContributionService.record_payment(
                contribution=contribution,
                member=serializer.context["membership"].user,
                amount=data.get("amount"),
                recorded_by=request.user,
                paid_at=data.get("paid_at"),
                note=data.get("note", ""),
                request=request,
            )
        except DjangoValidationError as exc:
            raise ValidationError({"non_field_errors": exc.messages})
        return Response(
            MemberContributionSerializer(payment).data,
            status=status.HTTP_201_CREATED,
        )


# --- Cash flow -----------------------------------------------------------------

@extend_schema(tags=["finances"])
class CashFlowListCreateView(_FinancesBase, ListCreateAPIView):
    """GET ``/chorales/<slug>/cashflows/`` — paginated, newest first, filters
    ``?type=entree|sortie`` and ``?start=&end=`` (YYYY-MM-DD, inclusive). The
    pagination envelope carries a ``totals`` object computed over the **whole
    filtered set** (not just the page): ``{"in", "out", "balance"}``.
    POST creates an entry (treasurer/admin)."""

    serializer_class = CashFlowSerializer

    def get_queryset(self):
        qs = (
            CashFlow.objects.select_related("created_by")
            .filter(chorale=self.request.chorale)
            .order_by("-date", "-created_at")
        )
        params = self.request.query_params
        flow_type = params.get("type")
        if flow_type:
            if flow_type not in (CashFlow.TYPE_ENTREE, CashFlow.TYPE_SORTIE):
                raise ValidationError({"type": [_("Use entree or sortie.")]})
            qs = qs.filter(type_cash_flow=flow_type)
        start = params.get("start")
        if start:
            qs = qs.filter(date__gte=_parse_date(start, "start"))
        end = params.get("end")
        if end:
            qs = qs.filter(date__lte=_parse_date(end, "end"))
        return qs

    @extend_schema(
        summary="List the cash flow entries (with running totals)",
        parameters=[
            OpenApiParameter(
                "type", str, description="entree (income) or sortie (expense).",
                enum=[CashFlow.TYPE_ENTREE, CashFlow.TYPE_SORTIE],
            ),
            OpenApiParameter("start", str, description="From date (YYYY-MM-DD)."),
            OpenApiParameter("end", str, description="To date (YYYY-MM-DD)."),
        ],
    )
    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        totals = self.get_queryset().aggregate(
            cash_in=Coalesce(
                Sum("amount", filter=Q(type_cash_flow=CashFlow.TYPE_ENTREE)),
                Value(0), output_field=MONEY,
            ),
            cash_out=Coalesce(
                Sum("amount", filter=Q(type_cash_flow=CashFlow.TYPE_SORTIE)),
                Value(0), output_field=MONEY,
            ),
        )
        cash_in = Decimal(str(totals["cash_in"]))
        cash_out = Decimal(str(totals["cash_out"]))
        response.data["totals"] = {
            "in": money_str(cash_in),
            "out": money_str(cash_out),
            "balance": money_str(cash_in - cash_out),
        }
        return response

    @extend_schema(summary="Record a cash flow entry (treasurer/admin)")
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

    def perform_create(self, serializer):
        flow = serializer.save()
        self._invalidate_dashboard()
        ActivityEvent.log(
            chorale=self.request.chorale,
            user=self.request.user,
            event_type="payment",
            description=(
                f"{flow.get_type_cash_flow_display()} enregistrée : "
                f"{flow.title} ({flow.amount} XAF)"
            ),
            obj=flow,
            request=self.request,
        )


@extend_schema(tags=["finances"], summary="Retrieve / edit a cash flow entry")
@extend_schema(
    methods=["PATCH"],
    summary="Edit a cash flow entry (treasurer/admin)",
)
class CashFlowDetailView(_FinancesBase, RetrieveUpdateAPIView):
    """GET/PATCH ``/chorales/<slug>/cashflows/<id>/``. No DELETE — the web
    offers none either; correct a mistake by editing or a counter-entry."""

    serializer_class = CashFlowSerializer
    http_method_names = ["get", "patch", "head", "options"]

    def get_queryset(self):
        return CashFlow.objects.select_related("created_by").filter(
            chorale=self.request.chorale
        )

    def perform_update(self, serializer):
        flow = serializer.save()
        self._invalidate_dashboard()
        ActivityEvent.log(
            chorale=self.request.chorale,
            user=self.request.user,
            event_type="payment",
            description=(
                f"Mouvement de caisse modifié : {flow.title} "
                f"({flow.amount} XAF)"
            ),
            obj=flow,
            request=self.request,
        )
