"""DRF permissions mirroring the web app's ``ChoraleRequireMixin`` / role logic.

``Membership`` is the single source of truth for membership and role (never read
role off the user). These permissions resolve the chorale from the URL ``slug``
and attach ``request.chorale`` / ``request.membership`` for the view to reuse —
the same contract the web mixins provide via ``self.chorale`` / ``self.membership``.

Status-code contract:
- chorale slug unknown                          → 404 (``NotFound``)
- authenticated but not a member of that chorale → 403 (permission returns False)
- member, but role not allowed for an unsafe verb → 403
"""
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import NotFound
from rest_framework.permissions import SAFE_METHODS, BasePermission

from manage_chorale.models import Chorale, Membership


class IsChoraleMember(BasePermission):
    """Any membership in the chorale named by ``<slug>`` grants access.

    Resolves and caches ``request.chorale`` and ``request.membership`` so the
    view layer never re-queries. A missing chorale is a 404; a non-member is a
    403 (we don't leak the chorale's existence beyond the 404 anyone hitting a
    bad slug already gets)."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        # Cache on the request: role permissions subclass this and call super().
        membership = getattr(request, "membership", None)
        if membership is not None:
            return True

        slug = view.kwargs.get("slug")
        chorale = Chorale.objects.filter(slug=slug).first()
        if chorale is None:
            raise NotFound(_("Chorale not found."))

        membership = (
            Membership.objects.select_related("chorale")
            .filter(chorale=chorale, user=request.user)
            .first()
        )
        if membership is None:
            return False

        request.chorale = chorale
        request.membership = membership
        return True


class ChoraleRolePermission(IsChoraleMember):
    """Read open to any member; unsafe verbs gated by role.

    ``is_admin`` always bypasses the role filter (matching ``RoleRequireMixin``).
    Subclasses set ``write_roles`` — the non-admin roles allowed to write."""

    write_roles: tuple = ()

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        if request.method in SAFE_METHODS:
            return True
        membership = request.membership
        return membership.is_admin or membership.role in self.write_roles


class IsChoraleAdminOrReadOnly(ChoraleRolePermission):
    """Write: chorale admin only. Read: any member."""

    write_roles = ()


class IsSecretaryOrAdminOrReadOnly(ChoraleRolePermission):
    """Write: secretary (or admin). Read: any member."""

    write_roles = (Membership.ROLE_SECRETARY,)


class IsTreasurerOrAdminOrReadOnly(ChoraleRolePermission):
    """Write: treasurer (or admin). Read: any member."""

    write_roles = (Membership.ROLE_TREASURER,)


class IsCensorOrAdminOrReadOnly(ChoraleRolePermission):
    """Write: censor (or admin). Read: any member."""

    write_roles = (Membership.ROLE_CENSOR,)
