"""Sprint 5 — attendance (Absence) per event, with bulk write.

``Absence`` is sparse: only absentees are stored, presence is implied. The
attendance sheet returned by GET is the full roster (every membership) with a
``present`` flag and the absence details for absentees.

Write access mirrors the web ``CensorRequiredMixin``: censor or admin. Reads
are open to any member (like the web ``AbsenceListView``). The bulk PUT is the
web ``AbsenceBulkCreateView`` semantics — idempotent replace per event — but
richer: ``reason`` / ``is_justified`` are per member, not shared.
"""
from django.core.cache import cache
from django.db import transaction
from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import extend_schema
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from manage_chorale.models import Absence, ChoraleEvent, Membership
from manage_chorale.models import Event as ActivityEvent

from .permissions import IsCensorOrAdminOrReadOnly, IsChoraleMember
from .serializers import (
    AbsenceSerializer,
    AttendanceEntrySerializer,
    AttendanceWriteSerializer,
)


class EventAttendanceView(APIView):
    """GET/PUT ``/chorales/<slug>/events/<id>/attendance/``."""

    permission_classes = [IsCensorOrAdminOrReadOnly]

    def _get_event(self, request, pk):
        event = ChoraleEvent.objects.filter(
            chorale=request.chorale, pk=pk
        ).first()
        if event is None:
            raise NotFound(_("Event not found."))
        if event.event_type not in Absence.TRACKED_EVENT_TYPES:
            raise ValidationError(
                {"event": [_("Attendance is not tracked for this event type.")]}
            )
        return event

    def _sheet(self, request, event):
        absences_by_user = {
            a.member_id: a for a in Absence.objects.filter(event=event)
        }
        entries = []
        memberships = (
            Membership.objects.select_related("user")
            .filter(chorale=request.chorale)
            .order_by("user__first_name", "user__last_name", "id")
        )
        for membership in memberships:
            absence = absences_by_user.get(membership.user_id)
            entries.append(
                {
                    "membership_id": membership.id,
                    "user_id": membership.user_id,
                    "first_name": membership.user.first_name,
                    "last_name": membership.user.last_name,
                    "username": membership.user.username,
                    "present": absence is None,
                    "absence": absence,
                }
            )
        return AttendanceEntrySerializer(entries, many=True).data

    @extend_schema(
        summary="Attendance sheet for an event",
        responses=AttendanceEntrySerializer(many=True),
        tags=["attendance"],
    )
    def get(self, request, slug, pk):
        event = self._get_event(request, pk)
        return Response(self._sheet(request, event))

    @extend_schema(
        summary="Bulk set the absentees of an event (censor/admin)",
        request=AttendanceWriteSerializer,
        responses=AttendanceEntrySerializer(many=True),
        tags=["attendance"],
    )
    def put(self, request, slug, pk):
        event = self._get_event(request, pk)
        serializer = AttendanceWriteSerializer(
            data=request.data, context={"chorale": request.chorale}
        )
        serializer.is_valid(raise_exception=True)
        items = serializer.validated_data["absences"]

        with transaction.atomic():
            # Idempotent replace: wipe the event's previous state, recreate.
            Absence.objects.filter(event=event).delete()
            Absence.objects.bulk_create(
                [
                    Absence(
                        event=event,
                        member=item["membership"].user,
                        reason=item["reason"],
                        is_justified=item["is_justified"],
                        recorded_by=request.user,
                    )
                    for item in items
                ]
            )

        # Unjustified absences feed the dashboard aggregate.
        cache.delete(f"dashboard_stats:{request.chorale.id}")

        ActivityEvent.log(
            chorale=request.chorale,
            user=request.user,
            event_type="other",
            description=f"Absences relevées pour « {event.title} » : "
            f"{len(items)} absent(s)",
            metadata={"event_id": event.id, "count": len(items)},
            request=request,
        )
        return Response(self._sheet(request, event))


@extend_schema(
    summary="Absence history and stats of a member",
    tags=["attendance"],
)
class MemberAbsenceListView(ListAPIView):
    """GET ``/chorales/<slug>/members/<id>/absences/`` (``id`` = membership id).

    Paginated history, newest event first. The standard pagination envelope is
    extended with a ``stats`` object computed over the **whole** history:
    ``{"total", "justified", "unjustified"}``."""

    permission_classes = [IsChoraleMember]
    serializer_class = AbsenceSerializer

    def _get_membership(self):
        membership = Membership.objects.filter(
            chorale=self.request.chorale, pk=self.kwargs["pk"]
        ).first()
        if membership is None:
            raise NotFound(_("Member not found."))
        return membership

    def get_queryset(self):
        membership = self._get_membership()
        return (
            Absence.objects.select_related("event")
            .filter(member=membership.user, event__chorale=self.request.chorale)
            .order_by("-event__date", "-id")
        )

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        qs = self.get_queryset()
        total = qs.count()
        justified = qs.filter(is_justified=True).count()
        response.data["stats"] = {
            "total": total,
            "justified": justified,
            "unjustified": total - justified,
        }
        return response
