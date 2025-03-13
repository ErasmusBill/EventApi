from rest_framework.permissions import BasePermission
from authservices.models import User

class IsOrganizer(BasePermission):
    def has_permission(self, request, view):
        if request.user.is_superuser:
            return True
        return request.user.role == User.role.ORGANIZER
    
    
    
class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.role == User.role.ADMIN    
    

class IsAttendee(BasePermission):
    def has_permission(self, request, view):
        return request.user.role == User.role.ATTENDEE
    
    
    