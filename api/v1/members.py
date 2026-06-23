"""Sprint 3 — members CRUD within a chorale.

A "member" is a ``Membership`` row (the canonical unit inside a chorale), joined
to its ``CustomUser`` + ``Profile``. Reads are open to any member; create / edit
/ remove are gated to secretary or admin (``IsSecretaryOrAdminOrReadOnly``).
"""
from django.db.models import Q
from rest_framework import status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.response import Response

from manage_chorale.models import Event as ActivityEvent
from manage_chorale.models import Membership

from .permissions import IsSecretaryOrAdminOrReadOnly
from .serializers import (
    MemberCreateSerializer,
    MemberSerializer,
    MemberUpdateSerializer,
)


class _MembersBase:
    """Shared chorale resolution + serializer context for member endpoints.
    ``IsSecretaryOrAdminOrReadOnly`` has already attached ``request.chorale`` /
    ``request.membership`` by the time these run."""

    permission_classes = [IsSecretaryOrAdminOrReadOnly]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["chorale"] = self.request.chorale
        return context


class MemberListCreateView(_MembersBase, ListCreateAPIView):
    """GET ``/chorales/<slug>/members/`` — paginated, ``?search=`` by name/email,
    ``?role=`` filter. POST creates/invites a member (secretary/admin)."""

    def get_queryset(self):
        qs = (
            Membership.objects.select_related("user", "user__profile")
            .filter(chorale=self.request.chorale)
            .order_by("user__first_name", "user__last_name", "id")
        )
        role = self.request.query_params.get("role")
        if role:
            qs = qs.filter(role=role)
        search = self.request.query_params.get("search")
        if search:
            qs = qs.filter(
                Q(user__first_name__icontains=search)
                | Q(user__last_name__icontains=search)
                | Q(user__username__icontains=search)
                | Q(user__email__icontains=search)
            )
        return qs

    def get_serializer_class(self):
        if self.request.method == "POST":
            return MemberCreateSerializer
        return MemberSerializer

    def create(self, request, *args, **kwargs):
        write = MemberCreateSerializer(
            data=request.data, context=self.get_serializer_context()
        )
        write.is_valid(raise_exception=True)
        membership = write.save()
        ActivityEvent.log(
            chorale=request.chorale,
            user=request.user,
            event_type="person_add",
            description=f"{membership.user.get_full_name() or membership.user.username} "
            f"added as {membership.get_role_display()}",
            obj=membership,
            request=request,
        )
        return Response(
            MemberSerializer(membership).data, status=status.HTTP_201_CREATED
        )


class MemberDetailView(_MembersBase, RetrieveUpdateDestroyAPIView):
    """GET/PATCH/DELETE ``/chorales/<slug>/members/<id>/`` (``id`` = membership
    id). PATCH edits role/name/contact (secretary/admin; role elevation
    admin-only). DELETE removes the membership (the web's ``person_remove``)."""

    serializer_class = MemberSerializer
    http_method_names = ["get", "patch", "delete", "head", "options"]

    def get_queryset(self):
        return Membership.objects.select_related(
            "user", "user__profile"
        ).filter(chorale=self.request.chorale)

    def partial_update(self, request, *args, **kwargs):
        membership = self.get_object()
        write = MemberUpdateSerializer(
            instance=membership,
            data=request.data,
            partial=True,
            context=self.get_serializer_context(),
        )
        write.is_valid(raise_exception=True)
        write.save()
        membership.refresh_from_db()
        return Response(MemberSerializer(membership).data)

    def perform_destroy(self, instance):
        # Don't strand a chorale: the admin membership can't be removed via the API.
        if instance.is_admin:
            raise PermissionDenied(
                "The chorale admin cannot be removed."
            )
        if instance.user_id == self.request.user.id:
            raise ValidationError({"detail": ["You cannot remove yourself."]})
        user = instance.user
        ActivityEvent.log(
            chorale=self.request.chorale,
            user=self.request.user,
            event_type="person_remove",
            description=f"{user.get_full_name() or user.username} removed from the chorale",
            request=self.request,
        )
        instance.delete()
