from django.db import migrations, models


class Migration(migrations.Migration):
    """Swap Chorale.members vers le through model Membership et drop Chorale.admin.
    Prérequis : 0010 a déjà rempli Membership à partir de la M2M implicite et de admin.
    Ce swap drop la table M2M implicite (manage_chorale_chorale_members).
    """

    dependencies = [
        ('manage_chorale', '0010_backfill_memberships'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='chorale',
            name='members',
        ),
        migrations.AddField(
            model_name='chorale',
            name='members',
            field=models.ManyToManyField(
                blank=True,
                related_name='chorales',
                through='manage_chorale.Membership',
                to='manage_users.customuser',
            ),
        ),
        migrations.RemoveField(
            model_name='chorale',
            name='admin',
        ),
    ]
