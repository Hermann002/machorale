"""Sprint 2 — chorale context & dashboard."""
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from manage_chorale.models import Membership
from manage_chorale.services import get_dashboard_stats

from .permissions import IsChoraleMember
from .serializers import ChoraleSerializer, DashboardStatsSerializer


class ChoraleListView(ListAPIView):
    """GET ``/chorales/`` — the chorales the authenticated user belongs to, each
    carrying *that user's* role/is_admin. Driven off ``Membership`` (the source
    of truth) so the role is always the caller's own."""

    serializer_class = ChoraleSerializer
    pagination_class = None  # a user's chorale set is small; return it whole.

    def get_queryset(self):
        memberships = (
            Membership.objects.select_related("chorale")
            .filter(user=self.request.user)
            .order_by("chorale__name")
        )
        chorales = []
        for membership in memberships:
            chorale = membership.chorale
            chorale._membership = membership
            chorales.append(chorale)
        return chorales


class DashboardView(APIView):
    """GET ``/chorales/<slug>/dashboard/`` — reuses ``get_dashboard_stats`` (the
    same Redis-cached, 60s-TTL aggregate the web dashboard renders). Membership
    is required; non-members get 403, unknown slug gets 404."""

    permission_classes = [IsChoraleMember]

    def get(self, request, slug):
        stats = get_dashboard_stats(request.chorale.id)
        return Response(DashboardStatsSerializer(stats).data)
