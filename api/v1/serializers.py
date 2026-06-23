"""Serializers for the v1 API.

Serializers expose existing models — no business rules live here. Money fields
are always ``DecimalField`` (never float). JSON keys are ``snake_case``.
"""
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from manage_chorale.models import Chorale, Membership
from manage_users.models import CustomUser, Profile


class ProfileSerializer(serializers.ModelSerializer):
    """Read view of a member's profile. ``_contact`` is exposed as ``contact``."""

    contact = serializers.CharField(source="_contact", allow_blank=True,
                                    allow_null=True, required=False)
    profession = serializers.CharField(read_only=True)

    class Meta:
        model = Profile
        fields = (
            "contact",
            "marital_status",
            "christened",
            "confirmed",
            "joined_date",
            "dob",
            "profession_c",
            "profession_o",
            "profession",
            "neighborhood",
            "department",
        )


class UserSerializer(serializers.ModelSerializer):
    """Current-user representation returned by ``auth/me`` and embedded in the
    token-pair response of ``auth/otp/verify``."""

    profile = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = (
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "is_verify",
            "profile",
        )
        read_only_fields = fields

    def get_profile(self, obj):
        profile = Profile.objects.filter(user=obj).first()
        if profile is None:
            return None
        return ProfileSerializer(profile).data


class ChoraleSerializer(serializers.ModelSerializer):
    """A chorale as seen by one of its members. ``role`` / ``is_admin`` come
    from *that* member's ``Membership`` — pass it via ``context['membership']``
    or annotate the instance with ``_membership`` (the list view does the latter)."""

    role = serializers.SerializerMethodField()
    is_admin = serializers.SerializerMethodField()

    class Meta:
        model = Chorale
        fields = (
            "id",
            "name",
            "slug",
            "type_c",
            "city",
            "country",
            "logo",
            "slogan",
            "role",
            "is_admin",
        )

    def _membership(self, obj):
        membership = getattr(obj, "_membership", None)
        if membership is not None:
            return membership
        return self.context.get("membership")

    def get_role(self, obj):
        membership = self._membership(obj)
        return membership.role if membership else None

    def get_is_admin(self, obj):
        membership = self._membership(obj)
        return membership.is_admin if membership else False


class MemberSerializer(serializers.ModelSerializer):
    """A chorale member = a ``Membership`` row joined to its user + profile.
    ``id`` is the **membership** id (the addressable unit within a chorale)."""

    user = UserSerializer(read_only=True)

    class Meta:
        model = Membership
        fields = ("id", "role", "is_admin", "joined_at", "user")
        read_only_fields = fields


# Roles assignable through the API. 'admin' is excluded: admin status is the
# `is_admin` flag, managed separately — mirrors the web ASSIGNABLE_ROLE_CHOICES.
ASSIGNABLE_ROLES = (
    Membership.ROLE_MEMBER,
    Membership.ROLE_SECRETARY,
    Membership.ROLE_TREASURER,
    Membership.ROLE_CENSOR,
)


class MemberWriteMixin:
    """Shared role-assignment guard: a non-admin writer (secretary) may only
    assign the plain ``member`` role; admins may assign any non-admin role."""

    def _check_role_assignment(self, role):
        if role is None:
            return
        actor = self.context["request"].membership
        if not actor.is_admin and role != Membership.ROLE_MEMBER:
            raise serializers.ValidationError(
                {"role": [_("Only an admin can assign elevated roles.")]}
            )


class MemberCreateSerializer(MemberWriteMixin, serializers.Serializer):
    """Create/invite a member: provisions ``CustomUser`` + ``Profile`` +
    ``Membership`` in one transaction (mirrors the web ``MemberPopupView``)."""

    email = serializers.EmailField()
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    contact_phone = serializers.CharField(
        max_length=15, required=False, allow_blank=True
    )
    role = serializers.ChoiceField(
        choices=ASSIGNABLE_ROLES, default=Membership.ROLE_MEMBER
    )

    def validate_email(self, value):
        value = value.lower()
        if CustomUser.objects.filter(email=value).exists():
            raise serializers.ValidationError(
                _("A user with this email already exists.")
            )
        return value

    def validate(self, attrs):
        self._check_role_assignment(attrs.get("role"))
        return attrs

    def _unique_username(self, email):
        base = email.split("@")[0].lower()
        username = base
        i = 1
        while CustomUser.objects.filter(username=username).exists():
            i += 1
            username = f"{base}{i}"
        return username

    def create(self, validated_data):
        from django.db import transaction

        chorale = self.context["chorale"]
        with transaction.atomic():
            # password=None → unusable password; members authenticate via the
            # OTP-email flow (Sprint 1), never a password.
            user = CustomUser.objects.create_user(
                username=self._unique_username(validated_data["email"]),
                email=validated_data["email"],
                password=None,
                first_name=validated_data["first_name"],
                last_name=validated_data["last_name"],
            )
            Profile.objects.create(
                user=user, _contact=validated_data.get("contact_phone") or None
            )
            membership = Membership.objects.create(
                user=user,
                chorale=chorale,
                role=validated_data["role"],
                is_admin=False,
            )
        return membership


class MemberUpdateSerializer(MemberWriteMixin, serializers.Serializer):
    """Edit a member: role (admin-gated) and basic name/contact fields."""

    first_name = serializers.CharField(max_length=150, required=False)
    last_name = serializers.CharField(max_length=150, required=False)
    contact_phone = serializers.CharField(
        max_length=15, required=False, allow_blank=True
    )
    role = serializers.ChoiceField(choices=ASSIGNABLE_ROLES, required=False)

    def validate(self, attrs):
        self._check_role_assignment(attrs.get("role"))
        return attrs

    def update(self, instance, validated_data):
        from django.db import transaction

        user = instance.user
        with transaction.atomic():
            if "role" in validated_data:
                instance.role = validated_data["role"]
                instance.save(update_fields=["role"])
            user_fields = []
            for field in ("first_name", "last_name"):
                if field in validated_data:
                    setattr(user, field, validated_data[field])
                    user_fields.append(field)
            if user_fields:
                user.save(update_fields=user_fields)
            if "contact_phone" in validated_data:
                profile, _created = Profile.objects.get_or_create(user=user)
                profile._contact = validated_data["contact_phone"] or None
                profile.save(update_fields=["_contact"])
        return instance


class DashboardStatsSerializer(serializers.Serializer):
    """Shapes the dict returned by ``services.get_dashboard_stats``. Money fields
    are ``DecimalField`` (rendered as strings) so no float ever crosses the wire;
    counts are integers."""

    total_members = serializers.IntegerField()
    upcoming_event_count = serializers.IntegerField()
    cash_balance = serializers.DecimalField(max_digits=14, decimal_places=2)
    cash_in_total = serializers.DecimalField(max_digits=14, decimal_places=2)
    cash_out_total = serializers.DecimalField(max_digits=14, decimal_places=2)
    contributions_collected_this_month = serializers.DecimalField(
        max_digits=14, decimal_places=2
    )
    active_contribution_count = serializers.IntegerField()
    open_sanctions_count = serializers.IntegerField()
    unjustified_absences_this_month = serializers.IntegerField()


class OtpRequestSerializer(serializers.Serializer):
    """Body for ``auth/otp/request``."""

    email = serializers.EmailField()

    def validate_email(self, value):
        return value.lower()


class OtpVerifySerializer(serializers.Serializer):
    """Body for ``auth/otp/verify``."""

    email = serializers.EmailField()
    code = serializers.CharField(max_length=6)

    def validate_email(self, value):
        return value.lower()
