from django.db import migrations


def backfill_memberships(apps, schema_editor):
    """Crée les Membership à partir de Chorale.admin (OneToOne) et de la M2M implicite chorale_members.
    Étape critique : doit s'exécuter AVANT 0011 qui drop la table M2M implicite.
    """
    Chorale = apps.get_model('manage_chorale', 'Chorale')
    Membership = apps.get_model('manage_chorale', 'Membership')

    ImplicitThrough = Chorale.members.through

    # 1) Admin → Membership(is_admin=True, role='admin') + Chorale.created_by
    for chorale in Chorale.objects.all():
        admin_id = getattr(chorale, 'admin_id', None)
        if not admin_id:
            continue
        Membership.objects.update_or_create(
            user_id=admin_id,
            chorale_id=chorale.id,
            defaults={'is_admin': True, 'role': 'admin'},
        )
        if not chorale.created_by_id:
            chorale.created_by_id = admin_id
            chorale.save(update_fields=['created_by'])

    # 2) Chaque (user, chorale) de la M2M implicite → Membership(role=user.chorale_role or 'member')
    #    get_or_create pour ne pas écraser l'admin déjà inséré au step 1.
    CustomUser = apps.get_model('manage_users', 'CustomUser')
    for row in ImplicitThrough.objects.all():
        user = CustomUser.objects.filter(id=row.customuser_id).first()
        role = getattr(user, 'chorale_role', None) or 'member' if user else 'member'
        Membership.objects.get_or_create(
            user_id=row.customuser_id,
            chorale_id=row.chorale_id,
            defaults={'role': role, 'is_admin': False},
        )


def noop_reverse(apps, schema_editor):
    # Reverse best-effort : on ne reconstruit pas la M2M implicite ni le OneToOne admin
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('manage_chorale', '0009_create_membership'),
    ]

    operations = [
        migrations.RunPython(backfill_memberships, reverse_code=noop_reverse),
    ]
