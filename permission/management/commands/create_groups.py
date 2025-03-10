from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from authservices.models import User

class Command(BaseCommand):
    help = 'Creates default user groups with permissions'

    def handle(self, *args, **options):
        # Create or get groups
        admin_group, _ = Group.objects.get_or_create(name='Admin')
        organizer_group, _ = Group.objects.get_or_create(name='Organizer')
        attendee_group, _ = Group.objects.get_or_create(name='Attendee')

        # Assign permissions to Organizer group
        organizer_perms = [
            'add_event',
            'change_event',
            'delete_event',
            'view_event'
        ]
        for perm in organizer_perms:
            organizer_group.permissions.add(
                Permission.objects.get(codename=perm))
        
        # Assign admin permissions
        admin_group.permissions.set(Permission.objects.all())

        self.stdout.write(self.style.SUCCESS('Successfully created groups'))