"""Serializers for the v1 API.

Serializers expose existing models — no business rules live here. Money fields
are always ``DecimalField`` (never float). JSON keys are ``snake_case``.
"""
from decimal import Decimal

from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from manage_chorale.models import (
    Absence,
    CashFlow,
    Chorale,
    ChoraleEvent,
    Contribution,
    MemberContribution,
    Membership,
)
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

    @extend_schema_field(ProfileSerializer(allow_null=True))
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

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_role(self, obj):
        membership = self._membership(obj)
        return membership.role if membership else None

    @extend_schema_field(serializers.BooleanField())
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


class ChoraleEventSerializer(serializers.ModelSerializer):
    """A calendar event (``ChoraleEvent``). ``report_file`` is read-only here —
    file upload lands with the meeting-reports sprint (multipart). Date rule
    mirrors the web ``ChoraleEventForm``: no past dates, except an edit that
    keeps the event's existing (already past) date untouched."""

    is_upcoming = serializers.BooleanField(read_only=True)
    report_file = serializers.FileField(read_only=True)
    expenses = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False, allow_null=True,
        min_value=Decimal("0"),
    )
    income = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False, allow_null=True,
        min_value=Decimal("0"),
    )

    class Meta:
        model = ChoraleEvent
        fields = (
            "id",
            "title",
            "description",
            "location",
            "date",
            "event_type",
            "expenses",
            "income",
            "report_file",
            "is_upcoming",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id", "report_file", "is_upcoming", "created_at", "updated_at",
        )

    def validate_date(self, value):
        if value < timezone.now():
            if self.instance is not None and value == self.instance.date:
                return value
            raise serializers.ValidationError(
                _("The event date cannot be in the past.")
            )
        return value

    def create(self, validated_data):
        return ChoraleEvent.objects.create(
            chorale=self.context["chorale"],
            created_by=self.context["request"].user,
            **validated_data,
        )


class EventSummarySerializer(serializers.ModelSerializer):
    """Minimal event reference embedded in absence rows."""

    class Meta:
        model = ChoraleEvent
        fields = ("id", "title", "date", "event_type")
        read_only_fields = fields


class AbsenceSerializer(serializers.ModelSerializer):
    """One absence row (sparse model: only absentees are stored)."""

    event = EventSummarySerializer(read_only=True)

    class Meta:
        model = Absence
        fields = ("id", "event", "reason", "is_justified", "recorded_at")
        read_only_fields = fields


class AttendanceAbsenceSerializer(serializers.ModelSerializer):
    """The absence details attached to an absent member in the attendance sheet."""

    class Meta:
        model = Absence
        fields = ("id", "reason", "is_justified")
        read_only_fields = fields


class AttendanceEntrySerializer(serializers.Serializer):
    """One line of the attendance sheet: a member of the chorale and their
    status for the event. ``absence`` is null when present."""

    membership_id = serializers.IntegerField()
    user_id = serializers.IntegerField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    username = serializers.CharField()
    present = serializers.BooleanField()
    absence = AttendanceAbsenceSerializer(allow_null=True)


class AbsenceItemWriteSerializer(serializers.Serializer):
    """One absentee in the bulk attendance write. ``member_id`` is the
    **membership** id (the addressable unit inside a chorale, same as the
    members API)."""

    member_id = serializers.IntegerField()
    reason = serializers.CharField(
        max_length=255, required=False, allow_blank=True, default=""
    )
    is_justified = serializers.BooleanField(required=False, default=False)


class AttendanceWriteSerializer(serializers.Serializer):
    """Bulk attendance body: the **full** list of absentees for the event.
    Idempotent replace (mirrors the web ``AbsenceBulkCreateView``): previous
    absences for the event are wiped and recreated; an empty list clears all."""

    absences = AbsenceItemWriteSerializer(many=True)

    def validate_absences(self, value):
        ids = [item["member_id"] for item in value]
        if len(ids) != len(set(ids)):
            raise serializers.ValidationError(
                _("Duplicate member in the absence list.")
            )
        memberships = Membership.objects.select_related("user").filter(
            chorale=self.context["chorale"], id__in=ids
        )
        by_id = {m.id: m for m in memberships}
        unknown = [str(i) for i in ids if i not in by_id]
        if unknown:
            raise serializers.ValidationError(
                _("Unknown member(s) in this chorale: %(ids)s")
                % {"ids": ", ".join(unknown)}
            )
        for item in value:
            item["membership"] = by_id[item["member_id"]]
        return value


class MemberSummarySerializer(serializers.ModelSerializer):
    """Compact user reference embedded in finance rows."""

    class Meta:
        model = CustomUser
        fields = ("id", "username", "first_name", "last_name")
        read_only_fields = fields


class ContributionSerializer(serializers.ModelSerializer):
    """A contribution *type* (catalogue entry), not a transaction."""

    amount = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=Decimal("0.01")
    )
    target_amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, allow_null=True,
        min_value=Decimal("0.01"),
    )
    total_collected = serializers.SerializerMethodField()

    class Meta:
        model = Contribution
        fields = (
            "id",
            "title",
            "amount",
            "target_amount",
            "description",
            "is_active",
            "total_collected",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "total_collected", "created_at", "updated_at")

    @extend_schema_field(
        serializers.DecimalField(max_digits=14, decimal_places=2)
    )
    def get_total_collected(self, obj):
        from .finances import money_str

        # Annotated by the list view; property fallback for single objects.
        collected = getattr(obj, "collected", None)
        return money_str(collected if collected is not None else obj.total_collected)

    def validate_title(self, value):
        qs = Contribution.objects.filter(
            chorale=self.context["chorale"], title=value
        )
        if self.instance is not None:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                _("A contribution type with this title already exists.")
            )
        return value

    def create(self, validated_data):
        return Contribution.objects.create(
            chorale=self.context["chorale"], **validated_data
        )


class MemberContributionSerializer(serializers.ModelSerializer):
    """A payment (immutable: edits are new rows, never updates)."""

    member = MemberSummarySerializer(read_only=True)
    recorded_by = MemberSummarySerializer(read_only=True)

    class Meta:
        model = MemberContribution
        fields = (
            "id", "amount", "paid_at", "note", "member", "recorded_by",
            "created_at",
        )
        read_only_fields = fields


class PaymentCreateSerializer(serializers.Serializer):
    """Record a payment against a contribution. ``member_id`` is the
    **membership** id. ``amount`` omitted → the contribution's expected
    amount (service default)."""

    member_id = serializers.IntegerField()
    amount = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False, allow_null=True,
        min_value=Decimal("0.01"),
    )
    paid_at = serializers.DateField(required=False)
    note = serializers.CharField(
        max_length=255, required=False, allow_blank=True, default=""
    )

    def validate_member_id(self, value):
        membership = (
            Membership.objects.select_related("user")
            .filter(chorale=self.context["chorale"], pk=value)
            .first()
        )
        if membership is None:
            raise serializers.ValidationError(
                _("Unknown member in this chorale.")
            )
        self.context["membership"] = membership
        return value


class CashFlowSerializer(serializers.ModelSerializer):
    """An income/expense entry. ``date`` is treasurer-entered (editable)."""

    amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, min_value=Decimal("0.01")
    )
    created_by = MemberSummarySerializer(read_only=True)

    class Meta:
        model = CashFlow
        fields = (
            "id",
            "title",
            "type_cash_flow",
            "amount",
            "date",
            "description",
            "created_by",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_by", "created_at", "updated_at")

    def create(self, validated_data):
        return CashFlow.objects.create(
            chorale=self.context["chorale"],
            created_by=self.context["request"].user,
            **validated_data,
        )


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
