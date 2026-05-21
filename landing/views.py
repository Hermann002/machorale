from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.db import connection
from django.conf import settings
from django.core.cache import cache
from django.views import View
from django.contrib.auth import login, logout
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.cache import never_cache
from datetime import timedelta, date
from uuid import uuid4

from manage_users.models import CustomUser
from django.core.exceptions import ObjectDoesNotExist

@never_cache
def home(request):
    slug = None
    if request.user.is_authenticated:
        active = request.session.get('active_chorale_slug')
        membership_qs = request.user.memberships.select_related('chorale').only('chorale__slug')
        if active and membership_qs.filter(chorale__slug=active).exists():
            slug = active
        else:
            first = membership_qs.first()
            if first:
                slug = first.chorale.slug
                request.session['active_chorale_slug'] = slug
    return render(request, 'landing/pages/home.html', {"slug": slug})

class DemoView(View):
    DEMO_LIFETIME_HOURS = 2

    def get(self, request):
        self._cleanup_expired_demo_users()

        if request.user.is_authenticated:
            logout(request)

        demo_user = self._create_demo_user()
        chorale = self._seed_demo_chorale(demo_user)

        login(request, demo_user, backend='manage_users.backends.CaseInsensitiveModelBackend')
        request.session['is_demo'] = True
        cache.set(f"user_slug_{demo_user.id}", chorale.slug, timeout=7200)

        return redirect(reverse('dashboard', kwargs={'slug': chorale.slug}))

    def _create_demo_user(self):
        from manage_users.models import Profile

        suffix = uuid4().hex[:8]
        demo_user = CustomUser.objects.create(
            username=f"demo_{suffix}",
            email=f"demo_{suffix}@demo.internal",
            first_name="Admin",
            last_name="Démo",
            is_verify=True,
        )
        demo_user.set_unusable_password()
        demo_user.save()
        Profile.objects.create(user=demo_user)
        return demo_user

    def _seed_demo_chorale(self, admin):
        from manage_chorale.models import Chorale, ChoraleEvent, Event, Membership
        from manage_users.models import Profile

        chorale = Chorale.objects.create(
            name="Chorale Démo",
            established_date=date(2020, 1, 15),
            country="Cameroun",
            city="Yaoundé",
            address="Quartier Bastos, Avenue Kennedy",
            contact_email="contact@chorale-demo.cm",
            contact_phone="+237 690 000 000",
            type_c="chorale",
            created_by=admin,
            slogan="Louer ensemble, grandir ensemble",
            meeting_frequency="weekly",
            description="Chorale de démonstration pour découvrir l'application.",
        )

        Membership.objects.create(
            user=admin, chorale=chorale,
            role=Membership.ROLE_ADMIN, is_admin=True,
        )

        member_data = [
            ("Sophie", "Mballa", Membership.ROLE_SECRETARY),
            ("Paul", "Nkeng", Membership.ROLE_TREASURER),
            ("Marie", "Fotso", Membership.ROLE_MEMBER),
            ("Jean", "Ateba", Membership.ROLE_MEMBER),
            ("Claire", "Biya", Membership.ROLE_CENSOR),
        ]
        for first_name, last_name, role in member_data:
            suffix = uuid4().hex[:6]
            m = CustomUser.objects.create(
                username=f"demo_m_{suffix}",
                email=f"demo_m_{suffix}@demo.internal",
                first_name=first_name,
                last_name=last_name,
                is_verify=True,
            )
            m.set_unusable_password()
            m.save()
            Profile.objects.create(user=m)
            Membership.objects.create(
                user=m, chorale=chorale, role=role, is_admin=False,
            )

        now = timezone.now()
        ChoraleEvent.objects.bulk_create([
            ChoraleEvent(
                chorale=chorale,
                title="Répétition hebdomadaire",
                description="Révision des chants pour le prochain dimanche.",
                location="Salle paroissiale Saint-Pierre",
                date=now - timedelta(days=7),
                event_type='practice',
                created_by=admin,
                expenses=5000,
            ),
            ChoraleEvent(
                chorale=chorale,
                title="Réunion de bureau",
                description="Discussion du budget trimestriel et planning des événements.",
                location="Bureau de la chorale",
                date=now - timedelta(days=14),
                event_type='meeting',
                created_by=admin,
            ),
            ChoraleEvent(
                chorale=chorale,
                title="Répétition générale — Concert de Noël",
                description="Répétition générale avant le grand concert annuel.",
                location="Cathédrale Notre-Dame de Yaoundé",
                date=now + timedelta(days=10),
                event_type='practice',
                created_by=admin,
            ),
            ChoraleEvent(
                chorale=chorale,
                title="Concert de Noël",
                description="Grand concert annuel ouvert au public. Entrée libre.",
                location="Cathédrale Notre-Dame de Yaoundé",
                date=now + timedelta(days=17),
                event_type='concert',
                created_by=admin,
                expenses=50000,
                income=120000,
            ),
        ])

        Event.log(chorale, admin, 'person_add', "5 membres ont rejoint la Chorale Démo.")
        Event.log(chorale, admin, 'payment', "Cotisation du mois d'octobre encaissée : 25 000 XAF.")
        Event.log(chorale, admin, 'upload_file', "Rapport de la réunion du bureau ajouté.")

        return chorale

    def _cleanup_expired_demo_users(self):
        # demo_* catches both admin (demo_<8>) and members (demo_m_<6>)
        cutoff = timezone.now() - timedelta(hours=self.DEMO_LIFETIME_HOURS)
        CustomUser.objects.filter(
            username__startswith='demo_',
            date_joined__lt=cutoff
        ).delete()


def health_check(request):
    """
    Endpoint de health check pour les services externes.
    Retourne 200 si tout va bien, 503 sinon.
    """
    checks = {
        "database": False,
        "redis": False,
        "debug": settings.DEBUG,
    }
    status_code = 200

    # 🔍 Vérification base de données
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        checks["database"] = True
    except Exception as e:
        checks["database_error"] = str(e)
        status_code = 503

    # 🔍 Vérification Redis (si utilisé)
    try:
        from django.core.cache import cache
        cache.set("__health_check__", "ok", timeout=10)
        if cache.get("__health_check__") == "ok":
            checks["redis"] = True
        else:
            checks["redis_error"] = "Cache get failed"
            status_code = 503
    except Exception as e:
        checks["redis_error"] = str(e)
        status_code = 503

    return JsonResponse(checks, status=status_code)