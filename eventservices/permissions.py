from rest_framework.permissions import BasePermission
from authservices.models import User

class IsOrganizer(BasePermission):
    def has_permission(self, request, view):
        return request.user.role == User.role.ORGANIZER
    
    
    
class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.role == User.role.ADMIN    
    

class IsAttendee(BasePermission):
    def has_permission(self, request, view):
        return super().has_permission(request, view)    