from rest_framework import serializers
from .models import *

class EventSerializer(serializers.ModelSerializer):
    organizer = serializers.StringRelatedField(read_only=True)
    
    class Meta:
        model = Event
        fields = [
            "id", "title","description","start_datetime","end_datetime","location","is_virtual","virtual_meeting_link","banner_image","capacity","registration_deadline","is_public","categories","organizer"
        ]
        
        read_only_fields = ["organizer"]
        
        
class EventRegistrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event_registration
        fields = ["id","event","attendee","status","registration_date"]
        read_only_fields = ["attendee","status","registration_date"]    
        
class TicketTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = TicketType
        fields = '__all__'      
        
        
class EventCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = EventCategory
        fields = '__all__'
                 