# Generated by Django 5.1.6 on 2025-03-13 22:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('authservices', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='role',
            field=models.CharField(choices=[('Admin', 'admin'), ('Attendee', 'attendee'), ('Organizer', 'organizer')], default='attendee', max_length=255),
        ),
    ]
