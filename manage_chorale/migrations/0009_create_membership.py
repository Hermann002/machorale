import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('manage_chorale', '0008_alter_cashflow_type_cash_flow_alter_chorale_type_c_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='chorale',
            name='created_by',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='created_chorales',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.CreateModel(
            name='Membership',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('role', models.CharField(
                    choices=[
                        ('member', 'Member'),
                        ('secretary', 'Secretary'),
                        ('treasurer', 'Treasurer'),
                        ('censor', 'Censor'),
                        ('admin', 'Admin'),
                    ],
                    default='member',
                    max_length=20,
                )),
                ('is_admin', models.BooleanField(default=False)),
                ('joined_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('chorale', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='memberships',
                    to='manage_chorale.chorale',
                )),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='memberships',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'constraints': [
                    models.UniqueConstraint(fields=('user', 'chorale'), name='uniq_user_chorale'),
                ],
                'indexes': [
                    models.Index(fields=['chorale', 'is_admin'], name='manage_chor_chorale_851738_idx'),
                    models.Index(fields=['user', 'chorale'], name='manage_chor_user_id_d30c26_idx'),
                ],
            },
        ),
    ]
