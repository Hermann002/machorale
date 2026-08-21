"""Sprint 4 — events CRUD with date-range querying.

Write access mirrors the web (``SecretaryOrAdminRequiredMixin`` on
``CreateEventView`` / ``EventUpdateView``): secretary or admin. Reads are open
to any member. Activity logging mirrors the web views (``event_type='other'``,
French descriptions — same audit trail either way in).
"""
import calendar
from datetime import date, datetime, time, timedelta

from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.exceptions import ValidationError
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView

from manage_chorale.models import ChoraleEvent
from manage_chorale.models import Event as ActivityEvent

from .permissions import IsSecretaryOrAdminOrReadOnly
from .serializers import ChoraleEventSerializer

EVENT_TYPES = [c[0] for c in ChoraleEvent.EVENT_TYPE_CHOICES]


def _parse_date(value, param):
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise ValidationError({param: [_("Use the YYYY-MM-DD format.")]})


def _aware(d, t=time.min):
    return timezone.make_aware(datetime.combine(d, t))


class _EventsBase:
    permission_classes = [IsSecretaryOrAdminOrReadOnly]
    serializer_class = ChoraleEventSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["chorale"] = self.request.chorale
        return context

    def _log(self, event, action):
        ActivityEvent.log(
            chorale=self.request.chorale,
            user=self.request.user,
            event_type="other",
            description=f"Événement {action} : {event.title}",
            metadata={"event_id": event.id, "title": event.title},
            request=self.request,
        )


@extend_schema(tags=["events"])
class EventListCreateView(_EventsBase, ListCreateAPIView):
    """GET ``/chorales/<slug>/events/`` — paginated, ordered by date. Filters:
    ``?month=YYYY-MM`` or ``?start=YYYY-MM-DD&end=YYYY-MM-DD`` (both inclusive,
    each side optional), ``?type=practice|meeting|concert|assistance|other``.
    POST creates an event (secretary/admin)."""

    @extend_schema(
        summary="List the events of a chorale",
        parameters=[
            OpenApiParameter(
                "month", str,
                description="Calendar month, YYYY-MM. Mutually exclusive with start/end.",
            ),
            OpenApiParameter(
                "start", str, description="Range start (inclusive), YYYY-MM-DD.",
            ),
            OpenApiParameter(
                "end", str, description="Range end (inclusive), YYYY-MM-DD.",
            ),
            OpenApiParameter(
                "type", str,
                description="Event type (practice, meeting, concert, assistance, other).",
                enum=EVENT_TYPES,
            ),
        ],
        responses=ChoraleEventSerializer(many=True),
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary="Create an event (secretary/admin)",
        request=ChoraleEventSerializer,
        responses={201: ChoraleEventSerializer},
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

    def get_queryset(self):
        qs = ChoraleEvent.objects.filter(chorale=self.request.chorale).order_by(
            "date", "id"
        )
        params = self.request.query_params

        month = params.get("month")
        if month:
            try:
                year, month_no = (int(p) for p in month.split("-", 1))
                first = date(year, month_no, 1)
            except ValueError:
                raise ValidationError({"month": [_("Use the YYYY-MM format.")]})
            last = date(year, month_no, calendar.monthrange(year, month_no)[1])
            return qs.filter(
                date__gte=_aware(first), date__lt=_aware(last) + timedelta(days=1)
            )

        start = params.get("start")
        if start:
            qs = qs.filter(date__gte=_aware(_parse_date(start, "start")))
        end = params.get("end")
        if end:
            qs = qs.filter(
                date__lt=_aware(_parse_date(end, "end")) + timedelta(days=1)
            )

        event_type = params.get("type")
        if event_type:
            if event_type not in EVENT_TYPES:
                raise ValidationError({"type": [_("Unknown event type.")]})
            qs = qs.filter(event_type=event_type)
        return qs

    def perform_create(self, serializer):
        event = serializer.save()
        self._log(event, "créé")


@extend_schema(tags=["events"], summary="Retrieve / edit / delete an event")
@extend_schema(
    methods=["PATCH"],
    summary="Edit an event (secretary/admin)",
    request=ChoraleEventSerializer,
    responses=ChoraleEventSerializer,
)
class EventDetailView(_EventsBase, RetrieveUpdateDestroyAPIView):
    """GET/PATCH/DELETE ``/chorales/<slug>/events/<id>/``. Writes are
    secretary/admin; PATCH keeping the existing (past) date is allowed so
    finances can be filled in after the event."""

    http_method_names = ["get", "patch", "delete", "head", "options"]

    def get_queryset(self):
        return ChoraleEvent.objects.filter(chorale=self.request.chorale)

    def perform_update(self, serializer):
        event = serializer.save()
        self._log(event, "modifié")

    def perform_destroy(self, instance):
        self._log(instance, "supprimé")
        instance.delete()
