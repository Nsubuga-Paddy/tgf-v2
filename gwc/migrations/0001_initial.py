# Generated manually for GWC models

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('accounts', '0003_add_bank_account_fields'),
    ]

    operations = [
        migrations.CreateModel(
            name='GWCGroup',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text='Group name', max_length=200)),
                ('description', models.TextField(blank=True, help_text='Group description')),
                ('target_amount', models.DecimalField(decimal_places=2, default=120000000, help_text='Minimum amount required (120M)', max_digits=14)),
                ('total_contributed', models.DecimalField(decimal_places=2, default=0.0, help_text='Total amount contributed by all members', max_digits=14)),
                ('is_active', models.BooleanField(default=True, help_text='Group is active and accepting members')),
                ('is_complete', models.BooleanField(default=False, help_text='Group has reached minimum target (120M)')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('completed_at', models.DateTimeField(blank=True, help_text='When group reached 120M', null=True)),
                ('created_by', models.ForeignKey(help_text='User who created this group', on_delete=django.db.models.deletion.CASCADE, related_name='created_gwc_groups', to='accounts.userprofile')),
            ],
            options={
                'verbose_name': 'GWC Group',
                'verbose_name_plural': 'GWC Groups',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='GWCGroupMember',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('contribution_amount', models.DecimalField(decimal_places=2, help_text='Amount this member contributed', max_digits=14)),
                ('is_leader', models.BooleanField(default=False, help_text='Is this member the group leader/creator')),
                ('joined_at', models.DateTimeField(auto_now_add=True)),
                ('group', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='members', to='gwc.gwcgroup')),
                ('user_profile', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='gwc_group_memberships', to='accounts.userprofile')),
            ],
            options={
                'verbose_name': 'GWC Group Member',
                'verbose_name_plural': 'GWC Group Members',
                'ordering': ['-joined_at'],
                'unique_together': {('group', 'user_profile')},
            },
        ),
        migrations.CreateModel(
            name='GWCContribution',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.DecimalField(decimal_places=2, help_text='Contribution amount', max_digits=14)),
                ('receipt_number', models.CharField(blank=True, help_text='Transaction receipt number', max_length=100, null=True)),
                ('contributed_at', models.DateTimeField(auto_now_add=True)),
                ('group', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='contributions', to='gwc.gwcgroup')),
                ('user_profile', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='gwc_contributions', to='accounts.userprofile')),
            ],
            options={
                'verbose_name': 'GWC Contribution',
                'verbose_name_plural': 'GWC Contributions',
                'ordering': ['-contributed_at'],
            },
        ),
    ]

