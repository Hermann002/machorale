from django.db import migrations


class Migration(migrations.Migration):
    """Drop CustomUser.role et CustomUser.chorale_role.
    Doit s'exécuter APRÈS manage_chorale.0010 (qui lit chorale_role pour backfill).
    """

    dependencies = [
        ('manage_users', '0008_alter_customuser_chorale_role_alter_customuser_role_and_more'),
        ('manage_chorale', '0010_backfill_memberships'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='customuser',
            name='chorale_role',
        ),
        migrations.RemoveField(
            model_name='customuser',
            name='role',
        ),
    ]
