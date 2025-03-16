from rest_framework.permissions import BasePermission

class IsOrganizerOrAdmin(BasePermission):
    def has_permission(self, request, view):
        if request.user.is_superuser:
            return True
        return request.user.role in ['organizer', 'admin']
class IsOrganizer(BasePermission):
    def has_permission(self, request, view):
        if request.user.is_superuser:
            return True
        return request.user.role == 'organizer'  

class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.role == 'admin'  

class IsAttendee(BasePermission):
    def has_permission(self, request, view):
        return request.user.role == 'attendee'  